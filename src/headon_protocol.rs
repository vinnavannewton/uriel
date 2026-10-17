//! Version 2 maneuver contract. The legacy crossing protocol remains version 1.
use serde::{Deserialize, Serialize};

pub const VERSION: u32 = 2;
pub const SCENARIO: &str = "headon-grid-v2";
pub const VEHICLE_IDS: [&str; 2] = ["thePlayer", "uriel_blue"];
pub const LEASE_S: f64 = 0.5;
pub const TARGET_SPEED: f64 = 30.0 / 3.6;

#[derive(Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Hello {
    pub protocol_version: u32,
    pub world_id: String,
    pub world_epoch: String,
    pub scenario_config_id: String,
    pub bridge_id: String,
    pub map_id: String,
    pub capabilities: Vec<String>,
}

#[derive(Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct VehicleState {
    pub vehicle_id: String,
    pub position_xyz_m: [f64; 3],
    pub velocity_xyz_mps: [f64; 3],
    pub forward_xyz: [f64; 3],
    pub up_xyz: [f64; 3],
    pub sensor_sim_time_s: f64,
    pub length_m: f64,
    pub width_m: f64,
    pub enclosing_radius_m: f64,
    pub damage: f64,
}

#[derive(Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Frame {
    pub protocol_version: u32,
    pub world_id: String,
    pub world_epoch: String,
    pub session_id: String,
    pub frame_seq: u64,
    pub sim_time_s: f64,
    pub vehicles: Vec<VehicleState>,
}

#[derive(Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Ack {
    pub protocol_version: u32,
    pub world_id: String,
    pub world_epoch: String,
    pub session_id: String,
    pub plan_seq: u64,
    pub maneuver_id: String,
    pub vehicle_id: String,
    /// "accepted" means the controller accepted the path, not achieved motion.
    pub status: String,
    pub reason: Option<String>,
}

#[derive(Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum Incoming {
    Hello(Hello),
    HeadonState(Frame),
    ManeuverAck(Ack),
}

#[derive(Clone, Serialize)]
pub struct PathRecommendation {
    pub vehicle_id: String,
    pub speed_cap_mps: f64,
    pub action: String,
    pub reason: String,
    /// Paths refer to the vehicle origin. The bridge converts to BeamNG front nodes.
    pub path_xy_m: Vec<[f64; 2]>,
}

#[derive(Clone, Serialize)]
pub struct ManeuverPlan {
    pub protocol_version: u32,
    pub world_id: String,
    pub world_epoch: String,
    pub session_id: String,
    pub scenario_config_id: String,
    pub based_on_frame_seq: u64,
    pub plan_seq: u64,
    pub maneuver_id: String,
    pub issued_sim_time_s: f64,
    pub valid_until_sim_time_s: f64,
    pub wall_freshness_s: f64,
    /// prepare (remain paused), execute (fresh lease), pause, or complete.
    pub status: String,
    pub reason: String,
    pub recommendations: Vec<PathRecommendation>,
}

#[derive(Serialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum Outgoing {
    HelloAck {
        protocol_version: u32,
        world_id: String,
        world_epoch: String,
        session_id: String,
        scenario_config_id: String,
        advice_horizon_sim_s: f64,
        wall_freshness_s: f64,
        status: String,
    },
    ManeuverPlan(ManeuverPlan),
    AckResult {
        vehicle_id: String,
        status: String,
    },
    Error {
        code: String,
        detail: String,
    },
}
