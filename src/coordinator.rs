use crate::{
    protocol::{Recommendation, Vehicle},
    scenario::{project, Scenario},
};
use serde::Serialize;
use std::collections::{HashMap, HashSet};

#[derive(Clone, Serialize)]
pub struct Reservation {
    pub vehicle_id: String,
    pub entry_sim_s: f64,
    pub exit_sim_s: f64,
    pub committed: bool,
}

#[derive(Clone)]
pub struct PlanInput {
    pub vehicles: Vec<Vehicle>,
    pub first_seen: HashMap<String, u64>,
    pub previous: Vec<Reservation>,
    pub sim_time_s: f64,
    pub plan_seq: u64,
    pub scenario: Scenario,
}

pub struct Plan {
    pub recommendations: Vec<Recommendation>,
    pub reservations: Vec<Reservation>,
    pub degraded: bool,
}

pub fn plan(input: PlanInput) -> Plan {
    let mut vehicles = input.vehicles;
    vehicles.sort_by_key(|v| {
        (
            input
                .first_seen
                .get(&v.vehicle_id)
                .copied()
                .unwrap_or(u64::MAX),
            v.vehicle_id.clone(),
        )
    });
    let headway_vehicles = vehicles.clone();
    let mut reservations = Vec::new();
    let mut recommendations = Vec::new();
    let mut degraded = false;
    let present: HashSet<_> = vehicles.iter().map(|v| v.vehicle_id.as_str()).collect();
    for r in &input.previous {
        if !present.contains(r.vehicle_id.as_str()) {
            reservations.push(r.clone());
            degraded = true;
        }
    }
    for v in vehicles {
        let Some(route) = input.scenario.route(&v.route_id) else {
            degraded = true;
            continue;
        };
        let (s, deviation) = project(route, v.position_xy_m);
        let zone_center_s = route.zone_center_s_m;
        let half = input.scenario.zone_half_extent_m + input.scenario.margin_m + v.length_m / 2.0;
        let entry_s = zone_center_s - half;
        let exit_s = zone_center_s + half;
        let speed = (v.velocity_xy_mps[0].powi(2) + v.velocity_xy_mps[1].powi(2)).sqrt();
        let in_zone = s >= entry_s && s <= exit_s;
        let prior = input.previous.iter().find(|r| r.vehicle_id == v.vehicle_id);
        let committed = in_zone
            || s >= route.commit_s_m && s < exit_s
            || prior.is_some_and(|r| r.committed && s < exit_s);
        if s > exit_s {
            recommendations.push(advice(
                &v.vehicle_id,
                input.scenario.max_speed_mps,
                "proceed",
                "zone_cleared",
                None,
                None,
            ));
            continue;
        }
        if deviation > 4.0 {
            degraded = true;
            recommendations.push(advice(
                &v.vehicle_id,
                0.0,
                "fallback",
                "route_deviation",
                None,
                None,
            ));
            if committed {
                reservations.push(Reservation {
                    vehicle_id: v.vehicle_id,
                    entry_sim_s: input.sim_time_s,
                    exit_sim_s: input.sim_time_s + 30.0,
                    committed: true,
                });
            }
            continue;
        }
        if committed {
            let exit = input.sim_time_s + ((exit_s - s).max(0.0) / speed.max(1.0)) + 1.0;
            reservations.push(Reservation {
                vehicle_id: v.vehicle_id.clone(),
                entry_sim_s: input.sim_time_s,
                exit_sim_s: exit,
                committed: true,
            });
            recommendations.push(advice(
                &v.vehicle_id,
                input.scenario.max_speed_mps,
                "proceed",
                "already_committed",
                Some(format!("reservation-{}-{}", input.plan_seq, v.vehicle_id)),
                Some([input.sim_time_s, input.sim_time_s + 0.5]),
            ));
            continue;
        }
        let distance = (entry_s - s).max(0.0);
        let stop_distance = speed * speed / 6.0 + speed * 0.5 + input.scenario.margin_m;
        if distance <= stop_distance {
            let exit = input.sim_time_s + (exit_s - s).max(0.0) / speed.max(1.0) + 2.0;
            reservations.push(Reservation {
                vehicle_id: v.vehicle_id.clone(),
                entry_sim_s: input.sim_time_s,
                exit_sim_s: exit,
                committed: true,
            });
            recommendations.push(advice(
                &v.vehicle_id,
                input.scenario.max_speed_mps,
                "proceed",
                "cannot_stop_before_zone",
                None,
                Some([input.sim_time_s, input.sim_time_s + 0.5]),
            ));
            continue;
        }
        let earliest = input.sim_time_s + distance / speed.max(1.0);
        let mut entry = earliest;
        for r in &reservations {
            if entry <= r.exit_sim_s + 1.0 && entry + 2.0 >= r.entry_sim_s {
                entry = r.exit_sim_s + 1.0;
            }
        }
        let exit = entry + (2.0 * half) / speed.max(2.0) + 1.0;
        let cap = (distance / (entry - input.sim_time_s).max(0.1))
            .clamp(0.0, input.scenario.max_speed_mps);
        let delayed = entry > earliest + 0.1;
        let action = if delayed { "yield" } else { "proceed" };
        let reason = if delayed {
            "conflicting_reservation"
        } else {
            "clear_window"
        };
        reservations.push(Reservation {
            vehicle_id: v.vehicle_id.clone(),
            entry_sim_s: entry,
            exit_sim_s: exit,
            committed: false,
        });
        recommendations.push(advice(
            &v.vehicle_id,
            if delayed { 0.0 } else { cap },
            action,
            reason,
            Some(format!("reservation-{}-{}", input.plan_seq, v.vehicle_id)),
            Some([entry, entry + 0.5]),
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
