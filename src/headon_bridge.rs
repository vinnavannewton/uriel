//! Dedicated maneuver-v2 WebSocket; legacy /ws/bridge is unchanged.
use crate::{headon::Session, headon_protocol::*};
use axum::extract::ws::{Message, WebSocket};
use serde_json::{json, Value};
use std::{
    collections::HashMap,
    sync::Arc,
    time::{Duration, Instant},
};
use tokio::sync::{mpsc, Mutex};

#[derive(Clone, Default)]
pub struct Hub(Arc<Mutex<HashMap<String, Entry>>>);
struct Entry {
    owner: Option<String>,
    epoch: String,
    snapshot: Value,
    received: Instant,
}

impl Hub {
    async fn register(&self, session: &Session, owner: &str) -> Result<(), String> {
        let mut entries = self.0.lock().await;
        if let Some(prior) = entries.get(&session.hello.world_id) {
            if prior.owner.is_some() {
                return Err("world already has an active bridge".into());
            }
            if prior.epoch == session.hello.world_epoch {
                return Err("reconnection requires a new reset epoch".into());
            }
        }
        entries.insert(
            session.hello.world_id.clone(),
            Entry {
                owner: Some(owner.into()),
                epoch: session.hello.world_epoch.clone(),
                snapshot: snapshot(session),
                received: Instant::now(),
            },
        );
        Ok(())
    }
    async fn update(&self, session: &Session, owner: &str, disconnected: bool) {
        let mut entries = self.0.lock().await;
        if let Some(entry) = entries.get_mut(&session.hello.world_id) {
            if entry.owner.as_deref() != Some(owner) {
                return;
            }
            entry.snapshot = snapshot(session);
            entry.received = session.last_received;
            if disconnected {
                entry.owner = None;
            }
        }
    }
    pub async fn snapshots(&self) -> Vec<Value> {
        self.0
            .lock()
            .await
            .values()
            .map(|entry| {
                let mut s = entry.snapshot.clone();
                let age = entry.received.elapsed().as_millis();
                s["wall_age_ms"] = json!(age);
                s["status"] = json!(if entry.owner.is_none() {
                    "disconnected"
                } else if age > 500 {
                    "stale"
                } else {
                    "connected"
                });
                s
            })
            .collect()
    }
    pub async fn get(&self, id: &str) -> Option<Value> {
        self.snapshots()
            .await
            .into_iter()
            .find(|s| s["world_id"] == id)
    }
}
fn snapshot(s: &Session) -> Value {
    json!({"world_id":s.hello.world_id,"world_epoch":s.hello.world_epoch,"bridge_id":s.hello.bridge_id,
        "scenario_config_id":SCENARIO,"protocol_version":VERSION,"frame_seq":s.last_frame.as_ref().map(|f|f.frame_seq),
        "sim_time_s":s.last_frame.as_ref().map_or(0.0,|f|f.sim_time_s),"wall_age_ms":0,"status":"connected",
        "vehicles":s.last_frame.as_ref().map(|f|f.vehicles.iter().enumerate().map(|(i,v)|json!({
            "vehicle_id":v.vehicle_id,"route_id":if v.vehicle_id==VEHICLE_IDS[0] {"north-south"} else {"south-north"},
            "position_xy_m":[v.position_xyz_m[0],v.position_xyz_m[1]],"velocity_xy_mps":[v.velocity_xyz_mps[0],v.velocity_xyz_mps[1]],
            "heading_rad":v.forward_xyz[1].atan2(v.forward_xyz[0]),"length_m":v.length_m,"width_m":v.width_m,"order":i
        })).collect::<Vec<_>>()).unwrap_or_default(),"reservations":[],"rejected":0,"coalesced":0,
        "acknowledgements":s.acknowledgements.iter().map(|k|(k,"accepted")).collect::<HashMap<_,_>>(),
        "last_plan":s.last_plan.as_ref().map(|p|Outgoing::ManeuverPlan(p.clone()))})
}

pub fn scenario() -> Value {
    json!({"id":SCENARIO,"label":"Plain Grid Plane: two-car coordinated head-on pass (algorithm only)",
        "zone_half_extent_m":5,"routes": [
            {"id":"north-south","points_xy_m":[[0,55],[0,-75]]},
            {"id":"south-north","points_xy_m":[[0,-55],[0,75]]}
        ],"map_id":"smallgrid","protocol_version":VERSION,"obstacles":[],"learned_model":null})
}
fn record(records: &mpsc::Sender<Value>, kind: &str, data: Value) {
    if records.try_send(json!({"kind":kind,"data":data})).is_err() {
        tracing::warn!("head-on recording queue unavailable");
    }
}
async fn send(socket: &mut WebSocket, out: &Outgoing) -> Result<(), ()> {
    let text = serde_json::to_string(out).map_err(|_| ())?;
    tokio::time::timeout(
        Duration::from_millis(250),
        socket.send(Message::Text(text.into())),
    )
    .await
    .map_err(|_| ())?
    .map_err(|_| ())
}

pub async fn serve(mut socket: WebSocket, hub: Hub, records: mpsc::Sender<Value>) {
    let owner = uuid::Uuid::new_v4().to_string();
    let mut session: Option<Session> = None;
    loop {
        let timeout = if session
            .as_ref()
            .and_then(|s| s.last_plan.as_ref())
            .is_some_and(|p| p.status == "execute")
        {
            750
        } else {
            5000
        };
        let message = tokio::time::timeout(Duration::from_millis(timeout), socket.recv()).await;
        let text = match message {
            Ok(Some(Ok(Message::Text(text)))) => text,
            Ok(Some(Ok(Message::Ping(_) | Message::Pong(_)))) => continue,
            Err(_) => {
                let _ = send(
                    &mut socket,
                    &Outgoing::Error {
                        code: "telemetry_timeout".into(),
                        detail: "maneuver session timed out; pause simulator".into(),
                    },
                )
                .await;
                break;
            }
            _ => break,
        };
        let incoming = match serde_json::from_str::<Incoming>(&text) {
            Ok(v) => v,
            Err(e) => {
                let _ = send(
                    &mut socket,
                    &Outgoing::Error {
                        code: "invalid_message".into(),
                        detail: e.to_string(),
                    },
                )
                .await;
                break;
            }
        };
        let response: Result<Outgoing, String> = match incoming {
            Incoming::Hello(hello) => {
                if session.is_some() {
                    Err("session already registered".into())
                } else {
                    match Session::new(hello) {
                        Err(e) => Err(e),
                        Ok(s) => match hub.register(&s, &owner).await {
                            Err(e) => Err(e),
                            Ok(()) => {
                                let out = Outgoing::HelloAck {
                                    protocol_version: VERSION,
                                    world_id: s.hello.world_id.clone(),
                                    world_epoch: s.hello.world_epoch.clone(),
                                    session_id: s.session_id.clone(),
                                    scenario_config_id: SCENARIO.into(),
                                    advice_horizon_sim_s: LEASE_S,
                                    wall_freshness_s: LEASE_S,
                                    status: "ready".into(),
                                };
                                record(
                                    &records,
                                    "headon_hello",
                                    json!({"world_id":s.hello.world_id,"world_epoch":s.hello.world_epoch,"session_id":s.session_id,"protocol_version":VERSION}),
                                );
                                session = Some(s);
                                Ok(out)
                            }
                        },
                    }
                }
            }
            Incoming::HeadonState(frame) => match session.as_mut() {
                None => Err("hello required before telemetry".into()),
                Some(s) => {
                    let input = json!({"world_id":frame.world_id,"world_epoch":frame.world_epoch,"session_id":frame.session_id,
                        "frame_seq":frame.frame_seq,"sim_time_s":frame.sim_time_s,"vehicles":frame.vehicles});
                    match s.frame(frame) {
                        Err(e) => Err(e),
                        Ok(plan) => {
                            record(&records, "headon_telemetry", input);
                            record(&records, "headon_plan", json!(&plan));
                            hub.update(s, &owner, false).await;
                            Ok(Outgoing::ManeuverPlan(plan))
                        }
                    }
                }
            },
            Incoming::ManeuverAck(ack) => match session.as_mut() {
                None => Err("hello required before acknowledgement".into()),
                Some(s) => {
                    let id = ack.vehicle_id.clone();
                    let status = ack.status.clone();
                    let input = json!({"world_id":ack.world_id,"world_epoch":ack.world_epoch,"session_id":ack.session_id,
                        "plan_seq":ack.plan_seq,"maneuver_id":ack.maneuver_id,"vehicle_id":id,"status":status,"reason":ack.reason});
                    match s.ack(ack) {
                        Err(e) => Err(e),
                        Ok(()) => {
                            record(&records, "headon_maneuver_ack", input);
                            hub.update(s, &owner, false).await;
                            Ok(Outgoing::AckResult {
                                vehicle_id: id,
                                status,
                            })
                        }
                    }
                }
            },
        };
        match response {
            Ok(out) => {
                if send(&mut socket, &out).await.is_err() {
                    break;
                }
            }
            Err(detail) => {
                record(&records, "headon_rejected", json!({"detail":detail}));
                let _ = send(
                    &mut socket,
                    &Outgoing::Error {
                        code: "headon_rejected".into(),
                        detail,
                    },
                )
                .await;
                break;
            }
        }
    }
    if let Some(s) = session {
        hub.update(&s, &owner, true).await;
        record(
            &records,
            "headon_disconnect",
            json!({"world_id":s.hello.world_id,"world_epoch":s.hello.world_epoch,"session_id":s.session_id,
            "last_status":s.last_plan.as_ref().map(|p|&p.status)}),
        );
    }
}
