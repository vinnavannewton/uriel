//! Display-only telemetry. Never emits or applies driving recommendations.
use crate::headon_protocol::{VehicleState, VEHICLE_IDS};
use serde::Deserialize;
use serde_json::{json, Value};
use std::{sync::Arc, time::Instant};
use tokio::sync::Mutex;

pub const SCENARIO: &str = "collision-grid-observer-v1";
const CROSSING_VEHICLE_IDS: [&str; 6] = [
    "uriel_red",
    "uriel_blue",
    "traffic_1",
    "traffic_2",
    "traffic_3",
    "traffic_4",
];
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Frame {
    #[serde(default = "default_mode")]
    pub mode: String,
    pub world_id: String,
    pub frame_seq: u64,
    pub sim_time_s: f64,
    pub finished: bool,
    pub vehicles: Vec<VehicleState>,
}
fn default_mode() -> String {
    "collision".into()
}
#[derive(Clone, Default)]
pub struct Hub(Arc<Mutex<Option<(Frame, Instant, Value)>>>);
impl Hub {
    pub async fn publish(&self, frame: Frame) -> Result<(), &'static str> {
        let crossing = frame.mode == "crossing";
        let expected_ids: &[&str] = if crossing && frame.vehicles.len() == 2 {
            &["uriel_red", "uriel_blue"]
        } else if crossing {
            CROSSING_VEHICLE_IDS.as_slice()
        } else {
            VEHICLE_IDS.as_slice()
        };
        if !(frame.world_id.starts_with("headon-collision-")
            || frame.world_id.starts_with("headon-dodge-")
            || (crossing && frame.world_id.starts_with("crossing-observer-")))
            || !matches!(frame.mode.as_str(), "collision" | "dodge" | "crossing")
            || !crate::protocol::valid_id(&frame.world_id)
            || !frame.sim_time_s.is_finite()
            || frame.vehicles.len() != expected_ids.len()
            || expected_ids.iter().any(|id| {
                frame
                    .vehicles
                    .iter()
                    .filter(|v| &v.vehicle_id == id)
                    .count()
                    != 1
            })
            || frame.vehicles.iter().any(|v| {
                v.position_xyz_m
                    .iter()
                    .chain(v.velocity_xyz_mps.iter())
                    .chain(v.forward_xyz.iter())
                    .chain(v.up_xyz.iter())
                    .any(|n| !n.is_finite())
                    || !v.length_m.is_finite()
                    || !(0.1..=20.).contains(&v.length_m)
                    || !v.width_m.is_finite()
                    || !(0.1..=10.).contains(&v.width_m)
                    || !v.damage.is_finite()
                    || !v.sensor_sim_time_s.is_finite()
            })
        {
            return Err("invalid observer telemetry");
        }
        let mut latest = self.0.lock().await;
        let bounds = if let Some((prior, received, bounds)) = latest.as_ref() {
            if prior.world_id == frame.world_id {
                if frame.frame_seq <= prior.frame_seq || frame.sim_time_s < prior.sim_time_s {
                    return Err("old observer frame");
                }
                bounds.clone()
            } else {
                if !prior.finished && received.elapsed().as_secs_f64() < 2. {
                    return Err("collision observer already active");
                }
                bounds_for(&frame)
            }
        } else {
            bounds_for(&frame)
        };
        *latest = Some((frame, Instant::now(), bounds));
        Ok(())
    }
    pub async fn snapshot(&self) -> Option<Value> {
        let latest = self.0.lock().await;
        let (f, received, bounds) = latest.as_ref()?;
        let age = received.elapsed().as_millis();
        Some(
            json!({"world_id":f.world_id,"world_epoch":f.world_id,"bridge_id":"beamng-collision-observer",
            "scenario_config_id":SCENARIO,"protocol_version":2,"frame_seq":f.frame_seq,"sim_time_s":f.sim_time_s,
            "wall_age_ms":age,"status":if f.finished {"disconnected"} else if age>1500 {"stale"} else {"connected"},
            "observation_only":true,"observation_mode":f.mode,"map_bounds_xy_m":bounds,"vehicles":f.vehicles.iter().map(|v|json!({
                "vehicle_id":v.vehicle_id,"route_id":if f.mode=="dodge" {"cooperative dodge"} else if f.mode=="crossing" {"perpendicular approach"} else {"collision baseline"},"position_xy_m":[v.position_xyz_m[0],v.position_xyz_m[1]],
                "velocity_xy_mps":[v.velocity_xyz_mps[0],v.velocity_xyz_mps[1]],"heading_rad":v.forward_xyz[1].atan2(v.forward_xyz[0]),
                "length_m":v.length_m,"width_m":v.width_m,"damage":v.damage
            })).collect::<Vec<_>>(),"reservations":[],"rejected":0,"coalesced":0,"acknowledgements":{},"last_plan":null}),
        )
    }
}
fn bounds_for(f: &Frame) -> Value {
    if f.mode == "crossing" {
        // The seeded subjects approach the origin on perpendicular lanes.
        // Keep a stable extent so the live grid does not zoom as they move.
        return json!([[-75., -75.], [110., 110.]]);
    }
    let a = f.vehicles[0].position_xyz_m;
    let b = f.vehicles[1].position_xyz_m;
    json!([
        [a[0].min(b[0]) - 30., a[1].min(b[1]) - 10.],
        [a[0].max(b[0]) + 30., a[1].max(b[1]) + 10.]
    ])
}
pub fn scenario() -> Value {
    json!({"id":SCENARIO,"label":"Grid Plane — measured vehicle positions","map_id":"smallgrid","routes":[],"zone_half_extent_m":0})
}

#[cfg(test)]
mod tests {
    use super::*;
    fn frame(seq: u64, finished: bool) -> Frame {
        Frame {
            mode: "collision".into(),
            world_id: "headon-collision-test".into(),
            frame_seq: seq,
            sim_time_s: seq as f64,
            finished,
            vehicles: VEHICLE_IDS
                .iter()
                .enumerate()
                .map(|(i, id)| VehicleState {
                    vehicle_id: id.to_string(),
                    position_xyz_m: [0., if i == 0 { 50. } else { -50. }, 0.],
                    velocity_xyz_mps: [0., 0., 0.],
                    forward_xyz: [0., 1., 0.],
                    up_xyz: [0., 0., 1.],
                    sensor_sim_time_s: seq as f64,
                    length_m: 4.5,
                    width_m: 1.8,
                    enclosing_radius_m: 2.5,
                    damage: 0.,
                })
                .collect(),
        }
    }
    #[tokio::test]
    async fn observed_motion_has_no_plan_and_retains_fixed_grid_and_final_positions() {
        let hub = Hub::default();
        hub.publish(frame(0, false)).await.unwrap();
        let first = hub.snapshot().await.unwrap();
        let mut next = frame(1, true);
        next.vehicles[0].position_xyz_m[1] = 10.;
        hub.publish(next).await.unwrap();
        let last = hub.snapshot().await.unwrap();
        assert_eq!(last["vehicles"][0]["position_xy_m"][1], 10.);
        assert_eq!(first["map_bounds_xy_m"], last["map_bounds_xy_m"]);
        assert_eq!(last["status"], "disconnected");
        assert_eq!(last["observation_only"], true);
        assert!(last["last_plan"].is_null());
    }
    #[tokio::test]
    async fn dodge_observation_is_labelled_without_emitting_a_plan() {
        let hub = Hub::default();
        let mut dodge = frame(0, false);
        dodge.world_id = "headon-dodge-test".into();
        dodge.mode = "dodge".into();
        hub.publish(dodge).await.unwrap();
        let snapshot = hub.snapshot().await.unwrap();
        assert_eq!(snapshot["observation_mode"], "dodge");
        assert!(snapshot["last_plan"].is_null());
    }
    #[tokio::test]
    async fn crossing_observation_accepts_teammate_subject_ids_and_keeps_grid_bounds() {
        let hub = Hub::default();
        let mut crossing = frame(0, false);
        crossing.mode = "crossing".into();
        crossing.world_id = "crossing-observer-fresh_001-test".into();
        crossing.vehicles[0].vehicle_id = CROSSING_VEHICLE_IDS[0].into();
        crossing.vehicles[1].vehicle_id = CROSSING_VEHICLE_IDS[1].into();
        let template = crossing.vehicles[0].clone();
        crossing
            .vehicles
            .extend(CROSSING_VEHICLE_IDS[2..].iter().enumerate().map(|(i, id)| {
                let mut vehicle = template.clone();
                vehicle.vehicle_id = (*id).into();
                vehicle.position_xyz_m[0] = i as f64 * 12.;
                vehicle
            }));
        hub.publish(crossing).await.unwrap();
        let snapshot = hub.snapshot().await.unwrap();
        assert_eq!(snapshot["observation_mode"], "crossing");
        assert_eq!(
            snapshot["map_bounds_xy_m"],
            json!([[-75., -75.], [110., 110.]])
        );
        assert_eq!(
            snapshot["vehicles"][0]["route_id"],
            "perpendicular approach"
        );
        assert!(snapshot["last_plan"].is_null());
    }
    #[tokio::test]
    async fn rejects_old_frames_duplicates_and_competing_active_producer() {
        let hub = Hub::default();
        hub.publish(frame(1, false)).await.unwrap();
        assert!(hub.publish(frame(1, false)).await.is_err());
        let mut duplicate = frame(2, false);
        duplicate.vehicles[1].vehicle_id = VEHICLE_IDS[0].into();
        assert!(hub.publish(duplicate).await.is_err());
        let mut competing = frame(2, false);
        competing.world_id = "headon-collision-other".into();
        assert!(hub.publish(competing).await.is_err());
    }
}
