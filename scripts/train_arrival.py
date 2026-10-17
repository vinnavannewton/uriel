#!/usr/bin/env python3
"""Build and evaluate offline Small Grid arrival/clearance regressors.

This tool reads existing ``uriel_experiment`` recordings. It never connects to
BeamNG and writes model artifacts below a new UUID directory in ``runs/``.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import platform
import sys
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import sklearn
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.model_selection import GroupShuffleSplit


ROOT = Path(__file__).resolve().parents[1]
FEATURES = [
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
]
TARGETS = ("entry", "clearance")
MAX_SAMPLE_HZ = 5.0
MIN_SPLIT_GROUPS = {"train": 3, "validation": 2, "test": 2}
VALIDATION_STATUSES = {"PASS", "PASS_WITH_LIMITATIONS"}
GRID = ((0.05, 7), (0.05, 15), (0.1, 7), (0.1, 15))


def read_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def validation_status_for_audit(path: Path) -> str | None:
    """A rejected malformed report must not crash audit serialization."""
    try:
        report = read_json(path)
        return report.get("status") if isinstance(report, dict) else None
    except (OSError, json.JSONDecodeError):
        return None


def as_float(value: Any) -> float:
    if value is None or value == "":
        return math.nan
    number = float(value)
    return number if math.isfinite(number) else math.nan


def as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def json_safe(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    return value


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(json_safe(value), indent=2, sort_keys=True) + "\n", encoding="utf-8")


@dataclass
class VehicleRun:
    trial_id: str
    vehicle_id: str
    role: str
    route_axis: str
    rows: list[dict[str, Any]]
    entry_time: float | None
    clearance_time: float | None
    first_damage_time: float | None
    first_deviation_time: float | None
    label_quality: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass
class Trial:
    trial_id: str
    batch_id: str
    folder: Path
    metadata: dict[str, Any]
    geometry: dict[str, Any]
    digest: str
    seed: Any
    config_hash: str
    group_id: str
    reason: str | None
    duplicate_of: str | None = None
    vehicle_runs: list[VehicleRun] = field(default_factory=list)
    row_count: int = 0


def load_rows(path: Path) -> tuple[list[dict[str, Any]], list[str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        fields = reader.fieldnames or []
        rows: list[dict[str, Any]] = []
        for source in reader:
            row: dict[str, Any] = dict(source)
            for key in ("frame_id",):
                try:
                    row[key] = int(source[key])
                except (KeyError, TypeError, ValueError):
                    row[key] = None
            for key in (
                "sim_time", "elapsed", "x", "y", "z", "yaw", "pitch", "roll",
                "vx", "vy", "vz", "speed", "ax", "ay", "az", "throttle",
                "brake", "steering", "gear", "target_speed", "start_delay",
                "relative_distance", "relative_speed", "damage", "front_progress",
                "rear_progress",
            ):
                try:
                    row[key] = as_float(source.get(key))
                except (TypeError, ValueError):
                    row[key] = math.nan
            row["route_deviation"] = as_bool(source.get("route_deviation"))
            try:
                row["bbox"] = json.loads(source.get("bbox_json") or "null")
            except (TypeError, json.JSONDecodeError):
                row["bbox"] = None
            rows.append(row)
    return rows, fields


def projected_box(row: dict[str, Any], axis: int) -> tuple[float, float, float, float] | None:
    points = row.get("bbox")
    if not isinstance(points, list) or not points:
        return None
    try:
        xy = [(float(point[0]), float(point[1])) for point in points]
    except (TypeError, ValueError, IndexError):
        return None
    if not all(math.isfinite(value) for point in xy for value in point):
        return None
    along = [point[axis] for point in xy]
    across = [point[1 - axis] for point in xy]
    return min(along), max(along), min(across), max(across)


def box_overlaps_zone(row: dict[str, Any], axis: int) -> bool | None:
    projected = projected_box(row, axis)
    if projected is None:
        return None
    _, _, lateral_min, lateral_max = projected
    axis_min, axis_max, _, _ = projected
    return axis_max >= -3.0 and axis_min <= 3.0 and lateral_max >= -3.0 and lateral_min <= 3.0


def config_map(metadata: dict[str, Any]) -> dict[str, dict[str, Any]]:
    configs = metadata.get("configuration", [])
    return {item.get("vehicle_id"): item for item in configs if isinstance(item, dict) and item.get("vehicle_id")}


def route_configuration_signature(metadata: dict[str, Any], geometry: dict[str, Any]) -> str:
    fields = (
        "role", "axis", "lane", "progress", "start_delay", "target_speed",
        "initial_speed_requested", "model", "source_background_id", "route_id",
    )
    configs = []
    for item in metadata.get("configuration", []):
        configs.append({key: item.get(key) for key in fields})
    signature = {
        "configuration": sorted(configs, key=lambda item: (item.get("role") or "", item.get("route_id") or "")),
        "zone": geometry.get("zone"),
        "map": geometry.get("map"),
        "ai": metadata.get("ai"),
    }
    return canonical_hash(signature)


def vehicle_quality(run: VehicleRun, target: str) -> dict[str, Any]:
    event_time = run.entry_time if target == "entry" else run.clearance_time
    if event_time is None:
        return {"status": "censored", "reason": f"no_{target}_observed_before_recording_end", "event_time": None}
    reasons: list[str] = []
    for field_name, timestamp in (
        ("damage_increase_before_event", run.first_damage_time),
        ("route_deviation_before_event", run.first_deviation_time),
    ):
        if timestamp is not None and timestamp <= event_time + 1e-9:
            reasons.append(field_name)
    return {
        "status": "excluded" if reasons else "eligible",
        "reason": ";".join(reasons) if reasons else None,
        "event_time": event_time,
        "first_damage_time": run.first_damage_time,
        "first_deviation_time": run.first_deviation_time,
    }


def recompute_vehicle_events(trial: Trial, all_rows: list[dict[str, Any]]) -> list[VehicleRun]:
    metadata_configs = config_map(trial.metadata)
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in all_rows:
        if row.get("vehicle_id"):
            grouped[row["vehicle_id"]].append(row)
    result: list[VehicleRun] = []
    for vehicle_id, rows in grouped.items():
        rows.sort(key=lambda row: (row["sim_time"] if math.isfinite(row["sim_time"]) else math.inf, row["frame_id"] or -1))
        config = metadata_configs.get(vehicle_id, {})
        axis = config.get("axis")
        axis_index = 0 if axis == "x" else 1 if axis == "y" else None
        entry_time: float | None = None
        clearance_time: float | None = None
        first_damage_time: float | None = None
        first_deviation_time: float | None = None
        initial_damage = next((row["damage"] for row in rows if math.isfinite(row["damage"])), math.nan)
        for row in rows:
            elapsed = row["elapsed"]
            if row["route_deviation"] and first_deviation_time is None and math.isfinite(elapsed):
                first_deviation_time = elapsed
            if math.isfinite(row["damage"]) and math.isfinite(initial_damage) and row["damage"] > initial_damage + 1e-6 and first_damage_time is None:
                first_damage_time = elapsed if math.isfinite(elapsed) else None
            if axis_index is None or not math.isfinite(elapsed):
                continue
            overlaps = box_overlaps_zone(row, axis_index)
            if overlaps is None:
                continue
            if overlaps and entry_time is None:
                entry_time = elapsed
            if entry_time is not None and clearance_time is None and not overlaps:
                projection = projected_box(row, axis_index)
                if projection is not None and projection[0] > 3.0:
                    clearance_time = elapsed
        run = VehicleRun(
            trial_id=trial.trial_id,
            vehicle_id=vehicle_id,
            role=str(config.get("role", "unknown")),
            route_axis=str(axis or ""),
            rows=rows,
            entry_time=entry_time,
            clearance_time=clearance_time,
            first_damage_time=first_damage_time,
            first_deviation_time=first_deviation_time,
        )
        run.label_quality = {target: vehicle_quality(run, target) for target in TARGETS}
        result.append(run)
    return result


def saved_label_check(trial: Trial, run: VehicleRun) -> dict[str, Any]:
    saved = trial.metadata.get("outcomes", {}).get(run.vehicle_id, {})
    if not saved:
        report = read_json(trial.folder / "validation_report.json")
        saved = report.get("outcomes", {}).get(run.vehicle_id, {})
    observed_step = max(
        (b["elapsed"] - a["elapsed"] for a, b in zip(run.rows, run.rows[1:]) if math.isfinite(a["elapsed"]) and math.isfinite(b["elapsed"]) and b["elapsed"] > a["elapsed"]),
        default=1.0 / 20.0,
    )
    checks: dict[str, Any] = {}
    for target, saved_key in (("entry", "entry_seconds"), ("clearance", "clearance_seconds")):
        expected = saved.get(saved_key)
        actual = run.entry_time if target == "entry" else run.clearance_time
        if expected is None and actual is None:
            checks[target] = {"matches": True, "saved": None, "recomputed": None}
        elif expected is None or actual is None:
            checks[target] = {"matches": False, "saved": expected, "recomputed": actual}
        else:
            matches = abs(float(expected) - actual) <= observed_step + 1e-6
            checks[target] = {"matches": matches, "saved": expected, "recomputed": actual, "tolerance_seconds": observed_step + 1e-6}
    return checks


def load_trial_folders(data_root: Path) -> list[Trial]:
    folders = sorted(path for path in data_root.glob("experiment_*/fresh_*") if path.is_dir())
    trials: list[Trial] = []
    seen_content: dict[str, str] = {}
    for folder in folders:
        batch_id = folder.parent.name
        trial_id = f"{batch_id}/{folder.name}"
        telemetry = folder / "telemetry.csv"
        metadata_path = folder / "metadata.json"
        geometry_path = folder / "geometry.json"
        validation_path = folder / "validation_report.json"
        reasons: list[str] = []
        metadata: dict[str, Any] = {}
        geometry: dict[str, Any] = {}
        digest = ""
        rows: list[dict[str, Any]] = []
        fields: list[str] = []
        try:
            if not telemetry.is_file() or telemetry.stat().st_size == 0:
                reasons.append("missing_or_empty_telemetry")
            else:
                digest = sha256_file(telemetry)
            if not metadata_path.is_file():
                reasons.append("missing_metadata")
            else:
                metadata = read_json(metadata_path)
            if not geometry_path.is_file():
                reasons.append("missing_geometry")
            else:
                geometry = read_json(geometry_path)
            if not validation_path.is_file():
                reasons.append("missing_validation_report")
            else:
                validation = read_json(validation_path)
                if validation.get("status") not in VALIDATION_STATUSES:
                    reasons.append(f"validation_status_{validation.get('status', 'missing')}")
                if validation.get("issues"):
                    reasons.append("validation_issues_present")
            if metadata.get("status") != "complete":
                reasons.append(f"trial_status_{metadata.get('status', 'missing')}")
            if telemetry.is_file() and telemetry.stat().st_size:
                rows, fields = load_rows(telemetry)
                if not rows:
                    reasons.append("no_telemetry_rows")
                if "bbox_json" not in fields:
                    reasons.append("missing_spawn_bbox_field")
                validation_report = read_json(validation_path) if validation_path.is_file() else {}
                if validation_report.get("sample_count") is not None and validation_report["sample_count"] != len(rows):
                    reasons.append("validation_sample_count_mismatch")
                subject_ids = {
                    item.get("vehicle_id") for item in metadata.get("configuration", [])
                    if isinstance(item, dict) and item.get("role") == "subject"
                }
                if subject_ids and any(
                    row.get("vehicle_id") in subject_ids and row.get("bbox") is None for row in rows
                ):
                    reasons.append("missing_subject_spawn_bbox_data")
            if digest and digest in seen_content and not reasons:
                duplicate_of = seen_content[digest]
                reasons.append("duplicate_telemetry_content")
            else:
                duplicate_of = None
                if digest and not reasons:
                    seen_content[digest] = trial_id
        except (OSError, json.JSONDecodeError, csv.Error, ValueError, TypeError) as exc:
            duplicate_of = None
            reasons.append(f"read_error:{type(exc).__name__}:{exc}")
        config_hash = route_configuration_signature(metadata, geometry) if metadata and geometry else ""
        seed = metadata.get("seed")
        group_id = f"seed:{seed}" if seed is not None else f"config:{config_hash or trial_id}"
        trial = Trial(
            trial_id=trial_id,
            batch_id=batch_id,
            folder=folder,
            metadata=metadata,
            geometry=geometry,
            digest=digest,
            seed=seed,
            config_hash=config_hash,
            group_id=group_id,
            reason=";".join(dict.fromkeys(reasons)) if reasons else None,
            duplicate_of=duplicate_of,
            row_count=len(rows),
        )
        if not trial.reason:
            trial.vehicle_runs = recompute_vehicle_events(trial, rows)
            if not any(vehicle.role == "subject" for vehicle in trial.vehicle_runs):
                trial.reason = "no_subject_vehicle_rows"
            elif any(not run.rows for run in trial.vehicle_runs):
                trial.reason = "empty_vehicle_trajectory"
        trials.append(trial)
    return trials


def assign_group_splits(trials: list[Trial], seed: int) -> dict[str, str]:
    unique_groups = sorted({trial.group_id for trial in trials if trial.reason is None and trial.duplicate_of is None})
    if len(unique_groups) < 3:
        return {group: "unassigned" for group in unique_groups}
    indexes = np.arange(len(unique_groups)).reshape(-1, 1)
    labels = np.asarray(unique_groups, dtype=object)
    first = GroupShuffleSplit(n_splits=1, test_size=0.4, random_state=seed)
    train_idx, temporary_idx = next(first.split(indexes, groups=labels))
    train_groups = set(labels[train_idx].tolist())
    temporary_groups = labels[temporary_idx]
    if len(temporary_groups) < 2:
        return {group: "unassigned" for group in unique_groups}
    second = GroupShuffleSplit(n_splits=1, test_size=0.5, random_state=seed + 1)
    validation_idx, test_idx = next(second.split(np.arange(len(temporary_groups)).reshape(-1, 1), groups=temporary_groups))
    validation_groups = set(temporary_groups[validation_idx].tolist())
    test_groups = set(temporary_groups[test_idx].tolist())
    result: dict[str, str] = {}
    for group in unique_groups:
        if group in train_groups:
            result[group] = "train"
        elif group in validation_groups:
            result[group] = "validation"
        elif group in test_groups:
            result[group] = "test"
        else:
            result[group] = "unassigned"
    return result


def group_and_sample_duplicate_configs(trials: list[Trial]) -> None:
    """Join trials that share either a seed or a randomized route configuration."""
    parents = list(range(len(trials)))

    def find(index: int) -> int:
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    def union(left: int, right: int) -> None:
        a, b = find(left), find(right)
        if a != b:
            parents[b] = a

    seed_owner: dict[str, int] = {}
    config_owner: dict[str, int] = {}
    for index, trial in enumerate(trials):
        if trial.seed is not None:
            key = str(trial.seed)
            if key in seed_owner:
                union(index, seed_owner[key])
            else:
                seed_owner[key] = index
        if trial.config_hash:
            if trial.config_hash in config_owner:
                union(index, config_owner[trial.config_hash])
            else:
                config_owner[trial.config_hash] = index
    root_names: dict[int, str] = {}
    for index, trial in enumerate(trials):
        root = find(index)
        root_names.setdefault(root, f"group:{trial.trial_id}")
        trial.group_id = root_names[root]


def sample_trajectory(rows: list[dict[str, Any]], max_hz: float = MAX_SAMPLE_HZ) -> list[dict[str, Any]]:
    sampled: list[dict[str, Any]] = []
    last_sim_time = -math.inf
    minimum_interval = 1.0 / max_hz
    for row in rows:
        timestamp = row["sim_time"]
        if not math.isfinite(timestamp):
            continue
        if not sampled or timestamp - last_sim_time + 1e-9 >= minimum_interval:
            sampled.append(row)
            last_sim_time = timestamp
    return sampled


def history_features(rows: list[dict[str, Any]]) -> dict[int, tuple[float, float, float, float]]:
    history: deque[tuple[float, float]] = deque()
    result: dict[int, tuple[float, float, float, float]] = {}
    prior: list[tuple[float, float]] = []
    for row in rows:
        now = row["elapsed"]
        speed = row["speed"]
        if not math.isfinite(now):
            continue
        while history and history[0][0] < now - 1.0 - 1e-9:
            history.popleft()
        def speed_at_lag(lag: float) -> float:
            candidates = [value for timestamp, value in prior if timestamp <= now - lag + 1e-9 and now - timestamp <= lag + 0.6]
            return candidates[-1] if candidates else math.nan
        values = [value for _, value in history]
        if math.isfinite(speed):
            values.append(speed)
        result[row["frame_id"]] = (
            speed_at_lag(0.5),
            speed_at_lag(1.0),
            float(np.mean(values)) if values else math.nan,
            float(np.std(values)) if values else math.nan,
        )
        if math.isfinite(speed):
            history.append((now, speed))
            prior.append((now, speed))
    return result


def nearest_vehicle_features(row: dict[str, Any]) -> tuple[float, float]:
    return row["relative_distance"], row["relative_speed"]


def create_feature_record(trial: Trial, vehicle: VehicleRun, row: dict[str, Any], history: tuple[float, float, float, float], metadata_configs: dict[str, dict[str, Any]]) -> dict[str, Any]:
    axis = 0 if vehicle.route_axis == "x" else 1
    projection = projected_box(row, axis)
    if projection is None:
        front_progress = row["front_progress"]
        rear_progress = row["rear_progress"]
    else:
        rear_progress, front_progress = projection[0], projection[1]
    along_speed = row["vx"] if axis == 0 else row["vy"]
    along_acceleration = row["ax"] if axis == 0 else row["ay"]
    if vehicle.route_axis not in {"x", "y"}:
        along_speed = math.nan
        along_acceleration = math.nan
    dimensions = trial.metadata.get("vehicle_dimensions", {}).get(vehicle.vehicle_id, {})
    config = metadata_configs.get(vehicle.vehicle_id, {})
    history_05, history_10, mean_1, std_1 = history
    nearest_distance, nearest_relative_speed = nearest_vehicle_features(row)
    return {
        "distance_to_entry_m": -3.0 - front_progress if math.isfinite(front_progress) else math.nan,
        "distance_to_rear_clearance_m": 3.0 - rear_progress if math.isfinite(rear_progress) else math.nan,
        "forward_speed_mps": along_speed,
        "forward_acceleration_mps2": along_acceleration,
        "speed_0_5s_ago_mps": history_05,
        "speed_1s_ago_mps": history_10,
        "speed_trailing_1s_mean_mps": mean_1,
        "speed_trailing_1s_std_mps": std_1,
        "vehicle_length_m": as_float(dimensions.get("length")),
        "vehicle_width_m": as_float(dimensions.get("width")),
        "vehicle_height_m": as_float(dimensions.get("height")),
        "nearest_vehicle_distance_m": nearest_distance,
        "nearest_vehicle_relative_speed_mps": nearest_relative_speed,
        "trial_id": trial.trial_id,
        "batch_id": trial.batch_id,
        "group_id": trial.group_id,
        "vehicle_id": vehicle.vehicle_id,
        "role": vehicle.role,
        "seed": trial.seed,
        "elapsed": row["elapsed"],
        "sim_time": row["sim_time"],
        "frame_id": row["frame_id"],
        "speed_mps": row["speed"],
        "route_id": config.get("route_id"),
    }


def build_examples(trials: list[Trial]) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    examples: dict[str, list[dict[str, Any]]] = {target: [] for target in TARGETS}
    audit: dict[str, Any] = {}
    for trial in trials:
        trial_info: dict[str, Any] = {"reason": trial.reason, "vehicles": {}}
        if trial.reason is None and trial.duplicate_of is None:
            metadata_configs = config_map(trial.metadata)
            for vehicle in trial.vehicle_runs:
                if vehicle.role != "subject":
                    trial_info["vehicles"][vehicle.vehicle_id] = {
                        "role": vehicle.role,
                        "entry": {"status": "excluded", "reason": "background_route_outside_conflict_zone_training_scope"},
                        "clearance": {"status": "excluded", "reason": "background_route_outside_conflict_zone_training_scope"},
                    }
                    continue
                sample_rows = sample_trajectory(vehicle.rows)
                histories = history_features(sample_rows)
                consistency = saved_label_check(trial, vehicle)
                for target in TARGETS:
                    quality = dict(vehicle.label_quality[target])
                    label_key = "entry_time" if target == "entry" else "clearance_time"
                    event_time = getattr(vehicle, label_key)
                    if quality["status"] == "eligible" and not consistency[target]["matches"]:
                        quality.update(status="excluded", reason="saved_label_mismatch", saved_label_check=consistency[target])
                    else:
                        quality["saved_label_check"] = consistency[target]
                    vehicle_audit = trial_info["vehicles"].setdefault(vehicle.vehicle_id, {"role": vehicle.role})
                    vehicle_audit[target] = quality
                    if quality["status"] != "eligible" or event_time is None:
                        continue
                    for row in sample_rows:
                        if not math.isfinite(row["elapsed"]) or row["elapsed"] >= event_time - 1e-9:
                            continue
                        history = histories.get(row["frame_id"])
                        if history is None:
                            continue
                        record = create_feature_record(trial, vehicle, row, history, metadata_configs)
                        record["target_seconds"] = max(0.0, event_time - row["elapsed"])
                        record["target"] = target
                        examples[target].append(record)
        audit[trial.trial_id] = trial_info
    return examples, audit


def balance_weights(records: list[dict[str, Any]]) -> np.ndarray:
    by_trial: dict[str, int] = defaultdict(int)
    for record in records:
        by_trial[record["trial_id"]] += 1
    if not records:
        return np.asarray([], dtype=float)
    weights = np.asarray([1.0 / by_trial[record["trial_id"]] for record in records], dtype=float)
    return weights * (len(weights) / weights.sum())


def weighted_quantile(values: np.ndarray, weights: np.ndarray, quantile: float) -> float:
    if len(values) == 0:
        return math.nan
    order = np.argsort(values)
    sorted_values = values[order]
    sorted_weights = weights[order]
    cumulative = np.cumsum(sorted_weights)
    cutoff = quantile * cumulative[-1]
    index = int(np.searchsorted(cumulative, cutoff, side="left"))
    return float(sorted_values[min(index, len(sorted_values) - 1)])


def run_balanced_metrics(records: list[dict[str, Any]], predictions: np.ndarray, selected: list[int] | None = None) -> dict[str, Any]:
    selected = list(range(len(records))) if selected is None else selected
    if not selected:
        return {"rows": 0, "trials": 0, "groups": 0, "mae_seconds": None, "p95_absolute_error_seconds": None, "coverage": 0.0}
    selected_records = [records[index] for index in selected]
    truth = np.asarray([record["target_seconds"] for record in selected_records], dtype=float)
    predicted = np.maximum(0.0, np.asarray([predictions[index] for index in selected], dtype=float))
    errors = np.abs(truth - predicted)
    weights = balance_weights(selected_records)
    return {
        "rows": len(selected_records),
        "trials": len({record["trial_id"] for record in selected_records}),
        "groups": len({record["group_id"] for record in selected_records}),
        "mae_seconds": float(np.average(errors, weights=weights)),
        "p95_absolute_error_seconds": weighted_quantile(errors, weights, 0.95),
        "coverage": float(np.isfinite(predicted).mean()),
        "mean_target_seconds": float(np.average(truth, weights=weights)),
    }


def metrics_for_predictions(records: list[dict[str, Any]], predictions: np.ndarray) -> dict[str, Any]:
    metrics: dict[str, Any] = {"all": run_balanced_metrics(records, predictions)}
    moving_indices = [index for index, record in enumerate(records) if record["forward_speed_mps"] > 0.2]
    stopped_indices = [index for index, record in enumerate(records) if not record["forward_speed_mps"] > 0.2]
    metrics["stopped_or_slow_ml"] = run_balanced_metrics(records, predictions, stopped_indices)
    baseline_values: list[float] = []
    baseline_records: list[dict[str, Any]] = []
    baseline_indices: list[int] = []
    distance_key = "distance_to_entry_m" if records and records[0]["target"] == "entry" else "distance_to_rear_clearance_m"
    for index in moving_indices:
        record = records[index]
        speed = record["forward_speed_mps"]
        distance = record[distance_key]
        if math.isfinite(speed) and speed > 0.2 and math.isfinite(distance):
            baseline_values.append(max(0.0, distance / speed))
            baseline_records.append(record)
            baseline_indices.append(index)
    model_common = run_balanced_metrics(records, predictions, baseline_indices)
    baseline = run_balanced_metrics(baseline_records, np.asarray(baseline_values, dtype=float))
    metrics["moving_common_rows"] = {"model": model_common, "distance_over_speed_baseline": baseline}
    metrics["baseline_unavailable_stopped_or_missing"] = len(records) - len(baseline_indices)
    return metrics


def fit_features(records: list[dict[str, Any]]) -> np.ndarray:
    return np.asarray([[as_float(record.get(feature)) for feature in FEATURES] for record in records], dtype=float)


def split_counts(records: list[dict[str, Any]], split_by_group: dict[str, str]) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {}
    for split_name in ("train", "validation", "test"):
        matching = [record for record in records if split_by_group.get(record["group_id"]) == split_name]
        result[split_name] = {
            "rows": len(matching),
            "trials": len({record["trial_id"] for record in matching}),
            "groups": len({record["group_id"] for record in matching}),
        }
    return result


def train_target(target: str, records: list[dict[str, Any]], split_by_group: dict[str, str], seed: int, output_dir: Path) -> dict[str, Any]:
    counts = split_counts(records, split_by_group)
    report: dict[str, Any] = {"status": "insufficient_data", "split_counts": counts, "candidate_validation": []}
    if any(counts[split]["groups"] < MIN_SPLIT_GROUPS[split] for split in MIN_SPLIT_GROUPS):
        report["reason"] = "not_enough_independent_scenario_groups_for_required_train_validation_test_split"
        return report
    train_records = [record for record in records if split_by_group.get(record["group_id"]) == "train"]
    validation_records = [record for record in records if split_by_group.get(record["group_id"]) == "validation"]
    test_records = [record for record in records if split_by_group.get(record["group_id"]) == "test"]
    x_train, y_train = fit_features(train_records), np.asarray([record["target_seconds"] for record in train_records])
    w_train = balance_weights(train_records)
    x_validation = fit_features(validation_records)
    best: tuple[tuple[float, float], dict[str, Any]] | None = None
    for learning_rate, max_leaf_nodes in GRID:
        model = HistGradientBoostingRegressor(
            learning_rate=learning_rate,
            max_leaf_nodes=max_leaf_nodes,
            max_iter=200,
            min_samples_leaf=20,
            l2_regularization=1.0,
            early_stopping=False,
            random_state=seed,
        )
        model.fit(x_train, y_train, sample_weight=w_train)
        candidate_dir = output_dir / "models" / "candidates"
        candidate_dir.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            model,
            candidate_dir / f"{target}_lr-{learning_rate:g}_leaves-{max_leaf_nodes}.joblib",
            compress=3,
        )
        validation_prediction = np.maximum(0.0, model.predict(x_validation))
        validation_result = run_balanced_metrics(validation_records, validation_prediction)
        candidate = {
            "learning_rate": learning_rate,
            "max_leaf_nodes": max_leaf_nodes,
            "max_iter": 200,
            "min_samples_leaf": 20,
            "l2_regularization": 1.0,
            "validation": validation_result,
        }
        report["candidate_validation"].append(candidate)
        score = (validation_result["mae_seconds"], validation_result["p95_absolute_error_seconds"])
        if best is None or score < best[0]:
            best = (score, candidate)
    assert best is not None
    chosen = best[1]
    training_validation = train_records + validation_records
    final = HistGradientBoostingRegressor(
        learning_rate=chosen["learning_rate"],
        max_leaf_nodes=chosen["max_leaf_nodes"],
        max_iter=200,
        min_samples_leaf=20,
        l2_regularization=1.0,
        early_stopping=False,
        random_state=seed,
    )
    final.fit(
        fit_features(training_validation),
        np.asarray([record["target_seconds"] for record in training_validation]),
        sample_weight=balance_weights(training_validation),
    )
    x_test = fit_features(test_records)
    test_prediction = np.maximum(0.0, final.predict(x_test))
    test_metrics = metrics_for_predictions(test_records, test_prediction)
    common = test_metrics["moving_common_rows"]
    model_common = common["model"]
    baseline = common["distance_over_speed_baseline"]
    acceptance = "insufficient_common_moving_rows"
    if model_common["rows"] > 0 and baseline["rows"] > 0:
        acceptance = "improves_offline_test_metrics" if (
            model_common["mae_seconds"] < baseline["mae_seconds"]
            and model_common["p95_absolute_error_seconds"] <= baseline["p95_absolute_error_seconds"]
        ) else "does_not_meet_offline_improvement_rule"
    report.update(
        status="evaluated",
        selected_hyperparameters={
            key: chosen[key] for key in ("learning_rate", "max_leaf_nodes", "max_iter", "min_samples_leaf", "l2_regularization")
        },
        selected_validation=chosen["validation"],
        test_metrics=test_metrics,
        offline_improvement_rule=acceptance,
        model_file=f"models/{target}.joblib",
        trained_rows=len(training_validation),
    )
    (output_dir / "models").mkdir(parents=True, exist_ok=True)
    joblib.dump(final, output_dir / "models" / f"{target}.joblib", compress=3)
    return report


def heldout_predictions(examples: dict[str, list[dict[str, Any]]], split_by_group: dict[str, str], model_results: dict[str, Any], output_path: Path) -> None:
    fieldnames = [
        "target", "split", "trial_id", "group_id", "seed", "vehicle_id", "elapsed_seconds",
        "truth_seconds", "prediction_seconds", "baseline_seconds", "forward_speed_mps",
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        for target, records in examples.items():
            if model_results.get(target, {}).get("status") != "evaluated":
                continue
            model = joblib.load(output_path.parent / "models" / f"{target}.joblib")
            test_records = [record for record in records if split_by_group.get(record["group_id"]) == "test"]
            predictions = np.maximum(0.0, model.predict(fit_features(test_records))) if test_records else np.asarray([])
            distance_key = "distance_to_entry_m" if target == "entry" else "distance_to_rear_clearance_m"
            for record, prediction in zip(test_records, predictions):
                speed = record["forward_speed_mps"]
                distance = record[distance_key]
                baseline = max(0.0, distance / speed) if math.isfinite(speed) and speed > 0.2 and math.isfinite(distance) else ""
                writer.writerow({
                    "target": target,
                    "split": "test",
                    "trial_id": record["trial_id"],
                    "group_id": record["group_id"],
                    "seed": record["seed"],
                    "vehicle_id": record["vehicle_id"],
                    "elapsed_seconds": f"{record['elapsed']:.9f}",
                    "truth_seconds": f"{record['target_seconds']:.9f}",
                    "prediction_seconds": f"{prediction:.9f}",
                    "baseline_seconds": baseline if isinstance(baseline, str) else f"{baseline:.9f}",
                    "forward_speed_mps": f"{speed:.9f}" if math.isfinite(speed) else "",
                })


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=ROOT / "uriel_experiment", help="root containing experiment_*/fresh_*/ data")
    parser.add_argument("--output", type=Path, default=ROOT / "runs" / "ml-arrival", help="local parent directory for a new UUID output folder")
    parser.add_argument("--seed", type=int, default=42, help="deterministic grouped split and model seed")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = make_parser().parse_args(argv)
    data_root = args.data_root.expanduser().resolve()
    output_parent = args.output.expanduser().resolve()
    output_dir = output_parent / f"pilot-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
    output_dir.mkdir(parents=True, exist_ok=False)

    trials = load_trial_folders(data_root)
    group_and_sample_duplicate_configs(trials)
    split_by_group = assign_group_splits(trials, args.seed)
    for trial in trials:
        if trial.duplicate_of is None and trial.reason is None:
            trial.reason = None
    examples, label_audit = build_examples(trials)

    audit = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "data_root": str(data_root),
        "max_sampling_hz": MAX_SAMPLE_HZ,
        "zone_definition_m": {"x": [-3.0, 3.0], "y": [-3.0, 3.0]},
        "split_seed": args.seed,
        "trial_count": len(trials),
        "accepted_unique_trials": sum(trial.reason is None and trial.duplicate_of is None for trial in trials),
        "duplicate_telemetry_trials": sum(trial.duplicate_of is not None for trial in trials),
        "trial_audit": [
            {
                "trial_id": trial.trial_id,
                "batch_id": trial.batch_id,
                "path": str(trial.folder),
                "status": trial.metadata.get("status"),
                "validation_status": validation_status_for_audit(trial.folder / "validation_report.json"),
                "seed": trial.seed,
                "telemetry_sha256": trial.digest,
                "configuration_sha256": trial.config_hash,
                "group_id": trial.group_id,
                "split": split_by_group.get(trial.group_id),
                "duplicate_of": trial.duplicate_of,
                "row_count": trial.row_count,
                "excluded_reason": trial.reason,
                "labels": label_audit.get(trial.trial_id, {}),
            }
            for trial in trials
        ],
        "target_sample_counts": {
            target: {
                "rows": len(records),
                "trials": len({record["trial_id"] for record in records}),
                "groups": len({record["group_id"] for record in records}),
                "split_counts": split_counts(records, split_by_group),
            }
            for target, records in examples.items()
        },
    }
    write_json(output_dir / "audit.json", audit)

    split_manifest = {
        "seed": args.seed,
        "method": "GroupShuffleSplit: 60% train, then split remaining groups evenly between validation and test",
        "grouping": "connected components of repeated seed and identical randomized scenario configuration across folders",
        "minimum_group_counts": MIN_SPLIT_GROUPS,
        "groups": [
            {"group_id": group, "split": split}
            for group, split in sorted(split_by_group.items())
        ],
        "trials": [
            {"trial_id": trial.trial_id, "group_id": trial.group_id, "split": split_by_group.get(trial.group_id), "included": trial.reason is None and trial.duplicate_of is None}
            for trial in trials
        ],
    }
    write_json(output_dir / "split_manifest.json", split_manifest)
    write_json(output_dir / "feature_schema.json", {
        "version": 1,
        "features_in_order": FEATURES,
        "units": {
            "distance_to_entry_m": "m",
            "distance_to_rear_clearance_m": "m",
            "forward_speed_mps": "m/s",
            "forward_acceleration_mps2": "m/s^2",
            "speed_0_5s_ago_mps": "m/s",
            "speed_1s_ago_mps": "m/s",
            "speed_trailing_1s_mean_mps": "m/s",
            "speed_trailing_1s_std_mps": "m/s",
            "vehicle_length_m": "m",
            "vehicle_width_m": "m",
            "vehicle_height_m": "m",
            "nearest_vehicle_distance_m": "m",
            "nearest_vehicle_relative_speed_mps": "m/s",
        },
        "targets": {"entry": "remaining seconds until first sampled spawn-OOBB proxy overlaps the virtual conflict square", "clearance": "remaining seconds until spawn-OOBB proxy rear is beyond 3m and no longer overlaps the virtual conflict square"},
        "causality": "all dynamic features are from the current or earlier sampled frame; no run identity, seed, colour, event time or future outcome is a model input",
        "missing_values": "kept as NaN and handled by HistGradientBoostingRegressor",
        "row_sampling": f"at most {MAX_SAMPLE_HZ:g} Hz, selected from recorded frames by simulation timestamps; no interpolation",
    })
    write_json(output_dir / "environment.json", {
        "python": sys.version,
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "numpy": np.__version__,
        "scikit_learn": sklearn.__version__,
        "joblib": joblib.__version__,
        "script_sha256": sha256_file(Path(__file__).resolve()),
    })

    model_results: dict[str, Any] = {}
    for target in TARGETS:
        model_results[target] = train_target(target, examples[target], split_by_group, args.seed, output_dir)
    write_json(output_dir / "evaluation_report.json", {
        "status": "complete" if all(result["status"] == "evaluated" for result in model_results.values()) else "insufficient_data",
        "models": model_results,
        "limitations": [
            "labels use virtual Small Grid geometry and spawn OOBB proxies rather than calibrated deforming bodies",
            "damage and route deviation are treated as label-quality exclusions when observed before the target event",
            "censored target times remain null and are excluded from ordinary regression fitting",
            "verified contact labels are unavailable and not used",
            "the recordings cover a narrow seeded Small Grid scenario; offline model results do not establish vehicle-control safety or generalization",
        ],
    })
    heldout_predictions(examples, split_by_group, model_results, output_dir / "heldout_predictions.csv")
    print(output_dir)
    for target, report in model_results.items():
        print(f"{target}: {report['status']}")
        if report.get("status") == "evaluated":
            print(json.dumps(report["test_metrics"], sort_keys=True))
            print("offline_rule=" + report["offline_improvement_rule"])
    return 0 if all(result["status"] == "evaluated" for result in model_results.values()) else 2


if __name__ == "__main__":
    raise SystemExit(main())
