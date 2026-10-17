//! Bounded, deterministic planner for the plain Grid Plane two-Vivace experiment.
use crate::headon_protocol::*;
use std::collections::HashSet;
use std::time::{Duration, Instant};

pub struct Session {
    pub hello: Hello,
    pub session_id: String,
    pub last_plan: Option<ManeuverPlan>,
    pub last_frame: Option<Frame>,
    pub acknowledgements: HashSet<String>,
    pub halted: bool,
    pub last_received: Instant,
    initial: Option<Vec<VehicleState>>,
}

pub fn position(car: usize, offset: f64, progress: f64) -> [f64; 2] {
    let blend = if progress <= 5.0 {
        0.0
    } else if progress < 40.0 {
        let u = (progress - 5.0) / 35.0;
        u * u * (3.0 - 2.0 * u)
    } else if progress <= 65.0 {
        1.0
    } else if progress < 85.0 {
        let u = (progress - 65.0) / 20.0;
        1.0 - u * u * (3.0 - 2.0 * u)
    } else {
        0.0
    };
    [
        offset * blend,
        (55.0 - progress) * if car == 0 { 1.0 } else { -1.0 },
    ]
}
fn distance(a: [f64; 2], b: [f64; 2]) -> f64 {
    (a[0] - b[0]).hypot(a[1] - b[1])
}
fn xy(p: [f64; 3]) -> [f64; 2] {
    [p[0], p[1]]
}
fn speed(v: &VehicleState) -> f64 {
    v.velocity_xyz_mps.iter().map(|x| x * x).sum::<f64>().sqrt()
}
fn path_distance(p: [f64; 2], points: &[[f64; 2]]) -> f64 {
    points
        .windows(2)
        .map(|ab| {
            let dx = ab[1][0] - ab[0][0];
            let dy = ab[1][1] - ab[0][1];
            let n = dx * dx + dy * dy;
            let t = if n == 0.0 {
                0.0
            } else {
                (((p[0] - ab[0][0]) * dx + (p[1] - ab[0][1]) * dy) / n).clamp(0.0, 1.0)
            };
            distance(p, [ab[0][0] + t * dx, ab[0][1] + t * dy])
        })
        .fold(f64::INFINITY, f64::min)
}

impl Session {
    pub fn new(hello: Hello) -> Result<Self, String> {
        if hello.protocol_version != VERSION
            || hello.scenario_config_id != SCENARIO
            || hello.map_id != "smallgrid"
            || [&hello.world_id, &hello.world_epoch, &hello.bridge_id]
                .iter()
                .any(|s| !crate::protocol::valid_id(s))
            || ["path_origin_xy_v2", "sim_pause_fallback"]
                .iter()
                .any(|c| !hello.capabilities.iter().any(|s| s == c))
        {
            return Err("version, scenario, map, identity or capability mismatch".into());
        }
        Ok(Self {
            hello,
            session_id: uuid::Uuid::new_v4().to_string(),
            last_plan: None,
            last_frame: None,
            acknowledgements: HashSet::new(),
            halted: false,
            last_received: Instant::now(),
            initial: None,
        })
    }
    fn identity(&self, version: u32, world: &str, epoch: &str, session: &str) -> bool {
        version == VERSION
            && world == self.hello.world_id
            && epoch == self.hello.world_epoch
            && session == self.session_id
    }
    fn validate_frame(&self, f: &Frame) -> Result<Vec<VehicleState>, String> {
        if !self.identity(
            f.protocol_version,
            &f.world_id,
            &f.world_epoch,
            &f.session_id,
        ) || !f.sim_time_s.is_finite()
            || f.sim_time_s < 0.0
            || f.vehicles.len() != 2
            || self
                .last_frame
                .as_ref()
                .is_some_and(|last| f.frame_seq <= last.frame_seq || f.sim_time_s < last.sim_time_s)
        {
            return Err("wrong identity, time, sequence or incomplete vehicle set".into());
        }
        let mut vehicles = Vec::new();
        for id in VEHICLE_IDS {
            let matches: Vec<_> = f.vehicles.iter().filter(|v| v.vehicle_id == id).collect();
            if matches.len() != 1 {
                return Err("missing or duplicate controlled vehicle".into());
            }
            let v = matches[0];
            let finite = v
                .position_xyz_m
                .iter()
                .chain(v.velocity_xyz_mps.iter())
                .chain(v.forward_xyz.iter())
                .chain(v.up_xyz.iter())
                .all(|x| x.is_finite());
            let norm = |a: [f64; 3]| a.iter().map(|x| x * x).sum::<f64>().sqrt();
            if !finite
                || !v.sensor_sim_time_s.is_finite()
                || (v.sensor_sim_time_s - f.sim_time_s).abs() > 0.25
                || !v.length_m.is_finite()
                || !(3.5..=5.5).contains(&v.length_m)
                || !v.width_m.is_finite()
                || !(1.5..=2.5).contains(&v.width_m)
                || !v.enclosing_radius_m.is_finite()
                || v.enclosing_radius_m < 0.5 * v.length_m.hypot(v.width_m)
                || v.enclosing_radius_m > 4.0
                || !v.damage.is_finite()
                || v.damage < 0.0
                || speed(v) > 10.5
                || (norm(v.forward_xyz) - 1.0).abs() > 0.05
                || (norm(v.up_xyz) - 1.0).abs() > 0.05
                || v.position_xyz_m.iter().any(|x| x.abs() > 1000.0)
            {
                return Err("invalid vehicle geometry, state, speed or sensor time".into());
            }
            vehicles.push(v.clone());
        }
        if (vehicles[0].sensor_sim_time_s - vehicles[1].sensor_sim_time_s).abs() > 0.25 {
            return Err("sensor times differ by over 250ms".into());
        }
        Ok(vehicles)
    }
    fn create_plan(
        &mut self,
        f: &Frame,
        vehicles: &[VehicleState],
    ) -> Result<ManeuverPlan, String> {
        for (i, v) in vehicles.iter().enumerate() {
            let sign = if i == 0 { 1.0 } else { -1.0 };
            if speed(v) > 0.5
                || v.position_xyz_m[0].abs() > 0.3
                || (v.position_xyz_m[1] - 55.0 * sign).abs() > 0.5
                || v.position_xyz_m[2].abs() > 0.8
                || v.forward_xyz[1] * (-sign) < 0.98
                || v.up_xyz[2] < 0.95
                || v.damage > 5.0
            {
                return Err(
                    "initial state must be repaired, stopped and aligned at the configured starts"
                        .into(),
                );
            }
        }
        let radii = vehicles[0].enclosing_radius_m + vehicles[1].enclosing_radius_m;
        let offsets = [3.5, -3.5];
        let feasible = [-0.5, -0.25, 0.0, 0.25, 0.5].into_iter().all(|delay| {
            (0..=260).all(|s| {
                distance(
                    position(0, offsets[0], s as f64 / 2.0),
                    position(
                        1,
                        offsets[1],
                        (s as f64 / 2.0 + delay * TARGET_SPEED).clamp(0.0, 130.0),
                    ),
                ) > radii + 0.6
            })
        });
        if !feasible {
            self.halted = true;
        }
        self.initial = Some(vehicles.to_vec());
        Ok(ManeuverPlan {
            protocol_version: VERSION,
            world_id: f.world_id.clone(),
            world_epoch: f.world_epoch.clone(),
            session_id: self.session_id.clone(),
            scenario_config_id: SCENARIO.into(),
            based_on_frame_seq: f.frame_seq,
            plan_seq: 0,
            maneuver_id: uuid::Uuid::new_v4().to_string(),
            issued_sim_time_s: f.sim_time_s,
            valid_until_sim_time_s: f.sim_time_s + LEASE_S,
            wall_freshness_s: LEASE_S,
            status: if feasible { "prepare" } else { "pause" }.into(),
            reason: if feasible {
                "paired_left_paths"
            } else {
                "no_clearance_for_declared_vehicle_envelopes"
            }
            .into(),
            recommendations: VEHICLE_IDS
                .iter()
                .enumerate()
                .map(|(i, id)| PathRecommendation {
                    vehicle_id: id.to_string(),
                    speed_cap_mps: TARGET_SPEED,
                    action: "follow_path".into(),
                    reason: "coordinated_left".into(),
                    path_xy_m: (0..=65)
                        .map(|s| position(i, offsets[i], (s * 2) as f64))
                        .collect(),
                })
                .collect(),
        })
    }
    pub fn frame(&mut self, frame: Frame) -> Result<ManeuverPlan, String> {
        let vehicles = match self.validate_frame(&frame) {
            Ok(v) => v,
            Err(e) => {
                self.halted = true;
                return Err(e);
            }
        };
        let mut plan = if let Some(p) = &self.last_plan {
            p.clone()
        } else {
            self.create_plan(&frame, &vehicles)?
        };
        let mut reason = None;
        if self
            .last_plan
            .as_ref()
            .is_some_and(|p| p.status == "execute")
        {
            if let Some(last) = &self.last_frame {
                if frame.sim_time_s <= last.sim_time_s
                    || vehicles.iter().any(|v| {
                        last.vehicles
                            .iter()
                            .find(|old| old.vehicle_id == v.vehicle_id)
                            .is_none_or(|old| v.sensor_sim_time_s <= old.sensor_sim_time_s)
                    })
                {
                    reason = Some("simulation_time_not_advancing");
                }
            }
        }
        if self
            .last_plan
            .as_ref()
            .is_some_and(|p| p.status == "execute")
            && self.last_received.elapsed() > Duration::from_secs_f64(LEASE_S)
        {
            reason = Some("telemetry_lease_expired");
        }
        for (i, v) in vehicles.iter().enumerate() {
            let initial = &self.initial.as_ref().unwrap()[i];
            if (v.enclosing_radius_m - initial.enclosing_radius_m).abs() > 0.001
                || (v.length_m - initial.length_m).abs() > 0.001
                || (v.width_m - initial.width_m).abs() > 0.001
            {
                reason = Some("vehicle_geometry_changed");
            }
            if v.damage > initial.damage + 5.0 {
                reason = Some("new_damage");
            }
            if v.up_xyz[2] < 0.9 {
                reason = Some("unstable_vehicle");
            }
            if path_distance(xy(v.position_xyz_m), &plan.recommendations[i].path_xy_m) > 1.25 {
                reason = Some("path_deviation");
            }
        }
        let relative = [
            vehicles[0].position_xyz_m[0] - vehicles[1].position_xyz_m[0],
            vehicles[0].position_xyz_m[1] - vehicles[1].position_xyz_m[1],
        ];
        let velocity = [
            vehicles[0].velocity_xyz_mps[0] - vehicles[1].velocity_xyz_mps[0],
            vehicles[0].velocity_xyz_mps[1] - vehicles[1].velocity_xyz_mps[1],
        ];
        let vv = velocity.iter().map(|v| v * v).sum::<f64>();
        let t = if vv > 0.0 {
            (-(relative[0] * velocity[0] + relative[1] * velocity[1]) / vv).clamp(0.0, 1.0)
        } else {
            0.0
        };
        if (relative[0] + t * velocity[0]).hypot(relative[1] + t * velocity[1])
            <= vehicles[0].enclosing_radius_m + vehicles[1].enclosing_radius_m + 0.2
        {
            reason = Some("imminent_overlap");
        }
        if let Some(reason) = reason {
            self.halted = true;
            plan.reason = reason.into();
        }
        plan.status = if self.halted {
            "pause"
        } else if plan.status == "complete"
            || (self.acknowledgements.len() == 2
                && vehicles[0].position_xyz_m[1] < -32.0
                && vehicles[1].position_xyz_m[1] > 32.0
                && vehicles.iter().all(|v| v.position_xyz_m[0].abs() < 1.0))
        {
            "complete"
        } else if self.acknowledgements.len() == 2 {
            "execute"
        } else {
            "prepare"
        }
        .into();
        if plan.status == "pause" || plan.status == "complete" {
            for r in &mut plan.recommendations {
                r.action = "pause".into();
                r.speed_cap_mps = 0.0;
            }
        }
        plan.plan_seq += 1;
        plan.based_on_frame_seq = frame.frame_seq;
        plan.issued_sim_time_s = frame.sim_time_s;
        plan.valid_until_sim_time_s = frame.sim_time_s + LEASE_S;
        self.last_frame = Some(frame);
        self.last_received = Instant::now();
        self.last_plan = Some(plan.clone());
        Ok(plan)
    }
    pub fn ack(&mut self, ack: Ack) -> Result<(), String> {
        let Some(p) = &self.last_plan else {
            return Err("no maneuver prepared".into());
        };
        if !self.identity(
            ack.protocol_version,
            &ack.world_id,
            &ack.world_epoch,
            &ack.session_id,
        ) || ack.plan_seq != p.plan_seq
            || ack.maneuver_id != p.maneuver_id
            || !VEHICLE_IDS.contains(&ack.vehicle_id.as_str())
            || !["accepted", "rejected"].contains(&ack.status.as_str())
            || ack.reason.as_ref().is_some_and(|s| s.len() > 256)
        {
            return Err("wrong identity, maneuver, plan or acknowledgement".into());
        }
        if ack.status == "rejected" {
            self.halted = true;
        } else {
            self.acknowledgements.insert(ack.vehicle_id);
        }
        Ok(())
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    fn session() -> Session {
        Session::new(Hello {
            protocol_version: 2,
            world_id: "test-world".into(),
            world_epoch: "reset-1".into(),
            scenario_config_id: SCENARIO.into(),
            bridge_id: "test-bridge".into(),
            map_id: "smallgrid".into(),
            capabilities: vec!["path_origin_xy_v2".into(), "sim_pause_fallback".into()],
        })
        .unwrap()
    }
    fn frame(s: &Session, seq: u64) -> Frame {
        Frame {
            protocol_version: 2,
            world_id: s.hello.world_id.clone(),
            world_epoch: s.hello.world_epoch.clone(),
            session_id: s.session_id.clone(),
            frame_seq: seq,
            sim_time_s: 10.0,
            vehicles: VEHICLE_IDS
                .iter()
                .enumerate()
                .map(|(i, id)| {
                    let sign = if i == 0 { 1.0 } else { -1.0 };
                    VehicleState {
                        vehicle_id: id.to_string(),
                        position_xyz_m: [0., 55. * sign, 0.2],
                        velocity_xyz_mps: [0., 0., 0.],
                        forward_xyz: [0., -sign, 0.],
                        up_xyz: [0., 0., 1.],
                        sensor_sim_time_s: 10.,
                        length_m: 4.5,
                        width_m: 2.02,
                        enclosing_radius_m: 2.8,
                        damage: 0.,
                    }
                })
                .collect(),
        }
    }
    fn accept(s: &mut Session, vehicle: &str) -> Result<(), String> {
        let p = s.last_plan.as_ref().unwrap();
        s.ack(Ack {
            protocol_version: 2,
            world_id: p.world_id.clone(),
            world_epoch: p.world_epoch.clone(),
            session_id: p.session_id.clone(),
            plan_seq: p.plan_seq,
            maneuver_id: p.maneuver_id.clone(),
            vehicle_id: vehicle.into(),
            status: "accepted".into(),
            reason: None,
        })
    }
    #[test]
    fn prepares_two_separated_paths_then_leases_same_paths_only_after_both_acks() {
        let mut s = session();
        let f = frame(&s, 0);
        let p = s.frame(f).unwrap();
        assert_eq!(p.status, "prepare");
        assert_eq!(p.recommendations.len(), 2);
        assert!(p.recommendations[0].path_xy_m.iter().any(|p| p[0] > 3.4));
        assert!(p.recommendations[1].path_xy_m.iter().any(|p| p[0] < -3.4));
        accept(&mut s, VEHICLE_IDS[0]).unwrap();
        let f = frame(&s, 1);
        assert_eq!(s.frame(f).unwrap().status, "prepare");
        accept(&mut s, VEHICLE_IDS[1]).unwrap();
        let f = frame(&s, 2);
        let next = s.frame(f).unwrap();
        assert_eq!(next.status, "execute");
        assert_eq!(next.maneuver_id, p.maneuver_id);
        assert_eq!(
            next.recommendations[0].path_xy_m,
            p.recommendations[0].path_xy_m
        );
        assert!(next.valid_until_sim_time_s - next.issued_sim_time_s <= 0.5);
    }
    #[test]
    fn rejects_wrong_version_map_or_missing_capability() {
        let s = session();
        let mut h = s.hello.clone();
        h.protocol_version = 1;
        assert!(Session::new(h).is_err());
        let mut h = s.hello.clone();
        h.map_id = "west_coast_usa".into();
        assert!(Session::new(h).is_err());
        let mut h = s.hello;
        h.capabilities.clear();
        assert!(Session::new(h).is_err());
    }
    #[test]
    fn rejects_incomplete_duplicate_old_and_wrong_session_frames() {
        for kind in 0..5 {
            let mut s = session();
            let f = frame(&s, 0);
            s.frame(f).unwrap();
            let mut f = frame(&s, 1);
            match kind {
                0 => {
                    f.vehicles.pop();
                }
                1 => f.vehicles[1].vehicle_id = VEHICLE_IDS[0].into(),
                2 => f.frame_seq = 0,
                3 => f.session_id = "other".into(),
                _ => f.sim_time_s = 9.,
            }
            assert!(s.frame(f).is_err());
        }
    }
    #[test]
    fn cannot_start_from_moving_misaligned_or_damaged_state() {
        for kind in 0..5 {
            let mut s = session();
            let mut f = frame(&s, 0);
            match kind {
                0 => f.vehicles[0].velocity_xyz_mps[1] = -4.,
                1 => f.vehicles[0].position_xyz_m[0] = 3.,
                2 => f.vehicles[0].damage = 50.,
                3 => f.vehicles[0].forward_xyz[1] = 1.,
                _ => f.vehicles[0].enclosing_radius_m = 1.,
            }
            assert!(s.frame(f).is_err());
        }
    }
    #[test]
    fn unsafe_motion_latches_pause_and_does_not_replan() {
        let mut s = session();
        let f = frame(&s, 0);
        let p = s.frame(f).unwrap();
        accept(&mut s, VEHICLE_IDS[0]).unwrap();
        accept(&mut s, VEHICLE_IDS[1]).unwrap();
        let mut f = frame(&s, 1);
        f.vehicles[0].damage = 20.;
        let out = s.frame(f).unwrap();
        assert_eq!(out.status, "pause");
        let f = frame(&s, 2);
        let out = s.frame(f).unwrap();
        assert_eq!(out.status, "pause");
        assert_eq!(out.maneuver_id, p.maneuver_id);
    }
    #[test]
    fn stale_telemetry_cannot_renew_execution_lease() {
        let mut s = session();
        let f = frame(&s, 0);
        s.frame(f).unwrap();
        accept(&mut s, VEHICLE_IDS[0]).unwrap();
        accept(&mut s, VEHICLE_IDS[1]).unwrap();
        let f = frame(&s, 1);
        s.frame(f).unwrap();
        s.last_received = Instant::now() - Duration::from_secs(1);
        let f = frame(&s, 2);
        assert_eq!(s.frame(f).unwrap().status, "pause");
    }
    #[test]
    fn frozen_execution_telemetry_cannot_renew_permission() {
        let mut s = session();
        let f = frame(&s, 0);
        s.frame(f).unwrap();
        accept(&mut s, VEHICLE_IDS[0]).unwrap();
        accept(&mut s, VEHICLE_IDS[1]).unwrap();
        let f = frame(&s, 1);
        assert_eq!(s.frame(f).unwrap().status, "execute");
        let f = frame(&s, 2);
        let paused = s.frame(f).unwrap();
        assert_eq!(paused.status, "pause");
        assert_eq!(paused.reason, "simulation_time_not_advancing");
    }
    #[test]
    fn rejects_wrong_ack_maneuver_and_unknown_vehicle() {
        let mut s = session();
        let f = frame(&s, 0);
        s.frame(f).unwrap();
        assert!(accept(&mut s, "stranger").is_err());
        let p = s.last_plan.clone().unwrap();
        let a = Ack {
            protocol_version: 2,
            world_id: p.world_id,
            world_epoch: p.world_epoch,
            session_id: p.session_id,
            plan_seq: p.plan_seq,
            maneuver_id: "old".into(),
            vehicle_id: VEHICLE_IDS[0].into(),
            status: "accepted".into(),
            reason: None,
        };
        assert!(s.ack(a).is_err());
    }
    #[test]
    fn completes_only_after_both_cars_pass_and_return() {
        let mut s = session();
        let f = frame(&s, 0);
        s.frame(f).unwrap();
        accept(&mut s, VEHICLE_IDS[0]).unwrap();
        accept(&mut s, VEHICLE_IDS[1]).unwrap();
        let mut f = frame(&s, 1);
        f.vehicles[0].position_xyz_m = [0., -33., 0.2];
        f.vehicles[1].position_xyz_m = [0., 33., 0.2];
        assert_eq!(s.frame(f).unwrap().status, "complete");
    }
}
