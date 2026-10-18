use serde::{Deserialize, Serialize};

pub const VERSION: u32 = 1;

#[derive(Clone, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum Incoming {
    Hello {
        protocol_version: u32,
        world_id: String,
        world_epoch: String,
        scenario_config_id: String,
        bridge_id: String,
    },
    StateBatch {
        protocol_version: u32,
        world_id: String,
        world_epoch: String,
        session_id: String,
        frame_seq: u64,
        sim_time_s: f64,
        scenario_config_id: String,
        vehicles: Vec<Vehicle>,
    },
    AppliedResult {
        protocol_version: u32,
        world_id: String,
        world_epoch: String,
        session_id: String,
        plan_seq: u64,
        vehicle_id: String,
        status: String,
        applied_speed_cap_mps: Option<f64>,
        rejection_reason: Option<String>,
    },
    VehicleRemoved {
        protocol_version: u32,
        world_id: String,
        world_epoch: String,
        session_id: String,
        vehicle_id: String,
        reason: String,
    },
}

#[derive(Clone, Serialize, Deserialize)]
pub struct Vehicle {
    pub vehicle_id: String,
    pub route_id: String,
    pub position_xy_m: [f64; 2],
    pub velocity_xy_mps: [f64; 2],
    /// Optional for existing crossing-v1 producers; acceleration is SI world XY.
    #[serde(default)]
    pub acceleration_xy_mps2: [f64; 2],
    pub heading_rad: f64,
    pub length_m: f64,
    pub width_m: f64,
}

#[derive(Clone, Serialize)]
pub struct Recommendation {
    pub vehicle_id: String,
    pub speed_cap_mps: f64,
    pub action: String,
    pub reason: String,
    pub reservation_id: Option<String>,
    pub entry_window_sim_s: Option<[f64; 2]>,
}

#[derive(Clone, Serialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum Outgoing {
    HelloAck {
        protocol_version: u32,
        world_id: String,
        world_epoch: String,
        session_id: String,
        status: String,
        advice_horizon_sim_s: f64,
        wall_freshness_s: f64,
    },
    RecommendationBatch {
        protocol_version: u32,
        world_id: String,
        world_epoch: String,
        session_id: String,
        based_on_frame_seq: u64,
        plan_seq: u64,
        issued_sim_time_s: f64,
        valid_until_sim_time_s: f64,
        status: String,
        recommendations: Vec<Recommendation>,
        #[serde(skip_serializing_if = "Option::is_none")]
        ml_predictions: Option<crate::ml::PredictionBatch>,
    },
    Error {
        code: String,
        detail: String,
    },
}

pub fn valid_id(s: &str) -> bool {
    !s.is_empty()
        && s.len() <= 96
        && s.bytes()
            .all(|b| b.is_ascii_alphanumeric() || matches!(b, b'-' | b'_' | b'.'))
}

pub fn valid_vehicle(v: &Vehicle, max_speed: f64) -> bool {
    valid_id(&v.vehicle_id)
        && valid_id(&v.route_id)
        && v.position_xy_m
            .iter()
            .all(|x| x.is_finite() && x.abs() <= 100_000.0)
        && v.velocity_xy_mps
            .iter()
            .all(|x| x.is_finite() && x.abs() <= max_speed * 2.0)
        && v.acceleration_xy_mps2
            .iter()
            .all(|x| x.is_finite() && x.abs() <= 50.0)
        && v.heading_rad.is_finite()
        && v.heading_rad.abs() <= 100.0
        && v.length_m.is_finite()
        && (1.0..=30.0).contains(&v.length_m)
        && v.width_m.is_finite()
        && (0.5..=10.0).contains(&v.width_m)
}

#[cfg(test)]
mod crossing_tests {
    use super::*;
    #[test]
    fn legacy_velocity_only_telemetry_defaults_acceleration_and_rejects_bad_acceleration() {
        let mut frame: serde_json::Value =
            serde_json::from_str(include_str!("../examples/state_batch.json")).unwrap();
        frame["vehicles"][0]
            .as_object_mut()
            .unwrap()
            .remove("acceleration_xy_mps2");
        let mut v: Vehicle = serde_json::from_value(frame["vehicles"][0].clone()).unwrap();
        assert_eq!(v.acceleration_xy_mps2, [0.0, 0.0]);
        assert!(valid_vehicle(&v, 12.0));
        v.acceleration_xy_mps2 = [f64::NAN, 0.0];
        assert!(!valid_vehicle(&v, 12.0));
        v.acceleration_xy_mps2 = [51.0, 0.0];
        assert!(!valid_vehicle(&v, 12.0));
    }
}
