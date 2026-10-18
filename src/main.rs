mod collision_observer;
mod conflict_resolution;
mod coordinator;
mod headon;
mod headon_bridge;
mod headon_protocol;
mod protocol;
mod scenario;
mod world;

use axum::{
    extract::{
        ws::{Message, WebSocket, WebSocketUpgrade},
        Path, State,
    },
    http::{header, HeaderMap, StatusCode},
    response::{Html, IntoResponse},
    routing::get,
    Json, Router,
};
use futures_util::{SinkExt, StreamExt};
use protocol::{Incoming, Outgoing, VERSION};
use scenario::Scenario;
use serde_json::{json, Value};
use std::{
    collections::{HashMap, HashSet},
    net::SocketAddr,
    path::PathBuf,
    sync::Arc,
    time::Instant,
};
use tokio::{
    fs::OpenOptions,
    io::AsyncWriteExt,
    sync::{mpsc, Mutex, Semaphore},
};
use tracing::{error, info, warn};
use uuid::Uuid;
use world::World;

#[derive(Clone)]
struct App {
    worlds: Arc<Mutex<HashMap<String, Arc<Mutex<World>>>>>,
    scenario: Scenario,
    token: Option<String>,
    compute: Arc<Semaphore>,
    records: mpsc::Sender<Value>,
    started: Instant,
    headon: headon_bridge::Hub,
    collision: collision_observer::Hub,
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "arc_angel=info".into()),
        )
        .init();
    let scenario_path =
        std::env::var("ARC_SCENARIO").unwrap_or_else(|_| "scenarios/crossing-v1.json".into());
    let scenario = Scenario::load(&scenario_path)?;
    let run_dir = PathBuf::from(std::env::var("ARC_RUN_DIR").unwrap_or_else(|_| "runs".into()))
        .join(Uuid::new_v4().to_string());
    tokio::fs::create_dir_all(&run_dir).await?;
    tokio::fs::write(run_dir.join("metadata.json"), serde_json::to_vec_pretty(&json!({"scenario":scenario,"protocol_version":VERSION,"build_version":env!("CARGO_PKG_VERSION")}))?).await?;
    let (tx, rx) = mpsc::channel(4096);
    tokio::spawn(record_writer(run_dir.join("events.jsonl"), rx));
    let app = App {
        worlds: Arc::new(Mutex::new(HashMap::new())),
        scenario,
        token: std::env::var("ARC_TOKEN").ok().filter(|s| !s.is_empty()),
        compute: Arc::new(Semaphore::new(4)),
        records: tx,
        started: Instant::now(),
        headon: headon_bridge::Hub::default(),
        collision: collision_observer::Hub::default(),
    };
    let router = Router::new()
        .route(
            "/",
            get(|| async { Html(include_str!("../web/index.html")) }),
        )
        .route(
            "/app.js",
            get(|| async {
                (
                    [(header::CONTENT_TYPE, "text/javascript")],
                    include_str!("../web/app.js"),
                )
            }),
        )
        .route(
            "/style.css",
            get(|| async {
                (
                    [(header::CONTENT_TYPE, "text/css")],
                    include_str!("../web/style.css"),
                )
            }),
        )
        .route("/health", get(|| async { Json(json!({"status":"ok"})) }))
        .route("/api/status", get(status))
        .route("/api/worlds", get(worlds))
        .route("/api/worlds/{id}", get(world_detail))
        .route("/api/scenarios/{id}", get(scenario_detail))
        .route(
            "/api/conflicts/evaluate",
            axum::routing::post(conflict_evaluate),
        )
        .route(
            "/api/conflicts/command-result",
            axum::routing::post(conflict_command_result),
        )
        .route("/ws/bridge", get(bridge_upgrade))
        .route("/ws/headon", get(headon_upgrade))
        .route(
            "/api/collision/telemetry",
            axum::routing::post(collision_telemetry),
        )
        .with_state(app);
    let bind: SocketAddr = std::env::var("ARC_BIND")
        .unwrap_or_else(|_| "127.0.0.1:3000".into())
        .parse()?;
    info!(%bind, "Arc Angel listening");
    let listener = tokio::net::TcpListener::bind(bind).await?;
    axum::serve(listener, router)
        .with_graceful_shutdown(async {
            let _ = tokio::signal::ctrl_c().await;
        })
        .await?;
    Ok(())
}

async fn record_writer(path: PathBuf, mut rx: mpsc::Receiver<Value>) {
    let Ok(mut file) = OpenOptions::new()
        .create(true)
        .append(true)
        .open(path)
        .await
    else {
        error!("record file could not be opened");
        return;
    };
    while let Some(value) = rx.recv().await {
        if let Ok(mut line) = serde_json::to_vec(&value) {
            line.push(b'\n');
            if let Err(e) = file.write_all(&line).await {
                error!(%e, "record write failed");
            }
        }
    }
}

fn record(app: &App, kind: &str, data: Value) {
    if app
        .records
        .try_send(
            json!({"kind":kind,"server_uptime_ms":app.started.elapsed().as_millis(),"data":data}),
        )
        .is_err()
    {
        warn!("record queue full");
    }
}

async fn status(State(app): State<App>) -> Json<Value> {
    let crossing_count = app.worlds.lock().await.len();
    let headon_count = app.headon.snapshots().await.len();
    let collision_count = usize::from(app.collision.snapshot().await.is_some());
    Json(
        json!({"service":"Arc Angel","version":env!("CARGO_PKG_VERSION"),
        "protocol_version":VERSION,"maneuver_protocol_version":headon_protocol::VERSION,
        "uptime_s":app.started.elapsed().as_secs(),"scenario_config_id":app.scenario.id,
        "world_count":crossing_count+headon_count+collision_count,"collision_world_count":collision_count,"crossing_world_count":crossing_count,
        "headon_world_count":headon_count,"recording":"jsonl"}),
    )
}
async fn worlds(State(app): State<App>) -> Json<Value> {
    let all: Vec<_> = app.worlds.lock().await.values().cloned().collect();
    let mut snapshots = Vec::new();
    for w in all {
        snapshots.push(w.lock().await.snapshot());
    }
    let mut snapshots: Vec<Value> = snapshots
        .into_iter()
        .map(|s| serde_json::to_value(s).unwrap())
        .collect();
    snapshots.extend(app.headon.snapshots().await);
    snapshots.extend(app.collision.snapshot().await);
    snapshots.sort_by_key(|s| s["wall_age_ms"].as_u64().unwrap_or(u64::MAX));
    Json(json!(snapshots))
}
async fn world_detail(
    Path(id): Path<String>,
    State(app): State<App>,
) -> Result<Json<Value>, StatusCode> {
    if let Some(snapshot) = app.collision.snapshot().await {
        if snapshot["world_id"] == id {
            return Ok(Json(snapshot));
        }
    }
    if let Some(snapshot) = app.headon.get(&id).await {
        return Ok(Json(snapshot));
    }
    let w = app
        .worlds
        .lock()
        .await
        .get(&id)
        .cloned()
        .ok_or(StatusCode::NOT_FOUND)?;
    let snapshot = w.lock().await.snapshot();
    Ok(Json(json!(snapshot)))
}
async fn scenario_detail(
    Path(id): Path<String>,
    State(app): State<App>,
) -> Result<Json<Value>, StatusCode> {
    if id == collision_observer::SCENARIO {
        return Ok(Json(collision_observer::scenario()));
    }
    if id == headon_protocol::SCENARIO {
        return Ok(Json(headon_bridge::scenario()));
    }
    if id != app.scenario.id {
        return Err(StatusCode::NOT_FOUND);
    }
    Ok(Json(json!(app.scenario)))
}
async fn bridge_upgrade(
    ws: WebSocketUpgrade,
    headers: HeaderMap,
    State(app): State<App>,
) -> impl IntoResponse {
    if let Some(expected) = &app.token {
        let supplied = headers
            .get(header::AUTHORIZATION)
            .and_then(|v| v.to_str().ok());
        if supplied != Some(format!("Bearer {expected}").as_str()) {
            return StatusCode::UNAUTHORIZED.into_response();
        }
    }
    ws.max_message_size(256 * 1024)
        .on_upgrade(move |socket| bridge(socket, app))
        .into_response()
}

async fn headon_upgrade(
    ws: WebSocketUpgrade,
    headers: HeaderMap,
    State(app): State<App>,
) -> impl IntoResponse {
    if let Some(expected) = &app.token {
        let supplied = headers
            .get(header::AUTHORIZATION)
            .and_then(|v| v.to_str().ok());
        if supplied != Some(format!("Bearer {expected}").as_str()) {
            return StatusCode::UNAUTHORIZED.into_response();
        }
    }
    ws.max_message_size(256 * 1024)
        .on_upgrade(move |socket| headon_bridge::serve(socket, app.headon, app.records))
        .into_response()
}

async fn bridge(socket: WebSocket, app: App) {
    let connection = Uuid::new_v4().to_string();
    let (mut sink, mut stream) = socket.split();
    let (plan_tx, mut plan_rx) = mpsc::channel::<Outgoing>(8);
    let mut owned: Option<(String, String)> = None;
    loop {
        let next = tokio::select! {
            message = stream.next() => message,
            Some(out) = plan_rx.recv() => {
                if sink.send(Message::Text(serde_json::to_string(&out).unwrap_or_default().into())).await.is_err() { break; }
                continue;
            }
        };
        let Some(Ok(message)) = next else {
            break;
        };
        let Message::Text(text) = message else {
            continue;
        };
        let parsed = serde_json::from_str::<Incoming>(&text);
        let response = match parsed {
            Ok(msg) => handle_message(&app, &connection, &mut owned, &plan_tx, msg).await,
            Err(e) => Err(("invalid_json", e.to_string())),
        };
        match response {
            Ok(Some(out)) => {
                if sink
                    .send(Message::Text(
                        serde_json::to_string(&out).unwrap_or_default().into(),
                    ))
                    .await
                    .is_err()
                {
                    break;
                }
            }
            Ok(None) => {}
            Err((code, detail)) => {
                record(&app, "rejected", json!({"code":code,"detail":detail}));
                let err = Outgoing::Error {
                    code: code.into(),
                    detail,
                };
                if sink
                    .send(Message::Text(
                        serde_json::to_string(&err).unwrap_or_default().into(),
                    ))
                    .await
                    .is_err()
                {
                    break;
                }
            }
        }
    }
    if let Some((id, session)) = owned {
        if let Some(w) = app.worlds.lock().await.get(&id).cloned() {
            let mut w = w.lock().await;
            if w.session_id == session && w.owner_id == connection {
                w.owner_id.clear();
                record(
                    &app,
                    "disconnect",
                    json!({"world_id":id,"session_id":session}),
                );
            }
        }
    }
}

async fn handle_message(
    app: &App,
    connection: &str,
    owned: &mut Option<(String, String)>,
    plan_tx: &mpsc::Sender<Outgoing>,
    msg: Incoming,
) -> Result<Option<Outgoing>, (&'static str, String)> {
    match msg {
        Incoming::Hello {
            protocol_version,
            world_id,
            world_epoch,
            scenario_config_id,
            bridge_id,
        } => {
            if protocol_version != VERSION
                || scenario_config_id != app.scenario.id
                || !protocol::valid_id(&world_id)
                || !protocol::valid_id(&world_epoch)
                || !protocol::valid_id(&bridge_id)
            {
                return Err((
                    "invalid_hello",
                    "version, scenario or identity invalid".into(),
                ));
            }
            if owned.is_some() {
                return Err((
                    "already_registered",
                    "connection already owns a world".into(),
                ));
            }
            let mut all = app.worlds.lock().await;
            let prior = if let Some(existing) = all.get(&world_id) {
                let old = existing.lock().await;
                if !old.owner_id.is_empty() {
                    return Err(("world_owned", "world has an active bridge".into()));
                }
                if old.epoch == world_epoch {
                    Some((
                        old.vehicles.clone(),
                        old.reservations.clone(),
                        old.first_seen.clone(),
                        old.sim_time_s,
                    ))
                } else {
                    None
                }
            } else {
                None
            };
            let session = Uuid::new_v4().to_string();
            let mut new_world = World::new(
                world_id.clone(),
                world_epoch.clone(),
                session.clone(),
                bridge_id,
                connection.into(),
                &app.scenario,
            );
            if let Some((vehicles, reservations, first_seen, sim_time_s)) = prior {
                new_world.vehicles = vehicles;
                new_world.reservations = reservations;
                new_world.first_seen = first_seen;
                new_world.sim_time_s = sim_time_s;
            }
            all.insert(world_id.clone(), Arc::new(Mutex::new(new_world)));
            *owned = Some((world_id.clone(), session.clone()));
            record(
                app,
                "hello",
                json!({"world_id":world_id,"world_epoch":world_epoch,"session_id":session}),
            );
            Ok(Some(Outgoing::HelloAck {
                protocol_version: VERSION,
                world_id,
                world_epoch,
                session_id: session,
                status: "ready".into(),
                advice_horizon_sim_s: 0.5,
                wall_freshness_s: 0.5,
            }))
        }
        Incoming::StateBatch {
            protocol_version,
            world_id,
            world_epoch,
            session_id,
            frame_seq,
            sim_time_s,
            scenario_config_id,
            vehicles,
        } => {
            if protocol_version != VERSION
                || scenario_config_id != app.scenario.id
                || !sim_time_s.is_finite()
                || sim_time_s < 0.0
                || vehicles.len() > 100
            {
                return Err((
                    "invalid_frame",
                    "version, scenario, time or vehicle count invalid".into(),
                ));
            }
            let w =
                owned_world(app, connection, owned, &world_id, &world_epoch, &session_id).await?;
            let mut w = w.lock().await;
            let mut ids = HashSet::new();
            if vehicles.iter().any(|v| {
                !protocol::valid_vehicle(v, app.scenario.max_speed_mps)
                    || app.scenario.route(&v.route_id).is_none()
                    || !ids.insert(v.vehicle_id.clone())
            }) {
                w.rejected += 1;
                return Err(("invalid_vehicle", "vehicle data or route invalid".into()));
            }
            if w.last_frame_seq.is_some_and(|old| frame_seq <= old) || sim_time_s < w.sim_time_s {
                w.rejected += 1;
                return Err((
                    "old_frame",
                    "frame sequence or simulation time went backwards".into(),
                ));
            }
            w.last_received = Instant::now();
            w.last_frame_seq = Some(frame_seq);
            w.sim_time_s = sim_time_s;
            for v in &vehicles {
                w.first_seen
                    .entry(v.vehicle_id.clone())
                    .or_insert(frame_seq);
            }
            w.vehicles = vehicles.clone();
            record(
                app,
                "telemetry",
                json!({"world_id":world_id,"world_epoch":world_epoch,"session_id":session_id,"frame_seq":frame_seq,"sim_time_s":sim_time_s,"vehicles":vehicles}),
            );
            if w.computing {
                if w.pending
                    .replace((frame_seq, sim_time_s, vehicles))
                    .is_some()
                {
                    w.coalesced += 1;
                }
                return Ok(None);
            }
            w.computing = true;
            drop(w);
            let worker_app = app.clone();
            let worker_world = w_clone(app, &world_id).await?;
            let worker_tx = plan_tx.clone();
            tokio::spawn(async move {
                let mut current = (frame_seq, sim_time_s, vehicles);
                loop {
                    match compute_plan(
                        &worker_app,
                        worker_world.clone(),
                        current.0,
                        current.1,
                        current.2,
                    )
                    .await
                    {
                        Ok(out) => {
                            if worker_tx.send(out).await.is_err() {
                                break;
                            }
                        }
                        Err(("stale_result", _)) => {}
                        Err((code, detail)) => {
                            record(
                                &worker_app,
                                "compute_error",
                                json!({"code":code,"detail":detail}),
                            );
                            let _ = worker_tx
                                .send(Outgoing::Error {
                                    code: code.into(),
                                    detail,
                                })
                                .await;
                        }
                    }
                    let mut w = worker_world.lock().await;
                    if let Some(pending) = w.pending.take() {
                        current = pending;
                    } else {
                        w.computing = false;
                        break;
                    }
                }
            });
            Ok(None)
        }
        Incoming::AppliedResult {
            protocol_version,
            world_id,
            world_epoch,
            session_id,
            plan_seq,
            vehicle_id,
            status,
            applied_speed_cap_mps,
            rejection_reason,
        } => {
            if protocol_version != VERSION
                || !protocol::valid_id(&vehicle_id)
                || !matches!(status.as_str(), "applied" | "rejected" | "overridden")
                || applied_speed_cap_mps
                    .is_some_and(|v| !v.is_finite() || v < 0.0 || v > app.scenario.max_speed_mps)
            {
                return Err(("invalid_ack", "acknowledgement invalid".into()));
            }
            let w =
                owned_world(app, connection, owned, &world_id, &world_epoch, &session_id).await?;
            let mut w = w.lock().await;
            if plan_seq != w.plan_seq {
                return Err(("old_plan", "acknowledgement refers to another plan".into()));
            }
            w.acknowledgements
                .insert(vehicle_id.clone(), status.clone());
            record(
                app,
                "applied_result",
                json!({"world_id":world_id,"plan_seq":plan_seq,"vehicle_id":vehicle_id,"status":status,"applied_speed_cap_mps":applied_speed_cap_mps,"rejection_reason":rejection_reason}),
            );
            Ok(None)
        }
        Incoming::VehicleRemoved {
            protocol_version,
            world_id,
            world_epoch,
            session_id,
            vehicle_id,
            reason,
        } => {
            if protocol_version != VERSION
                || !protocol::valid_id(&vehicle_id)
                || reason != "confirmed_clear"
            {
                return Err(("invalid_removal", "removal requires confirmed_clear".into()));
            }
            let w =
                owned_world(app, connection, owned, &world_id, &world_epoch, &session_id).await?;
            let mut w = w.lock().await;
            w.vehicles.retain(|v| v.vehicle_id != vehicle_id);
            w.reservations.retain(|r| r.vehicle_id != vehicle_id);
            w.first_seen.remove(&vehicle_id);
            record(
                app,
                "vehicle_removed",
                json!({"world_id":world_id,"vehicle_id":vehicle_id,"reason":reason}),
            );
            Ok(None)
        }
    }
}

async fn w_clone(app: &App, id: &str) -> Result<Arc<Mutex<World>>, (&'static str, String)> {
    app.worlds
        .lock()
        .await
        .get(id)
        .cloned()
        .ok_or(("world_missing", "world unavailable".into()))
}
async fn owned_world(
    app: &App,
    connection: &str,
    owned: &Option<(String, String)>,
    id: &str,
    epoch: &str,
    session: &str,
) -> Result<Arc<Mutex<World>>, (&'static str, String)> {
    if owned.as_ref() != Some(&(id.into(), session.into())) {
        return Err((
            "wrong_session",
            "connection does not own world/session".into(),
        ));
    }
    let w = w_clone(app, id).await?;
    {
        let g = w.lock().await;
        if g.epoch != epoch || g.session_id != session || g.owner_id != connection {
            return Err(("wrong_session", "epoch or owner mismatch".into()));
        }
    }
    Ok(w)
}

async fn compute_plan(
    app: &App,
    world: Arc<Mutex<World>>,
    frame_seq: u64,
    sim_time_s: f64,
    vehicles: Vec<protocol::Vehicle>,
) -> Result<Outgoing, (&'static str, String)> {
    let permit = app
        .compute
        .clone()
        .acquire_owned()
        .await
        .map_err(|e| ("compute_unavailable", e.to_string()))?;
    let (input, world_id, epoch, session) = {
        let mut w = world.lock().await;
        w.plan_seq += 1;
        (
            coordinator::PlanInput {
                vehicles,
                first_seen: w.first_seen.clone(),
                previous: w.reservations.clone(),
                sim_time_s,
                plan_seq: w.plan_seq,
                scenario: app.scenario.clone(),
            },
            w.world_id.clone(),
            w.epoch.clone(),
            w.session_id.clone(),
        )
    };
    let plan_seq = input.plan_seq;
    let started = Instant::now();
    let plan = tokio::task::spawn_blocking(move || {
        let _permit = permit;
        coordinator::plan(input)
    })
    .await
    .map_err(|e| ("compute_failed", e.to_string()))?;
    let mut w = world.lock().await;
    if w.session_id != session || w.last_frame_seq != Some(frame_seq) {
        return Err((
            "stale_result",
            "newer frame or session superseded result".into(),
        ));
    }
    w.reservations = plan.reservations;
    let out = Outgoing::RecommendationBatch {
        protocol_version: VERSION,
        world_id: world_id.clone(),
        world_epoch: epoch,
        session_id: session,
        based_on_frame_seq: frame_seq,
        plan_seq,
        issued_sim_time_s: sim_time_s,
        valid_until_sim_time_s: sim_time_s + 0.5,
        status: if plan.degraded {
            "degraded"
        } else {
            "coordinated"
        }
        .into(),
        recommendations: plan.recommendations,
    };
    w.last_plan = Some(out.clone());
    record(
        app,
        "plan",
        json!({"world_id":world_id,"compute_ms":started.elapsed().as_millis(),"plan":out}),
    );
    Ok(out)
}

async fn collision_telemetry(
    State(app): State<App>,
    headers: HeaderMap,
    Json(frame): Json<collision_observer::Frame>,
) -> Result<StatusCode, StatusCode> {
    if let Some(expected) = &app.token {
        if headers
            .get(header::AUTHORIZATION)
            .and_then(|v| v.to_str().ok())
            != Some(format!("Bearer {expected}").as_str())
        {
            return Err(StatusCode::UNAUTHORIZED);
        }
    }
    let event = json!({"kind":"collision_observation","data":{"world_id":frame.world_id,"frame_seq":frame.frame_seq,"sim_time_s":frame.sim_time_s,"finished":frame.finished,"mode":frame.mode,"vehicles":frame.vehicles}});
    app.collision
        .publish(frame)
        .await
        .map_err(|_| StatusCode::BAD_REQUEST)?;
    let _ = app.records.try_send(event);
    Ok(StatusCode::NO_CONTENT)
}

async fn conflict_evaluate(
    State(app): State<App>,
    headers: HeaderMap,
    Json(request): Json<conflict_resolution::EvaluateRequest>,
) -> Result<Json<conflict_resolution::EvaluateResponse>, StatusCode> {
    if !authorized(&headers, app.token.as_deref()) {
        return Err(StatusCode::UNAUTHORIZED);
    }
    let response = conflict_resolution::evaluate(request).map_err(|_| StatusCode::BAD_REQUEST)?;
    record(&app, "conflict_evaluation", json!(response));
    Ok(Json(response))
}

#[derive(serde::Deserialize)]
#[serde(deny_unknown_fields)]
struct CommandResultRequest {
    record: conflict_resolution::CommandRecord,
    observed_speed_mps: Option<f64>,
    stopped_threshold_mps: f64,
}

async fn conflict_command_result(
    State(app): State<App>,
    headers: HeaderMap,
    Json(mut request): Json<CommandResultRequest>,
) -> Result<StatusCode, StatusCode> {
    if !authorized(&headers, app.token.as_deref()) {
        return Err(StatusCode::UNAUTHORIZED);
    }
    if !protocol::valid_id(&request.record.command_id)
        || !protocol::valid_id(&request.record.vehicle_id)
        || !request.record.sim_time_s.is_finite()
        || request.record.sim_time_s < 0.0
        || !request.stopped_threshold_mps.is_finite()
        || request.stopped_threshold_mps < 0.0
        || request.stopped_threshold_mps > 2.0
        || request
            .observed_speed_mps
            .is_some_and(|v| !v.is_finite() || v < 0.0)
    {
        return Err(StatusCode::BAD_REQUEST);
    }
    conflict_resolution::verify_command_response(
        &mut request.record,
        request.observed_speed_mps,
        request.stopped_threshold_mps,
    );
    record(&app, "conflict_command_result", json!(request.record));
    Ok(StatusCode::NO_CONTENT)
}

fn authorized(headers: &HeaderMap, expected: Option<&str>) -> bool {
    expected.is_none_or(|token| {
        headers
            .get(header::AUTHORIZATION)
            .and_then(|v| v.to_str().ok())
            == Some(format!("Bearer {token}").as_str())
    })
}
