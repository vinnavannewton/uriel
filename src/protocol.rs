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
        && v.heading_rad.is_finite()
        && v.heading_rad.abs() <= 100.0
        && v.length_m.is_finite()
        && (1.0..=30.0).contains(&v.length_m)
        && v.width_m.is_finite()
        && (0.5..=10.0).contains(&v.width_m)
}
