use crate::{
    coordinator::Reservation,
    protocol::{Outgoing, Vehicle},
    scenario::Scenario,
};
use serde::Serialize;
use std::{
    collections::{HashMap, VecDeque},
    time::Instant,
};

#[derive(Clone, Copy)]
pub struct SpeedSample {
    pub sim_time_s: f64,
    pub forward_speed_mps: f64,
}

pub struct World {
    pub world_id: String,
    pub epoch: String,
    pub session_id: String,
    pub bridge_id: String,
    pub owner_id: String,
    pub scenario_id: String,
    pub last_frame_seq: Option<u64>,
    pub plan_seq: u64,
    pub sim_time_s: f64,
    pub last_received: Instant,
    pub vehicles: Vec<Vehicle>,
    pub first_seen: HashMap<String, u64>,
    pub reservations: Vec<Reservation>,
    pub last_plan: Option<Outgoing>,
    pub acknowledgements: HashMap<String, String>,
    pub computing: bool,
    pub pending: Option<(u64, f64, Vec<Vehicle>)>,
    pub rejected: u64,
    pub coalesced: u64,
    pub speed_history: HashMap<String, VecDeque<SpeedSample>>,
}

#[derive(Serialize)]
pub struct WorldSnapshot {
    pub world_id: String,
    pub world_epoch: String,
    pub bridge_id: String,
    pub scenario_config_id: String,
    pub frame_seq: Option<u64>,
    pub sim_time_s: f64,
    pub wall_age_ms: u128,
    pub status: &'static str,
    pub vehicles: Vec<Vehicle>,
    pub reservations: Vec<Reservation>,
    pub last_plan: Option<Outgoing>,
    pub acknowledgements: HashMap<String, String>,
    pub rejected: u64,
    pub coalesced: u64,
}

impl World {
    pub fn new(
        world_id: String,
        epoch: String,
        session_id: String,
        bridge_id: String,
        owner_id: String,
        scenario: &Scenario,
    ) -> Self {
        Self {
            world_id,
            epoch,
            session_id,
            bridge_id,
            owner_id,
            scenario_id: scenario.id.clone(),
            last_frame_seq: None,
            plan_seq: 0,
            sim_time_s: 0.0,
            last_received: Instant::now(),
            vehicles: vec![],
            first_seen: HashMap::new(),
            reservations: vec![],
            last_plan: None,
            acknowledgements: HashMap::new(),
            computing: false,
            pending: None,
            rejected: 0,
            coalesced: 0,
            speed_history: HashMap::new(),
        }
    }
    pub fn snapshot(&self) -> WorldSnapshot {
        let age = self.last_received.elapsed().as_millis();
        WorldSnapshot {
            world_id: self.world_id.clone(),
            world_epoch: self.epoch.clone(),
            bridge_id: self.bridge_id.clone(),
            scenario_config_id: self.scenario_id.clone(),
            frame_seq: self.last_frame_seq,
            sim_time_s: self.sim_time_s,
            wall_age_ms: age,
            status: if age > 500 { "stale" } else { "connected" },
            vehicles: self.vehicles.clone(),
            reservations: self.reservations.clone(),
            last_plan: self.last_plan.clone(),
            acknowledgements: self.acknowledgements.clone(),
            rejected: self.rejected,
            coalesced: self.coalesced,
        }
    }
}
