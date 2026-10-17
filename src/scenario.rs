use serde::{Deserialize, Serialize};
use std::{collections::HashSet, fs};

#[derive(Clone, Serialize, Deserialize)]
pub struct Route {
    pub id: String,
    pub points_xy_m: Vec<[f64; 2]>,
    pub zone_center_s_m: f64,
    pub yield_s_m: f64,
    pub commit_s_m: f64,
}

#[derive(Clone, Serialize, Deserialize)]
pub struct Scenario {
    pub id: String,
    pub label: String,
    pub zone_half_extent_m: f64,
    pub margin_m: f64,
    pub max_speed_mps: f64,
    pub routes: Vec<Route>,
}

impl Scenario {
    pub fn load(path: &str) -> Result<Self, String> {
        let data = fs::read_to_string(path).map_err(|e| e.to_string())?;
        let s: Self = serde_json::from_str(&data).map_err(|e| e.to_string())?;
        let mut ids = HashSet::new();
        if !crate::protocol::valid_id(&s.id)
            || !s.zone_half_extent_m.is_finite()
            || s.zone_half_extent_m <= 0.0
            || !s.margin_m.is_finite()
            || s.margin_m < 0.0
            || !s.max_speed_mps.is_finite()
            || s.max_speed_mps <= 0.0
            || s.routes.is_empty()
            || s.routes.iter().any(|r| {
                !crate::protocol::valid_id(&r.id)
                    || !ids.insert(&r.id)
                    || r.points_xy_m.len() < 2
                    || r.points_xy_m.iter().flatten().any(|v| !v.is_finite())
                    || !r.zone_center_s_m.is_finite()
                    || r.zone_center_s_m <= r.commit_s_m
                    || !r.yield_s_m.is_finite()
                    || !r.commit_s_m.is_finite()
                    || r.yield_s_m < 0.0
                    || r.commit_s_m < r.yield_s_m
            })
        {
            return Err("invalid scenario configuration".into());
        }
        Ok(s)
    }

    pub fn route(&self, id: &str) -> Option<&Route> {
        self.routes.iter().find(|r| r.id == id)
    }
}

pub fn project(route: &Route, p: [f64; 2]) -> (f64, f64) {
    let mut best = (0.0, f64::INFINITY);
    let mut prefix = 0.0;
    for pair in route.points_xy_m.windows(2) {
        let a = pair[0];
        let b = pair[1];
        let dx = b[0] - a[0];
        let dy = b[1] - a[1];
        let len2 = dx * dx + dy * dy;
        if len2 <= 0.0 {
            continue;
        }
        let t = (((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / len2).clamp(0.0, 1.0);
        let x = a[0] + t * dx;
        let y = a[1] + t * dy;
        let d = ((p[0] - x).powi(2) + (p[1] - y).powi(2)).sqrt();
        if d < best.1 {
            best = (prefix + t * len2.sqrt(), d);
        }
        prefix += len2.sqrt();
    }
    best
}
