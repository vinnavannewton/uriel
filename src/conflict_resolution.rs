//! State-aware intersection conflict primitives.
//!
//! This module deliberately has no optimistic default for braking capability:
//! a vehicle is stoppable only when a validated deceleration envelope is given.

use serde::{Deserialize, Serialize};
use std::collections::HashSet;

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum VehicleState {
    Approaching,
    StoppingFeasible,
    StoppingUncertain,
    StoppingInfeasible,
    InsideConflictZone,
    ClearingConflictZone,
    StoppedBeforeZone,
    Cleared,
    StateUnknown,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Action {
    Yield,
    Stop,
    ContinueToClear,
    Release,
    ClearanceVerified,
    SafeHold,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct VehicleObservation {
    pub vehicle_id: String,
    pub route_id: String,
    pub speed_mps: f64,
    pub acceleration_mps2: Option<f64>,
    pub distance_to_entry_m: f64,
    pub distance_to_rear_clearance_m: f64,
    pub time_to_entry_s: Option<f64>,
    pub time_to_rear_clearance_s: Option<f64>,
    pub waiting_time_s: f64,
    pub length_m: f64,
    pub width_m: f64,
    pub telemetry_age_s: f64,
    pub uncertainty_s: f64,
    pub occupies_zone: bool,
    pub rear_clear: bool,
    pub continue_to_clear_verified: bool,
    pub braking_deceleration_mps2: Option<f64>,
    pub braking_envelope_validated: bool,
}

#[derive(Clone, Copy, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct StoppingConfig {
    pub reaction_time_s: f64,
    pub safety_margin_m: f64,
    pub control_delay_s: f64,
    pub max_telemetry_age_s: f64,
    pub max_uncertainty_s: f64,
}

#[derive(Clone, Copy, Debug, PartialEq)]
pub struct StopAssessment {
    pub feasible: Option<bool>,
    pub stopping_distance_m: Option<f64>,
}

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct ProposedAction {
    pub vehicle_id: String,
    pub action: Action,
    pub reason: &'static str,
    pub reservation_id: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Serialize)]
pub struct SafetyDecision {
    pub accepted: bool,
    pub state: VehicleState,
    pub reason: &'static str,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CommandRecord {
    pub command_id: String,
    pub sim_time_s: f64,
    pub vehicle_id: String,
    pub action: Action,
    pub reservation_id: Option<String>,
    pub acknowledged: Option<bool>,
    pub response_verified: Option<bool>,
    pub response_speed_mps: Option<f64>,
    pub failure: Option<String>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Reservation {
    pub vehicle_id: String,
    pub route_id: String,
    pub committed: bool,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct EvaluateRequest {
    pub frame_seq: u64,
    pub sim_time_s: f64,
    pub config: StoppingConfig,
    pub observations: Vec<VehicleObservation>,
    #[serde(default)]
    pub previous_reservations: Vec<Reservation>,
    #[serde(default)]
    pub conflicting_routes: Vec<[String; 2]>,
}

#[derive(Clone, Debug, Serialize)]
pub struct EvaluateResponse {
    pub frame_seq: u64,
    pub sim_time_s: f64,
    pub phase: &'static str,
    pub safe_hold: bool,
    pub actions: Vec<ProposedAction>,
    pub reservations: Vec<Reservation>,
    pub monitor: Vec<SafetyDecision>,
}

pub fn evaluate(request: EvaluateRequest) -> Result<EvaluateResponse, &'static str> {
    let c = request.config;
    if !request.sim_time_s.is_finite()
        || request.sim_time_s < 0.0
        || request.frame_seq == 0
        || request.observations.is_empty()
        || request.observations.len() > 100
        || request.previous_reservations.len() > 100
        || c.reaction_time_s < 0.0
        || c.reaction_time_s > 5.0
        || c.control_delay_s < 0.0
        || c.control_delay_s > 5.0
        || c.safety_margin_m < 0.0
        || c.safety_margin_m > 100.0
        || c.max_telemetry_age_s <= 0.0
        || c.max_telemetry_age_s > 2.0
        || c.max_uncertainty_s < 0.0
        || c.max_uncertainty_s > 5.0
        || !c.reaction_time_s.is_finite()
        || !c.control_delay_s.is_finite()
        || !c.safety_margin_m.is_finite()
        || !c.max_telemetry_age_s.is_finite()
        || !c.max_uncertainty_s.is_finite()
        || request.conflicting_routes.len() > 100
        || request
            .conflicting_routes
            .iter()
            .flatten()
            .any(|id| !crate::protocol::valid_id(id))
        || request.previous_reservations.iter().any(|r| {
            !crate::protocol::valid_id(&r.vehicle_id) || !crate::protocol::valid_id(&r.route_id)
        })
    {
        return Err("invalid_frame_config_or_bounds");
    }
    let conflicts: HashSet<_> = request
        .conflicting_routes
        .into_iter()
        .map(|pair| (pair[0].clone(), pair[1].clone()))
        .collect();
    let (mut actions, reservations, mut safe_hold) = resolve(
        &request.observations,
        &request.previous_reservations,
        &conflicts,
        c,
    );
    let monitor: Vec<_> = actions
        .iter()
        .map(|a| {
            safety_monitor(
                a,
                request
                    .observations
                    .iter()
                    .find(|o| o.vehicle_id == a.vehicle_id),
                &reservations,
                &conflicts,
                c,
            )
        })
        .collect();
    for (action, verdict) in actions.iter_mut().zip(&monitor) {
        if !verdict.accepted && action.action != Action::ContinueToClear {
            action.action = Action::SafeHold;
            action.reason = verdict.reason;
            safe_hold = true;
        }
    }
    let phase = if safe_hold {
        "SAFE_HOLD"
    } else if actions.iter().any(|a| a.action == Action::ContinueToClear) {
        "CROSSING"
    } else if reservations.iter().any(|r| !r.committed) {
        "RESERVED"
    } else {
        "ASSESSING"
    };
    Ok(EvaluateResponse {
        frame_seq: request.frame_seq,
        sim_time_s: request.sim_time_s,
        phase,
        safe_hold,
        actions,
        reservations,
        monitor,
    })
}

pub fn stopping_distance(o: &VehicleObservation, c: StoppingConfig) -> StopAssessment {
    let fresh = o.telemetry_age_s.is_finite()
        && o.telemetry_age_s >= 0.0
        && o.telemetry_age_s <= c.max_telemetry_age_s
        && o.uncertainty_s.is_finite()
        && o.uncertainty_s >= 0.0
        && o.uncertainty_s <= c.max_uncertainty_s;
    let valid_config = c.reaction_time_s.is_finite()
        && c.reaction_time_s >= 0.0
        && c.control_delay_s.is_finite()
        && c.control_delay_s >= 0.0
        && c.safety_margin_m.is_finite()
        && c.safety_margin_m >= 0.0;
    let braking = o
        .braking_deceleration_mps2
        .filter(|d| d.is_finite() && *d > 0.0);
    if !fresh || !valid_config || !o.braking_envelope_validated || braking.is_none() {
        return StopAssessment {
            feasible: None,
            stopping_distance_m: None,
        };
    }
    if !o.speed_mps.is_finite() || o.speed_mps < 0.0 || !o.distance_to_entry_m.is_finite() {
        return StopAssessment {
            feasible: None,
            stopping_distance_m: None,
        };
    }
    let v = o.speed_mps;
    let decel = braking.unwrap();
    let reaction = v * (c.reaction_time_s + c.control_delay_s + o.uncertainty_s);
    let braking_distance = v * v / (2.0 * decel);
    // Entry distance is measured to the vehicle's front boundary. Include its
    // half-length so the stopping estimate protects the complete footprint.
    let distance = reaction + braking_distance + c.safety_margin_m + o.length_m.max(0.0) / 2.0;
    StopAssessment {
        feasible: Some(o.distance_to_entry_m > distance),
        stopping_distance_m: Some(distance),
    }
}

pub fn classify(o: &VehicleObservation, c: StoppingConfig) -> VehicleState {
    if !valid_observation(o, c) {
        return VehicleState::StateUnknown;
    }
    if o.rear_clear {
        return VehicleState::Cleared;
    }
    if o.occupies_zone {
        return if o.speed_mps <= 0.1 {
            VehicleState::InsideConflictZone
        } else {
            VehicleState::ClearingConflictZone
        };
    }
    if o.distance_to_entry_m < 0.0 {
        return VehicleState::StateUnknown;
    }
    if o.speed_mps <= 0.1 {
        return VehicleState::StoppedBeforeZone;
    }
    match stopping_distance(o, c).feasible {
        Some(true) => VehicleState::StoppingFeasible,
        Some(false) => VehicleState::StoppingInfeasible,
        None => VehicleState::StoppingUncertain,
    }
}

pub fn resolve(
    observations: &[VehicleObservation],
    prior: &[Reservation],
    conflicting_routes: &HashSet<(String, String)>,
    config: StoppingConfig,
) -> (Vec<ProposedAction>, Vec<Reservation>, bool) {
    let mut actions = Vec::new();
    let mut reservations = prior.to_vec();
    let mut safe_hold = false;
    let mut seen = HashSet::new();
    let valid_set = !observations.is_empty()
        && observations
            .iter()
            .all(|o| seen.insert(o.vehicle_id.as_str()) && valid_observation(o, config));
    if !valid_set {
        return (
            observations
                .iter()
                .map(|o| ProposedAction {
                    vehicle_id: o.vehicle_id.clone(),
                    action: Action::SafeHold,
                    reason: "invalid_or_duplicate_state",
                    reservation_id: None,
                })
                .collect(),
            reservations,
            true,
        );
    }

    // Preserve occupancy before considering any waiting candidate.
    let mut ordered = observations.iter().collect::<Vec<_>>();
    ordered.sort_by(|a, b| {
        b.waiting_time_s
            .total_cmp(&a.waiting_time_s)
            .then_with(|| {
                a.time_to_entry_s
                    .unwrap()
                    .total_cmp(&b.time_to_entry_s.unwrap())
            })
            .then_with(|| a.vehicle_id.cmp(&b.vehicle_id))
    });
    for o in &ordered {
        let state = classify(o, config);
        if matches!(
            state,
            VehicleState::InsideConflictZone | VehicleState::ClearingConflictZone
        ) {
            if let Some(reservation) = reservations
                .iter_mut()
                .find(|r| r.vehicle_id == o.vehicle_id)
            {
                reservation.committed = true;
                reservation.route_id = o.route_id.clone();
            } else {
                reservations.push(Reservation {
                    vehicle_id: o.vehicle_id.clone(),
                    route_id: o.route_id.clone(),
                    committed: true,
                });
            }
            actions.push(ProposedAction {
                vehicle_id: o.vehicle_id.clone(),
                action: if o.continue_to_clear_verified {
                    Action::ContinueToClear
                } else {
                    safe_hold = true;
                    Action::SafeHold
                },
                reason: if o.continue_to_clear_verified {
                    "protect_occupied_zone"
                } else {
                    "clearance_path_not_verified"
                },
                reservation_id: Some(format!("occupied:{}", o.vehicle_id)),
            });
        } else if state == VehicleState::StateUnknown
            || state == VehicleState::StoppingUncertain
            || state == VehicleState::StoppingInfeasible
        {
            safe_hold = true;
            if !reservations.iter().any(|r| r.vehicle_id == o.vehicle_id) {
                reservations.push(Reservation {
                    vehicle_id: o.vehicle_id.clone(),
                    route_id: o.route_id.clone(),
                    committed: true,
                });
            }
            actions.push(ProposedAction {
                vehicle_id: o.vehicle_id.clone(),
                action: Action::SafeHold,
                reason: if state == VehicleState::StoppingInfeasible {
                    "stopping_not_feasible"
                } else {
                    "state_or_stopping_uncertain"
                },
                reservation_id: None,
            });
        } else if state == VehicleState::Cleared {
            reservations.retain(|r| r.vehicle_id != o.vehicle_id);
            actions.push(ProposedAction {
                vehicle_id: o.vehicle_id.clone(),
                action: Action::ClearanceVerified,
                reason: "rear_clearance_verified",
                reservation_id: None,
            });
        }
    }

    let occupied: Vec<_> = observations
        .iter()
        .filter(|o| o.occupies_zone && !o.rear_clear)
        .collect();
    let committed: Vec<_> = reservations
        .iter()
        .filter(|r| r.committed)
        .cloned()
        .collect();
    // The initial policy is strictly one vehicle across the managed zone at
    // a time, even when an incomplete conflict table says routes do not meet.
    let mut crossing_reserved = !reservations.is_empty();
    for o in &ordered {
        if actions.iter().any(|a| a.vehicle_id == o.vehicle_id) {
            continue;
        }
        let overlaps_occupancy = occupied
            .iter()
            .any(|x| conflicts(&o.route_id, &x.route_id, conflicting_routes));
        let conflicts_committed = committed.iter().any(|r| {
            r.vehicle_id != o.vehicle_id && conflicts(&o.route_id, &r.route_id, conflicting_routes)
        });
        if overlaps_occupancy || conflicts_committed {
            let state = classify(o, config);
            let action = if state == VehicleState::StoppingFeasible {
                Action::Yield
            } else {
                Action::SafeHold
            };
            if action == Action::SafeHold {
                safe_hold = true;
            }
            actions.push(ProposedAction {
                vehicle_id: o.vehicle_id.clone(),
                action,
                reason: "incompatible_occupancy_or_uncertainty",
                reservation_id: None,
            });
            continue;
        }
        if crossing_reserved {
            let state = classify(o, config);
            let action = if state == VehicleState::StoppingFeasible
                || state == VehicleState::StoppedBeforeZone
            {
                Action::Yield
            } else {
                Action::SafeHold
            };
            if action == Action::SafeHold {
                safe_hold = true;
            }
            actions.push(ProposedAction {
                vehicle_id: o.vehicle_id.clone(),
                action,
                reason: "single_vehicle_crossing_limit",
                reservation_id: None,
            });
            continue;
        }
        if matches!(
            classify(o, config),
            VehicleState::StoppingFeasible | VehicleState::StoppedBeforeZone
        ) {
            let overlaps_reservation = reservations
                .iter()
                .any(|r| conflicts(&o.route_id, &r.route_id, conflicting_routes));
            if !overlaps_reservation {
                let reservation_id = format!("reservation:{}", o.vehicle_id);
                reservations.push(Reservation {
                    vehicle_id: o.vehicle_id.clone(),
                    route_id: o.route_id.clone(),
                    committed: false,
                });
                crossing_reserved = true;
                actions.push(ProposedAction {
                    vehicle_id: o.vehicle_id.clone(),
                    action: Action::Release,
                    reason: "single_conflict_free_candidate",
                    reservation_id: Some(reservation_id),
                });
            } else {
                actions.push(ProposedAction {
                    vehicle_id: o.vehicle_id.clone(),
                    action: Action::Yield,
                    reason: "conflicting_reservation",
                    reservation_id: None,
                });
            }
        } else if classify(o, config) == VehicleState::StoppedBeforeZone {
            actions.push(ProposedAction {
                vehicle_id: o.vehicle_id.clone(),
                action: Action::Yield,
                reason: "not_yet_eligible",
                reservation_id: None,
            });
        } else {
            safe_hold = true;
            actions.push(ProposedAction {
                vehicle_id: o.vehicle_id.clone(),
                action: Action::SafeHold,
                reason: "stopping_not_established_feasible",
                reservation_id: None,
            });
        }
    }
    (actions, reservations, safe_hold)
}

pub fn safety_monitor(
    proposed: &ProposedAction,
    observation: Option<&VehicleObservation>,
    reservations: &[Reservation],
    conflicting_routes: &HashSet<(String, String)>,
    config: StoppingConfig,
) -> SafetyDecision {
    let Some(o) = observation else {
        return reject(VehicleState::StateUnknown, "vehicle_identity_unverified");
    };
    if o.vehicle_id != proposed.vehicle_id || !valid_observation(o, config) {
        return reject(
            VehicleState::StateUnknown,
            "critical_state_invalid_or_stale",
        );
    }
    let state = classify(o, config);
    match proposed.action {
        Action::Stop | Action::Yield => {
            if state != VehicleState::StoppingFeasible && state != VehicleState::StoppedBeforeZone {
                return reject(state, "stop_not_established_feasible");
            }
        }
        Action::Release => {
            if state != VehicleState::StoppingFeasible && state != VehicleState::StoppedBeforeZone {
                return reject(state, "release_state_ineligible");
            }
            if reservations.iter().any(|r| {
                r.vehicle_id != o.vehicle_id
                    && conflicts(&o.route_id, &r.route_id, conflicting_routes)
            }) {
                return reject(state, "conflicting_reservation_exists");
            }
        }
        Action::ContinueToClear => {
            if !o.occupies_zone || o.rear_clear || !o.continue_to_clear_verified {
                return reject(state, "clearance_action_not_justified");
            }
        }
        Action::ClearanceVerified => {
            if !o.rear_clear {
                return reject(state, "rear_clearance_not_verified");
            }
        }
        Action::SafeHold => return reject(state, "safe_hold_blocks_release"),
    }
    SafetyDecision {
        accepted: true,
        state,
        reason: "monitor_approved",
    }
}

fn valid_observation(o: &VehicleObservation, c: StoppingConfig) -> bool {
    !o.vehicle_id.is_empty()
        && !o.route_id.is_empty()
        && o.speed_mps.is_finite()
        && o.speed_mps >= 0.0
        && o.distance_to_entry_m.is_finite()
        && o.distance_to_rear_clearance_m.is_finite()
        && o.time_to_entry_s.is_some_and(|v| v.is_finite() && v >= 0.0)
        && o.time_to_rear_clearance_s
            .is_some_and(|v| v.is_finite() && v >= 0.0)
        && o.waiting_time_s.is_finite()
        && o.waiting_time_s >= 0.0
        && o.length_m.is_finite()
        && (1.0..=30.0).contains(&o.length_m)
        && o.width_m.is_finite()
        && (0.5..=10.0).contains(&o.width_m)
        && o.telemetry_age_s.is_finite()
        && o.telemetry_age_s >= 0.0
        && o.telemetry_age_s <= c.max_telemetry_age_s
        && o.uncertainty_s.is_finite()
        && o.uncertainty_s >= 0.0
        && o.uncertainty_s <= c.max_uncertainty_s
        && o.acceleration_mps2.is_none_or(f64::is_finite)
}
fn conflicts(a: &str, b: &str, pairs: &HashSet<(String, String)>) -> bool {
    a == b
        || pairs.contains(&(a.to_owned(), b.to_owned()))
        || pairs.contains(&(b.to_owned(), a.to_owned()))
}
fn reject(state: VehicleState, reason: &'static str) -> SafetyDecision {
    SafetyDecision {
        accepted: false,
        state,
        reason,
    }
}

pub fn verify_command_response(
    record: &mut CommandRecord,
    speed_mps: Option<f64>,
    stopped_threshold_mps: f64,
) {
    record.response_speed_mps = speed_mps.filter(|v| v.is_finite() && *v >= 0.0);
    record.response_verified = match (record.acknowledged, record.response_speed_mps) {
        (Some(true), Some(speed))
            if record.action == Action::Stop || record.action == Action::Yield =>
        {
            Some(speed <= stopped_threshold_mps)
        }
        (Some(true), Some(_)) => Some(true),
        (Some(false), _) => Some(false),
        _ => None,
    };
}

#[cfg(test)]
mod tests {
    use super::*;
    fn cfg() -> StoppingConfig {
        StoppingConfig {
            reaction_time_s: 0.5,
            safety_margin_m: 2.0,
            control_delay_s: 0.2,
            max_telemetry_age_s: 0.25,
            max_uncertainty_s: 0.2,
        }
    }
    fn obs(id: &str, route: &str, distance: f64) -> VehicleObservation {
        VehicleObservation {
            vehicle_id: id.into(),
            route_id: route.into(),
            speed_mps: 5.0,
            acceleration_mps2: Some(0.0),
            distance_to_entry_m: distance,
            distance_to_rear_clearance_m: 10.0,
            time_to_entry_s: Some(distance.max(0.0) / 5.0),
            time_to_rear_clearance_s: Some((distance + 10.0).max(0.0) / 5.0),
            waiting_time_s: 0.0,
            length_m: 4.5,
            width_m: 1.8,
            telemetry_age_s: 0.01,
            uncertainty_s: 0.01,
            occupies_zone: false,
            rear_clear: false,
            continue_to_clear_verified: false,
            braking_deceleration_mps2: Some(5.0),
            braking_envelope_validated: true,
        }
    }
    fn pairs() -> HashSet<(String, String)> {
        HashSet::from([("east".into(), "north".into())])
    }

    fn request(observations: Vec<VehicleObservation>) -> EvaluateRequest {
        EvaluateRequest {
            frame_seq: 1,
            sim_time_s: 0.0,
            config: cfg(),
            observations,
            previous_reservations: vec![],
            conflicting_routes: vec![["east".into(), "north".into()]],
        }
    }
    #[test]
    fn stop_requires_validated_braking_envelope() {
        let mut o = obs("a", "east", 50.0);
        o.braking_envelope_validated = false;
        assert_eq!(stopping_distance(&o, cfg()).feasible, None);
        o.braking_envelope_validated = true;
        assert_eq!(stopping_distance(&o, cfg()).feasible, Some(true));
        o.distance_to_entry_m = 3.0;
        assert_eq!(stopping_distance(&o, cfg()).feasible, Some(false));
    }
    #[test]
    fn stale_telemetry_is_unknown_and_blocks_release() {
        let mut o = obs("a", "east", 50.0);
        o.telemetry_age_s = 0.5;
        assert_eq!(classify(&o, cfg()), VehicleState::StateUnknown);
        let action = ProposedAction {
            vehicle_id: "a".into(),
            action: Action::Release,
            reason: "test",
            reservation_id: None,
        };
        assert!(!safety_monitor(&action, Some(&o), &[], &pairs(), cfg()).accepted);
    }
    #[test]
    fn occupied_car_is_preserved_and_incompatible_arrival_yields() {
        let mut inside = obs("inside", "east", 0.0);
        inside.occupies_zone = true;
        inside.continue_to_clear_verified = true;
        inside.braking_envelope_validated = false;
        let other = obs("other", "north", 50.0);
        let (actions, reservations, hold) = resolve(&[inside, other], &[], &pairs(), cfg());
        assert!(!hold);
        assert!(reservations
            .iter()
            .any(|r| r.vehicle_id == "inside" && r.committed));
        assert_eq!(
            actions
                .iter()
                .find(|a| a.vehicle_id == "inside")
                .unwrap()
                .action,
            Action::ContinueToClear
        );
        assert_eq!(
            actions
                .iter()
                .find(|a| a.vehicle_id == "other")
                .unwrap()
                .action,
            Action::Yield
        );

        let mut entered = obs("entered", "east", 0.0);
        entered.occupies_zone = true;
        entered.continue_to_clear_verified = true;
        let tentative = Reservation {
            vehicle_id: "entered".into(),
            route_id: "east".into(),
            committed: false,
        };
        let (_, reservations, _) = resolve(&[entered], &[tentative], &pairs(), cfg());
        assert!(reservations
            .iter()
            .any(|r| r.vehicle_id == "entered" && r.committed));

        let mut blocked = obs("blocked", "east", 0.0);
        blocked.occupies_zone = true;
        blocked.continue_to_clear_verified = false;
        let (actions, reservations, hold) = resolve(&[blocked], &[], &pairs(), cfg());
        assert!(hold);
        assert_eq!(actions[0].action, Action::SafeHold);
        assert!(reservations.iter().any(|r| r.committed));
    }
    #[test]
    fn ambiguous_braking_enters_safe_hold_without_issuing_stop() {
        let mut a = obs("a", "east", 50.0);
        a.braking_envelope_validated = false;
        let b = obs("b", "north", 50.0);
        let (actions, _, hold) = resolve(&[a, b], &[], &pairs(), cfg());
        assert!(hold);
        assert!(actions.iter().any(|a| a.action == Action::SafeHold));
        assert!(actions.iter().all(|a| a.action != Action::Release));
    }
    #[test]
    fn reservation_monitor_rejects_incompatible_release() {
        let o = obs("b", "north", 50.0);
        let action = ProposedAction {
            vehicle_id: "b".into(),
            action: Action::Release,
            reason: "test",
            reservation_id: None,
        };
        let reservations = [Reservation {
            vehicle_id: "a".into(),
            route_id: "east".into(),
            committed: false,
        }];
        assert_eq!(
            safety_monitor(&action, Some(&o), &reservations, &pairs(), cfg()).reason,
            "conflicting_reservation_exists"
        );
    }
    #[test]
    fn command_ack_is_not_response_verification() {
        let mut r = CommandRecord {
            command_id: "cmd-1".into(),
            sim_time_s: 1.0,
            vehicle_id: "a".into(),
            action: Action::Stop,
            reservation_id: None,
            acknowledged: Some(true),
            response_verified: None,
            response_speed_mps: None,
            failure: None,
        };
        verify_command_response(&mut r, None, 0.1);
        assert_eq!(r.response_verified, None);
        verify_command_response(&mut r, Some(0.0), 0.1);
        assert_eq!(r.response_verified, Some(true));
    }
    #[test]
    fn cleared_rear_releases_reservation() {
        let mut o = obs("a", "east", -1.0);
        o.rear_clear = true;
        let old = Reservation {
            vehicle_id: "a".into(),
            route_id: "east".into(),
            committed: true,
        };
        let (_, reservations, _) = resolve(&[o], &[old], &pairs(), cfg());
        assert!(reservations.is_empty());
    }

    #[test]
    fn endpoint_evaluator_releases_only_one_conflicting_route() {
        let response = evaluate(request(vec![
            obs("a", "east", 50.0),
            obs("b", "north", 50.0),
        ]))
        .unwrap();
        assert_eq!(
            response
                .actions
                .iter()
                .filter(|a| a.action == Action::Release)
                .count(),
            1
        );
        assert!(response.monitor.iter().all(|d| d.accepted));
    }

    #[test]
    fn endpoint_evaluator_prefers_oldest_waiter() {
        let mut older = obs("older", "east", 70.0);
        older.waiting_time_s = 8.0;
        let younger = obs("younger", "north", 30.0);
        let response = evaluate(request(vec![younger, older])).unwrap();
        assert_eq!(
            response
                .actions
                .iter()
                .find(|a| a.action == Action::Release)
                .unwrap()
                .vehicle_id,
            "older"
        );
    }

    #[test]
    fn initial_policy_limits_each_frame_to_one_vehicle_even_for_unlisted_route_pairs() {
        let response = evaluate(request(vec![
            obs("a", "east", 50.0),
            obs("b", "side_road", 50.0),
        ]))
        .unwrap();
        assert_eq!(
            response
                .actions
                .iter()
                .filter(|a| a.action == Action::Release)
                .count(),
            1
        );
    }

    #[test]
    fn unable_to_stop_vehicle_does_not_receive_yield_or_release() {
        let mut o = obs("a", "east", 3.0);
        let response = evaluate(request(vec![o.clone()])).unwrap();
        assert_eq!(response.actions[0].action, Action::SafeHold);
        o.occupies_zone = true;
        o.continue_to_clear_verified = true;
        let response = evaluate(request(vec![o])).unwrap();
        assert_eq!(response.actions[0].action, Action::ContinueToClear);
    }
}
