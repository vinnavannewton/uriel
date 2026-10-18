use crate::{
    protocol::{Recommendation, Vehicle},
    scenario::{project, Route, Scenario},
};
use serde::Serialize;
use std::collections::{HashMap, HashSet};

const HORIZON_S: f64 = 8.0;
const ACCEL_HORIZON_S: f64 = 1.0;
const BRAKING_MPS2: f64 = 3.0;
const RESPONSE_S: f64 = 0.5;
const TIME_MARGIN_S: f64 = 1.0;
const UNRESOLVED_S: f64 = 3600.0;

#[derive(Clone, Serialize)]
pub struct Reservation {
    pub vehicle_id: String,
    pub route_id: String,
    pub entry_sim_s: f64,
    pub exit_sim_s: f64,
    pub committed: bool,
    pub granted: bool,
    pub envelope_radius_m: f64,
    pub yielding_to: Vec<String>,
}

#[derive(Clone)]
pub struct PlanInput {
    pub vehicles: Vec<Vehicle>,
    pub first_seen: HashMap<String, u64>,
    pub previous: Vec<Reservation>,
    pub sim_time_s: f64,
    pub plan_seq: u64,
    pub scenario: Scenario,
    pub ml_predictions: HashMap<String, crate::ml::Prediction>,
}

pub struct Plan {
    pub recommendations: Vec<Recommendation>,
    pub reservations: Vec<Reservation>,
    pub degraded: bool,
}

struct Approach<'a> {
    vehicle: &'a Vehicle,
    distance: f64,
    speed: f64,
    accel: f64,
    radius: f64,
    entry: Option<f64>,
    exit: f64,
    occupied: bool,
    must_go: bool,
    cleared: bool,
    invalid: bool,
}

// Along-route acceleration is used for one second, then speed is held constant.
// Braking never predicts reverse travel or spontaneous movement from rest.
fn travel(speed: f64, accel: f64, time: f64) -> f64 {
    let t = time.min(ACCEL_HORIZON_S);
    let t = if accel < 0.0 {
        t.min(speed / -accel)
    } else {
        t
    };
    speed * t + 0.5 * accel * t * t + (speed + accel * t).max(0.0) * (time - t).max(0.0)
}

fn eta(distance: f64, speed: f64, accel: f64) -> Option<f64> {
    eta_with_horizon(distance, speed, accel, HORIZON_S)
}

fn eta_with_horizon(distance: f64, speed: f64, accel: f64, horizon: f64) -> Option<f64> {
    if distance <= 0.0 {
        return Some(0.0);
    }
    if travel(speed, accel, horizon) < distance {
        return None;
    }
    let (mut low, mut high) = (0.0, horizon);
    for _ in 0..40 {
        let mid = (low + high) / 2.0;
        if travel(speed, accel, mid) < distance {
            low = mid;
        } else {
            high = mid;
        }
    }
    Some(high)
}

fn point_at(route: &Route, progress: f64) -> [f64; 2] {
    let mut remaining = progress;
    for p in route.points_xy_m.windows(2) {
        let length = (p[1][0] - p[0][0]).hypot(p[1][1] - p[0][1]);
        if length <= 0.0 {
            continue;
        }
        if remaining <= length {
            let t = (remaining / length).clamp(0.0, 1.0);
            return [
                p[0][0] + t * (p[1][0] - p[0][0]),
                p[0][1] + t * (p[1][1] - p[0][1]),
            ];
        }
        remaining -= length;
    }
    *route.points_xy_m.last().unwrap()
}

fn approach<'a>(v: &'a Vehicle, route: &Route, scenario: &Scenario) -> Approach<'a> {
    let (s, deviation) = project(route, v.position_xy_m);
    let a = point_at(route, (s - 0.05).max(0.0));
    let b = point_at(route, s + 0.05);
    let norm = (b[0] - a[0]).hypot(b[1] - a[1]).max(1e-9);
    let tangent = [(b[0] - a[0]) / norm, (b[1] - a[1]) / norm];
    let signed_speed = v.velocity_xy_mps[0] * tangent[0] + v.velocity_xy_mps[1] * tangent[1];
    let speed = signed_speed.max(0.0);
    let accel = (v.acceleration_xy_mps2[0] * tangent[0] + v.acceleration_xy_mps2[1] * tangent[1])
        .clamp(-8.0, 4.0);
    let radius = v.length_m.hypot(v.width_m) / 2.0;
    let half = scenario.zone_half_extent_m + scenario.margin_m + radius;
    let entry_s = route.zone_center_s_m - half;
    let exit_s = route.zone_center_s_m + half;
    let distance = (entry_s - s).max(0.0);
    let occupied = s >= entry_s && s <= exit_s;
    let reacting_speed = speed + accel.max(0.0) * RESPONSE_S;
    let stop_distance = speed * RESPONSE_S
        + 0.5 * accel.max(0.0) * RESPONSE_S.powi(2)
        + reacting_speed.powi(2) / (2.0 * BRAKING_MPS2)
        + scenario.margin_m;
    Approach {
        vehicle: v,
        distance,
        speed,
        accel,
        radius,
        entry: eta(distance, speed, accel),
        exit: eta_with_horizon((exit_s - s).max(0.0), speed, accel, 60.0).unwrap_or(UNRESOLVED_S),
        occupied,
        must_go: occupied || (speed > 0.5 && distance <= stop_distance),
        cleared: s > exit_s,
        invalid: deviation > 4.0 || signed_speed < -0.5,
    }
}

fn spatial_conflict(scenario: &Scenario, a: &Reservation, b: &Reservation) -> bool {
    if a.route_id == b.route_id {
        return false;
    } // Same-route following is handled below.
    let (Some(ar), Some(br)) = (scenario.route(&a.route_id), scenario.route(&b.route_id)) else {
        return true;
    };
    let ap = point_at(ar, ar.zone_center_s_m);
    let bp = point_at(br, br.zone_center_s_m);
    // Conservative enclosing circles cover the entire buffered route-zone span.
    (ap[0] - bp[0]).hypot(ap[1] - bp[1])
        <= 2.0 * (scenario.zone_half_extent_m + scenario.margin_m)
            + a.envelope_radius_m
            + b.envelope_radius_m
}

fn overlaps(a: &Reservation, b: &Reservation) -> bool {
    a.entry_sim_s <= b.exit_sim_s + TIME_MARGIN_S && a.exit_sim_s + TIME_MARGIN_S >= b.entry_sim_s
}

// Choose a cap that delays entry even after allowing for response time and a
// finite braking ramp. A cap is a request, not proof that the car achieved it.
fn delayed_cap(a: &Approach, wait_s: f64, max_speed: f64) -> f64 {
    if wait_s >= UNRESOLVED_S / 2.0 || a.speed < 0.5 {
        return 0.0;
    }
    let reaction = wait_s.min(RESPONSE_S);
    let v = a.speed + a.accel.max(0.0) * reaction;
    let initial = a.speed * reaction + 0.5 * a.accel.max(0.0) * reaction.powi(2);
    let remaining = (wait_s - reaction).max(0.0);
    let (mut low, mut high) = (0.0, a.speed.min(max_speed));
    for _ in 0..40 {
        let cap = (low + high) / 2.0;
        let braking = ((v - cap).max(0.0) / BRAKING_MPS2).min(remaining);
        let distance = initial + v * braking - 0.5 * BRAKING_MPS2 * braking.powi(2)
            + cap * (remaining - braking);
        if distance < (a.distance - 0.5).max(0.0) {
            low = cap;
        } else {
            high = cap;
        }
    }
    low
}

pub fn plan(input: PlanInput) -> Plan {
    let scenario = &input.scenario;
    let now = input.sim_time_s;
    let headway_vehicles = input.vehicles.clone();
    let mut approaches: Vec<_> = input
        .vehicles
        .iter()
        .filter_map(|v| {
            scenario
                .route(&v.route_id)
                .map(|route| approach(v, route, scenario))
        })
        .collect();
    // Experimental hybrid estimates may widen a physical occupancy window.
    // They cannot shorten physical clearance or move physical entry later.
    for a in &mut approaches {
        if a.invalid || a.cleared || a.occupied || a.must_go {
            continue;
        }
        if let Some(p) = input.ml_predictions.get(&a.vehicle.vehicle_id) {
            if p.status != "predicted" { continue; }
            if let (Some(entry), Some(exit)) = (p.entry_eta_s, p.rear_clearance_eta_s) {
                if entry.is_finite() && exit.is_finite() && entry >= 0.0
                    && exit >= entry && exit <= 60.0 {
                    if let Some(physical_entry) = a.entry {
                        a.entry = Some(physical_entry.min((entry - 2.0).max(0.0)));
                        a.exit = a.exit.max(exit + 2.0);
                    }
                }
            }
        }
    }
    approaches.sort_by_key(|a| {
        let prior = input
            .previous
            .iter()
            .position(|r| r.vehicle_id == a.vehicle.vehicle_id);
        let granted = prior.is_some_and(|i| input.previous[i].granted);
        (
            !a.occupied,
            !a.must_go,
            !granted,
            prior.unwrap_or(usize::MAX),
            input
                .first_seen
                .get(&a.vehicle.vehicle_id)
                .copied()
                .unwrap_or(u64::MAX),
            a.vehicle.vehicle_id.clone(),
        )
    });
    let present: HashSet<_> = input
        .vehicles
        .iter()
        .map(|v| v.vehicle_id.as_str())
        .collect();
    let mut reservations = Vec::new();
    let mut recommendations = Vec::new();
    let mut degraded = approaches.len() != input.vehicles.len();
    for previous in &input.previous {
        if !present.contains(previous.vehicle_id.as_str())
            && (previous.granted || previous.committed)
        {
            let mut held = previous.clone();
            held.entry_sim_s = now;
            held.exit_sim_s = now + UNRESOLVED_S;
            reservations.push(held);
            degraded = true;
        }
    }
    let reserve = |a: &Approach| Reservation {
        vehicle_id: a.vehicle.vehicle_id.clone(),
        route_id: a.vehicle.route_id.clone(),
        entry_sim_s: now + a.entry.unwrap_or(0.0),
        exit_sim_s: now + a.exit,
        committed: a.must_go,
        granted: true,
        envelope_radius_m: a.radius,
        yielding_to: Vec::new(),
    };
    let mut emergency = HashSet::new();
    for (i, a) in approaches.iter().enumerate() {
        if !a.must_go || a.cleared {
            continue;
        }
        for b in &approaches[i + 1..] {
            if b.must_go && !b.cleared {
                let (ar, br) = (reserve(a), reserve(b));
                if spatial_conflict(scenario, &ar, &br) && overlaps(&ar, &br) {
                    emergency.insert(a.vehicle.vehicle_id.as_str());
                    emergency.insert(b.vehicle.vehicle_id.as_str());
                }
            }
        }
    }
    for a in &approaches {
        let id = &a.vehicle.vehicle_id;
        let mut r = reserve(a);
        let (mut action, mut reason, mut cap) = ("proceed", "clear_window", scenario.max_speed_mps);
        if a.invalid || emergency.contains(id.as_str()) {
            degraded = true;
            action = "fallback";
            cap = 0.0;
            reason = if a.invalid {
                "route_deviation_or_reverse"
            } else {
                "conflict_braking_infeasible"
            };
            r.entry_sim_s = now;
            r.exit_sim_s = now + UNRESOLVED_S;
            r.committed = true;
            reservations.push(r);
            recommendations.push(advice(id, cap, action, reason, None, None));
            continue;
        }
        if a.cleared {
            recommendations.push(advice(id, cap, action, "zone_cleared", None, None));
            continue;
        }
        let prior_blockers = input
            .previous
            .iter()
            .find(|p| p.vehicle_id == *id)
            .map(|p| p.yielding_to.clone())
            .unwrap_or_default();
        let previously_granted = input
            .previous
            .iter()
            .any(|p| p.vehicle_id == *id && p.granted);
        let mut blocked = false;
        let duration = (r.exit_sim_s - r.entry_sim_s).max(0.2);
        for b in &reservations {
            if prior_blockers.contains(&b.vehicle_id) {
                blocked = true;
                r.yielding_to.push(b.vehicle_id.clone());
                r.entry_sim_s = r.entry_sim_s.max(b.exit_sim_s + TIME_MARGIN_S + 0.001);
                r.exit_sim_s = r.entry_sim_s + duration;
            }
        }
        if a.entry.is_none() && !a.occupied && !blocked && !previously_granted {
            // A stopped car may start; until motion is observed no arrival time
            // is fabricated. Existing grants still retain their priority.
            if !reservations.iter().any(|b| {
                spatial_conflict(scenario, &r, b) && b.exit_sim_s >= now + UNRESOLVED_S / 2.0
            }) {
                recommendations.push(advice(
                    id,
                    cap,
                    action,
                    "outside_prediction_horizon",
                    None,
                    None,
                ));
                continue;
            }
        }
        for _ in 0..=reservations.len() {
            let mut changed = false;
            for b in &reservations {
                if spatial_conflict(scenario, &r, b) && overlaps(&r, b) {
                    blocked = true;
                    if !r.yielding_to.contains(&b.vehicle_id) {
                        r.yielding_to.push(b.vehicle_id.clone());
                    }
                    r.entry_sim_s = b.exit_sim_s + TIME_MARGIN_S + 0.001;
                    r.exit_sim_s = r.entry_sim_s + duration;
                    changed = true;
                }
            }
            if !changed {
                break;
            }
        }
        if blocked {
            action = if a.must_go { "fallback" } else { "yield" };
            reason = if a.must_go {
                "conflict_braking_infeasible"
            } else {
                "predicted_crossing_conflict"
            };
            cap = if a.must_go {
                degraded = true;
                0.0
            } else {
                delayed_cap(a, r.entry_sim_s - now, scenario.max_speed_mps)
            };
            r.granted = false;
        } else if a.occupied {
            reason = "already_in_crossing";
        }
        // Reserve full front-entry to rear-clearance interval, never a fixed
        // two-second shortcut. Keep grant order stable across input reordering.
        let window = Some([r.entry_sim_s, r.entry_sim_s + 0.5]);
        reservations.push(r);
        recommendations.push(advice(
            id,
            cap,
            action,
            reason,
            Some(format!("reservation-{}-{}", input.plan_seq, id)),
            window,
        ));
    }
    for follower in &headway_vehicles {
        let Some(route) = input.scenario.route(&follower.route_id) else {
            continue;
        };
        let (follower_s, _) = project(route, follower.position_xy_m);
        let nearest = headway_vehicles
            .iter()
            .filter(|lead| {
                lead.vehicle_id != follower.vehicle_id && lead.route_id == follower.route_id
            })
            .filter_map(|lead| {
                let (lead_s, _) = project(route, lead.position_xy_m);
                (lead_s > follower_s).then_some((lead, lead_s - follower_s))
            })
            .min_by(|a, b| a.1.total_cmp(&b.1));
        if let Some((lead, gap)) = nearest {
            let follower_speed = follower.velocity_xy_mps[0].hypot(follower.velocity_xy_mps[1]);
            let lead_speed = lead.velocity_xy_mps[0].hypot(lead.velocity_xy_mps[1]);
            let required = follower.length_m + input.scenario.margin_m + follower_speed * 2.0;
            if gap < required {
                if let Some(advice) = recommendations
                    .iter_mut()
                    .find(|a| a.vehicle_id == follower.vehicle_id && a.action != "fallback")
                {
                    advice.speed_cap_mps = advice.speed_cap_mps.min(
                        if gap < follower.length_m + input.scenario.margin_m {
                            0.0
                        } else {
                            lead_speed
                        },
                    );
                    if advice.action != "yield" {
                        advice.action = "yield".into();
                        advice.reason = "following_headway".into();
                    }
                }
            }
        }
    }
    Plan {
        recommendations,
        reservations,
        degraded,
    }
}

fn advice(
    id: &str,
    cap: f64,
    action: &str,
    reason: &str,
    reservation_id: Option<String>,
    window: Option<[f64; 2]>,
) -> Recommendation {
    Recommendation {
        vehicle_id: id.into(),
        speed_cap_mps: cap,
        action: action.into(),
        reason: reason.into(),
        reservation_id,
        entry_window_sim_s: window,
    }
}

#[cfg(test)]
mod crossing_tests {
    use super::*;
    use serde_json::json;

    fn scenario() -> Scenario {
        Scenario::load("scenarios/crossing-v1.json").unwrap()
    }
    fn car(id: &str, route: &str, distance: f64, speed: f64, accel: f64) -> Vehicle {
        let east = route == "west-east";
        serde_json::from_value(json!({"vehicle_id":id,"route_id":route,
            "position_xy_m":if east {[-distance,0.0]} else {[0.0,-distance]},
            "velocity_xy_mps":if east {[speed,0.0]} else {[0.0,speed]},
            "acceleration_xy_mps2":if east {[accel,0.0]} else {[0.0,accel]},
            "heading_rad":if east {0.0} else {std::f64::consts::FRAC_PI_2},
            "length_m":4.5,"width_m":1.8}))
        .unwrap()
    }
    fn input(vehicles: Vec<Vehicle>, previous: Vec<Reservation>, time: f64) -> PlanInput {
        PlanInput {
            vehicles,
            first_seen: HashMap::new(),
            previous,
            sim_time_s: time,
            plan_seq: 1,
            scenario: scenario(),
            ml_predictions: HashMap::new(),
        }
    }
    fn get<'a>(p: &'a Plan, id: &str) -> &'a Recommendation {
        p.recommendations
            .iter()
            .find(|r| r.vehicle_id == id)
            .unwrap()
    }
    #[test]
    fn hybrid_widens_physics_window_and_ignores_inverted_predictions() {
        let baseline_input = input(vec![car("a", "west-east", 25.0, 5.0, 0.0)], vec![], 0.0);
        let baseline = plan(baseline_input.clone());
        let mut hybrid_input = baseline_input.clone();
        hybrid_input.ml_predictions.insert("a".into(), crate::ml::Prediction {
            vehicle_id: "a".into(), entry_eta_s: Some(0.5),
            rear_clearance_eta_s: Some(7.0), status: "predicted".into(),
        });
        let hybrid = plan(hybrid_input.clone());
        assert!(hybrid.reservations[0].entry_sim_s < baseline.reservations[0].entry_sim_s);
        assert!(hybrid.reservations[0].exit_sim_s >= baseline.reservations[0].exit_sim_s);
        assert!(hybrid.reservations[0].exit_sim_s >= 9.0);
        hybrid_input.ml_predictions.get_mut("a").unwrap().rear_clearance_eta_s = Some(0.1);
        let invalid = plan(hybrid_input);
        assert_eq!(invalid.reservations[0].entry_sim_s, baseline.reservations[0].entry_sim_s);
        assert_eq!(invalid.reservations[0].exit_sim_s, baseline.reservations[0].exit_sim_s);
    }
    #[test]
    fn simultaneous_crossing_slows_one_and_holds_priority_after_reordering() {
        let a = car("a", "west-east", 40.0, 8.0, 0.0);
        let b = car("b", "south-north", 40.0, 8.0, 0.0);
        let p = plan(input(vec![a.clone(), b.clone()], vec![], 0.0));
        assert_eq!(get(&p, "a").action, "proceed");
        assert_eq!(get(&p, "b").action, "yield");
        assert!(get(&p, "b").speed_cap_mps > 0.0 && get(&p, "b").speed_cap_mps < 8.0);
        let mut next = input(vec![b, a], p.reservations, 0.2);
        next.first_seen.insert("b".into(), 0);
        next.first_seen.insert("a".into(), 99);
        let p = plan(next);
        assert_eq!(get(&p, "b").action, "yield");
    }
    #[test]
    fn stationary_occupant_is_seeded_before_waiters_and_never_times_out() {
        let blocker = car("z", "south-north", 0.0, 0.0, 0.0);
        let waiting = car("a", "west-east", 40.0, 8.0, 0.0);
        let p = plan(input(vec![waiting.clone(), blocker.clone()], vec![], 0.0));
        assert_eq!(get(&p, "a").action, "yield");
        assert_eq!(get(&p, "a").speed_cap_mps, 0.0);
        let p = plan(input(vec![waiting, blocker], p.reservations, 200.0));
        assert_eq!(get(&p, "a").speed_cap_mps, 0.0);
    }
    #[test]
    fn simultaneous_unstoppable_approaches_request_emergency_braking() {
        let p = plan(input(
            vec![
                car("a", "west-east", 12.0, 12.0, 0.0),
                car("b", "south-north", 12.0, 12.0, 0.0),
            ],
            vec![],
            0.0,
        ));
        assert!(p.degraded);
        for r in p.recommendations {
            assert_eq!(r.action, "fallback");
            assert_eq!(r.speed_cap_mps, 0.0);
        }
    }
    #[test]
    fn acceleration_from_rest_is_used_to_detect_a_near_term_conflict() {
        let p = plan(input(
            vec![
                car("a", "west-east", 30.0, 6.0, 0.0),
                car("b", "south-north", 22.0, 0.0, 4.0),
            ],
            vec![],
            0.0,
        ));
        assert_eq!(get(&p, "b").action, "yield");
        assert_eq!(get(&p, "b").reason, "predicted_crossing_conflict");
    }
    #[test]
    fn measured_rear_clearance_releases_the_other_car() {
        let p = plan(input(
            vec![
                car("a", "west-east", 30.0, 6.0, 0.0),
                car("b", "south-north", 30.0, 6.0, 0.0),
            ],
            vec![],
            0.0,
        ));
        let p = plan(input(
            vec![
                car("a", "west-east", -30.0, 6.0, 0.0),
                car("b", "south-north", 30.0, 0.0, 0.0),
            ],
            p.reservations,
            10.0,
        ));
        assert_eq!(get(&p, "b").action, "proceed");
    }
    #[test]
    fn missing_granted_car_blocks_until_reconciled_even_after_predicted_exit() {
        let p = plan(input(
            vec![
                car("a", "west-east", 30.0, 6.0, 0.0),
                car("b", "south-north", 30.0, 6.0, 0.0),
            ],
            vec![],
            0.0,
        ));
        let p = plan(input(
            vec![car("b", "south-north", 30.0, 0.0, 0.0)],
            p.reservations,
            100.0,
        ));
        assert!(p.degraded);
        assert_eq!(get(&p, "b").speed_cap_mps, 0.0);
    }
    #[test]
    fn reverse_motion_is_not_treated_as_positive_approach_speed() {
        let p = plan(input(
            vec![car("a", "west-east", 30.0, -8.0, 0.0)],
            vec![],
            0.0,
        ));
        assert_eq!(get(&p, "a").action, "fallback");
    }
    #[test]
    fn slowing_the_yielder_does_not_release_it_before_the_winner_clears() {
        let p = plan(input(
            vec![
                car("a", "west-east", 40.0, 8.0, 0.0),
                car("b", "south-north", 40.0, 8.0, 0.0),
            ],
            vec![],
            0.0,
        ));
        let p = plan(input(
            vec![
                car("a", "west-east", 30.0, 8.0, 0.0),
                car("b", "south-north", 35.0, 0.0, 0.0),
            ],
            p.reservations,
            1.0,
        ));
        assert_eq!(get(&p, "b").action, "yield");
        assert_eq!(get(&p, "b").speed_cap_mps, 0.0);
    }
    #[test]
    fn separated_arrivals_do_not_force_yield() {
        let p = plan(input(
            vec![
                car("a", "west-east", 20.0, 3.0, 0.0),
                car("b", "south-north", 80.0, 3.0, 0.0),
            ],
            vec![],
            0.0,
        ));
        assert!(p.recommendations.iter().all(|r| r.action == "proceed"));
    }
}
