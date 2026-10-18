use crate::{
    protocol::Vehicle,
    scenario::{project, Scenario},
    world::SpeedSample,
};
use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::{
    collections::{HashMap, VecDeque},
    net::SocketAddr,
    time::Duration,
};
use tokio::{
    io::{AsyncBufReadExt, AsyncReadExt, AsyncWriteExt, BufReader},
    net::TcpStream,
    time::timeout,
};

fn route_tangent(route: &crate::scenario::Route, position: [f64; 2]) -> [f64; 2] {
    let mut best_distance = f64::INFINITY;
    let mut best_tangent = [1.0, 0.0];
    for segment in route.points_xy_m.windows(2) {
        let dx = segment[1][0] - segment[0][0];
        let dy = segment[1][1] - segment[0][1];
        let length_squared = dx * dx + dy * dy;
        if length_squared <= f64::EPSILON {
            continue;
        }
        let t = (((position[0] - segment[0][0]) * dx + (position[1] - segment[0][1]) * dy)
            / length_squared)
            .clamp(0.0, 1.0);
        let px = segment[0][0] + t * dx;
        let py = segment[0][1] + t * dy;
        let distance = (position[0] - px).hypot(position[1] - py);
        if distance < best_distance {
            let length = length_squared.sqrt();
            best_distance = distance;
            best_tangent = [dx / length, dy / length];
        }
    }
    best_tangent
}

pub const FEATURES: [&str; 13] = [
    "distance_to_entry_m",
    "distance_to_rear_clearance_m",
    "forward_speed_mps",
    "forward_acceleration_mps2",
    "speed_0_5s_ago_mps",
    "speed_1s_ago_mps",
    "speed_trailing_1s_mean_mps",
    "speed_trailing_1s_std_mps",
    "vehicle_length_m",
    "vehicle_width_m",
    "vehicle_height_m",
    "nearest_vehicle_distance_m",
    "nearest_vehicle_relative_speed_mps",
];

#[derive(Clone, Serialize, Deserialize)]
pub struct Prediction {
    pub vehicle_id: String,
    pub entry_eta_s: Option<f64>,
    pub rear_clearance_eta_s: Option<f64>,
    pub status: String,
}

#[derive(Clone, Serialize, Deserialize)]
pub struct PredictionBatch {
    pub status: String,
    pub model_version: Option<String>,
    pub predictions: Vec<Prediction>,
}

pub fn observe_speeds(
    history: &mut HashMap<String, VecDeque<SpeedSample>>,
    sim_time_s: f64,
    vehicles: &[Vehicle],
    scenario: &Scenario,
) {
    for vehicle in vehicles {
        let Some(route) = scenario.route(&vehicle.route_id) else {
            continue;
        };
        let tangent = route_tangent(route, vehicle.position_xy_m);
        let speed =
            vehicle.velocity_xy_mps[0] * tangent[0] + vehicle.velocity_xy_mps[1] * tangent[1];
        let samples = history.entry(vehicle.vehicle_id.clone()).or_default();
        if let Some(previous) = samples.back() {
            if sim_time_s - previous.sim_time_s < 0.2 - 1e-9 {
                continue;
            }
        }
        samples.push_back(SpeedSample {
            sim_time_s,
            forward_speed_mps: speed,
        });
        while samples
            .front()
            .is_some_and(|sample| sim_time_s - sample.sim_time_s > 2.0)
        {
            samples.pop_front();
        }
    }
    history.retain(|id, _| vehicles.iter().any(|vehicle| &vehicle.vehicle_id == id));
}

pub fn feature_rows(
    vehicles: &[Vehicle],
    scenario: &Scenario,
    history: &HashMap<String, VecDeque<SpeedSample>>,
    sim_time_s: f64,
) -> Vec<Value> {
    vehicles
        .iter()
        .map(|vehicle| {
            let Some(route) = scenario.route(&vehicle.route_id) else {
                return json!({});
            };
            let (along, _) = project(route, vehicle.position_xy_m);
            let tangent = route_tangent(route, vehicle.position_xy_m);
            let body_half_extent = projected_body_half_extent(vehicle, tangent);
            let forward_speed =
                vehicle.velocity_xy_mps[0] * tangent[0] + vehicle.velocity_xy_mps[1] * tangent[1];
            let samples = history
                .get(&vehicle.vehicle_id)
                .cloned()
                .unwrap_or_default();
            let acceleration = samples
                .iter()
                .rev()
                .find(|sample| sim_time_s - sample.sim_time_s >= 0.05)
                .map(|old| (forward_speed - old.forward_speed_mps) / (sim_time_s - old.sim_time_s));
            let speed_at = |lag: f64| -> Option<f64> {
                samples
                    .iter()
                    .rev()
                    .find(|sample| {
                        let age = sim_time_s - sample.sim_time_s;
                        age >= lag && age <= lag + 0.6
                    })
                    .map(|sample| sample.forward_speed_mps)
            };
            let mut trailing: Vec<f64> = samples
                .iter()
                .filter(|sample| sim_time_s - sample.sim_time_s <= 1.0)
                .map(|sample| sample.forward_speed_mps)
                .collect();
            trailing.push(forward_speed);
            let mean = trailing.iter().sum::<f64>() / trailing.len() as f64;
            let variance = trailing
                .iter()
                .map(|speed| (speed - mean).powi(2))
                .sum::<f64>()
                / trailing.len() as f64;
            let nearest = vehicles
                .iter()
                .filter(|other| other.vehicle_id != vehicle.vehicle_id)
                .map(|other| {
                    let dx = other.position_xy_m[0] - vehicle.position_xy_m[0];
                    let dy = other.position_xy_m[1] - vehicle.position_xy_m[1];
                    let distance = dx.hypot(dy);
                    let relative_speed = if distance > 1e-9 {
                        ((other.velocity_xy_mps[0] - vehicle.velocity_xy_mps[0]) * dx
                            + (other.velocity_xy_mps[1] - vehicle.velocity_xy_mps[1]) * dy)
                            / distance
                    } else { 0.0 };
                    (distance, relative_speed)
                })
                .min_by(|left, right| left.0.total_cmp(&right.0));
            let entry_center_s = route.zone_center_s_m - scenario.zone_half_extent_m;
            let clearance_center_s = route.zone_center_s_m + scenario.zone_half_extent_m;
            let mut values = serde_json::Map::new();
            let features: [(&str, Option<f64>); 13] = [
                (FEATURES[0], Some(entry_center_s - body_half_extent - along)),
                (
                    FEATURES[1],
                    Some(clearance_center_s + body_half_extent - along),
                ),
                (FEATURES[2], Some(forward_speed)),
                (FEATURES[3], acceleration),
                (FEATURES[4], speed_at(0.5)),
                (FEATURES[5], speed_at(1.0)),
                (FEATURES[6], Some(mean)),
                (FEATURES[7], Some(variance.sqrt())),
                (FEATURES[8], Some(vehicle.length_m)),
                (FEATURES[9], Some(vehicle.width_m)),
                (FEATURES[10], None),
                (FEATURES[11], nearest.map(|item| item.0)),
                (FEATURES[12], nearest.map(|item| item.1)),
            ];
            for (key, value) in features {
                values.insert(
                    key.into(),
                    value
                        .filter(|number| number.is_finite())
                        .map_or(Value::Null, |number| json!(number)),
                );
            }
            json!({"vehicle_id": vehicle.vehicle_id, "values": values})
        })
        .collect()
}

fn projected_body_half_extent(vehicle: &Vehicle, route_tangent: [f64; 2]) -> f64 {
    let forward = [vehicle.heading_rad.cos(), vehicle.heading_rad.sin()];
    let side = [-forward[1], forward[0]];
    vehicle.length_m / 2.0 * (forward[0] * route_tangent[0] + forward[1] * route_tangent[1]).abs()
        + vehicle.width_m / 2.0 * (side[0] * route_tangent[0] + side[1] * route_tangent[1]).abs()
}

pub async fn predict(address: SocketAddr, features: Vec<Value>) -> Result<PredictionBatch, String> {
    let request = json!({"type":"predict_batch", "features":features});
    let operation = async {
        let mut stream = TcpStream::connect(address)
            .await
            .map_err(|error| error.to_string())?;
        let mut bytes = serde_json::to_vec(&request).map_err(|error| error.to_string())?;
        bytes.push(b'\n');
        stream
            .write_all(&bytes)
            .await
            .map_err(|error| error.to_string())?;
        let mut line = String::new();
        BufReader::new(stream)
            .take(64 * 1024)
            .read_line(&mut line)
            .await
            .map_err(|error| error.to_string())?;
        if line.is_empty() {
            return Err("worker closed without a response".into());
        }
        let response: PredictionBatch =
            serde_json::from_str(&line).map_err(|error| error.to_string())?;
        if response.status != "ok"
            || response.predictions.len() != request["features"].as_array().map_or(0, Vec::len)
        {
            return Err("worker returned an invalid prediction batch".into());
        }
        if response
            .predictions
            .iter()
            .zip(request["features"].as_array().into_iter().flatten())
            .any(|(prediction, row)| {
                prediction.vehicle_id != row["vehicle_id"].as_str().unwrap_or_default()
            })
        {
            return Err("worker prediction vehicle IDs do not match the request".into());
        }
        if response.predictions.iter().any(|prediction| {
            prediction
                .entry_eta_s
                .is_some_and(|value| !value.is_finite() || value < 0.0)
                || prediction
                    .rear_clearance_eta_s
                    .is_some_and(|value| !value.is_finite() || value < 0.0)
        }) {
            return Err("worker returned a non-finite or negative ETA".into());
        }
        Ok(response)
    };
    timeout(Duration::from_millis(40), operation)
        .await
        .map_err(|_| "worker timed out after 40 ms".to_owned())?
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::scenario::Route;
    use tokio::{
        io::{AsyncBufReadExt, AsyncWriteExt, BufReader},
        net::TcpListener,
    };

    fn scenario() -> Scenario {
        Scenario {
            id: "test".into(),
            label: "test".into(),
            zone_half_extent_m: 3.0,
            margin_m: 1.0,
            max_speed_mps: 20.0,
            routes: vec![Route {
                id: "east".into(),
                points_xy_m: vec![[-10.0, 0.0], [10.0, 0.0]],
                zone_center_s_m: 10.0,
                yield_s_m: 1.0,
                commit_s_m: 2.0,
            }],
        }
    }

    fn vehicle(id: &str, x: f64, speed: f64) -> Vehicle {
        Vehicle {
            vehicle_id: id.into(),
            route_id: "east".into(),
            position_xy_m: [x, 0.0],
            velocity_xy_mps: [speed, 0.0],
            acceleration_xy_mps2: [0.0, 0.0],
            heading_rad: 0.0,
            length_m: 4.0,
            width_m: 2.0,
        }
    }

    #[test]
    fn feature_rows_match_training_schema_and_geometry() {
        let scenario = scenario();
        let car = vehicle("car-a", -2.0, 5.0);
        let mut history = HashMap::new();
        observe_speeds(&mut history, 0.0, std::slice::from_ref(&car), &scenario);
        observe_speeds(&mut history, 0.2, std::slice::from_ref(&car), &scenario);
        let rows = feature_rows(std::slice::from_ref(&car), &scenario, &history, 0.2);
        let values = rows[0]["values"].as_object().unwrap();
        assert_eq!(values.len(), FEATURES.len());
        assert_eq!(values["distance_to_entry_m"], json!(-3.0));
        assert_eq!(values["distance_to_rear_clearance_m"], json!(7.0));
        assert_eq!(values["forward_speed_mps"], json!(5.0));
        assert_eq!(values["vehicle_height_m"], Value::Null);
        assert_eq!(values["nearest_vehicle_distance_m"], Value::Null);
    }

    #[test]
    fn nearest_relative_speed_is_radial_like_recorded_training_data() {
        let scenario = scenario();
        let a = vehicle("a", -5.0, 4.0);
        let mut b = vehicle("b", -5.0, 4.0);
        b.position_xy_m = [-5.0, 3.0];
        b.velocity_xy_mps = [4.0, -2.0];
        let rows = feature_rows(&[a,b], &scenario, &HashMap::new(), 0.0);
        assert_eq!(rows[0]["values"]["nearest_vehicle_relative_speed_mps"], json!(-2.0));
    }

    #[tokio::test]
    async fn json_line_worker_response_is_bound_to_requested_vehicle() {
        let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
        let address = listener.local_addr().unwrap();
        let server = tokio::spawn(async move {
            let (stream, _) = listener.accept().await.unwrap();
            let mut reader = BufReader::new(stream);
            let mut request = String::new();
            reader.read_line(&mut request).await.unwrap();
            let parsed: Value = serde_json::from_str(&request).unwrap();
            assert_eq!(parsed["type"], "predict_batch");
            assert_eq!(parsed["features"][0]["vehicle_id"], "car-a");
            reader
                .get_mut()
                .write_all(b"{\"status\":\"ok\",\"model_version\":\"unit\",\"predictions\":[{\"vehicle_id\":\"car-a\",\"entry_eta_s\":1.25,\"rear_clearance_eta_s\":2.5,\"status\":\"predicted\"}]}\n")
                .await
                .unwrap();
        });
        let batch = predict(address, vec![json!({"vehicle_id":"car-a","values":{}})])
            .await
            .unwrap();
        assert_eq!(batch.model_version.as_deref(), Some("unit"));
        assert_eq!(batch.predictions[0].entry_eta_s, Some(1.25));
        server.await.unwrap();
    }
}
