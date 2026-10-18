#!/usr/bin/env python3
"""Small localhost JSON-line server for the offline arrival ETA models."""

from __future__ import annotations

import argparse
import json
import math
import os
import socketserver
import sys
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import sklearn

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
from train_arrival import FEATURES  # noqa: E402


def load_models(directory: Path) -> tuple[dict[str, Any], str]:
    schema = json.loads((directory / "feature_schema.json").read_text(encoding="utf-8"))
    if (directory / "models" / "portable.json").exists():
        import hashlib
        from portable_eta import PortableRegressor
        path = directory / "models" / "portable.json"
        manifest = json.loads((directory / "portable_manifest.json").read_text())
        if schema.get("features") != FEATURES:
            raise ValueError("portable feature contract mismatch")
        if hashlib.sha256(path.read_bytes()).hexdigest() != manifest.get("sha256"):
            raise ValueError("portable model hash mismatch")
        if not manifest.get("native_parity_verified"):
            raise ValueError("portable model parity has not been verified")
        data = json.loads(path.read_text())
        models = {name: PortableRegressor(data[name]) for name in ("entry", "clearance")}
        fixtures = json.loads((directory / "portable_fixtures.json").read_text())
        matrix = np.asarray([[math.nan if v is None else v for v in row] for row in fixtures["features"]])
        for name, model in models.items():
            np.testing.assert_allclose(model.predict(matrix), fixtures[name], atol=1e-4, rtol=1e-5)
        return models, directory.name
    if (directory / "models" / "entry.ubj").exists():
        import hashlib
        import xgboost as xgb
        report = json.loads((directory / "evaluation_report.json").read_text())
        manifest = json.loads((directory / "artifact_manifest.json").read_text())
        if schema.get("features") != FEATURES or report.get("status") != "evaluated_exploratory":
            raise ValueError("XGBoost model schema or grouped evaluation is invalid")
        if report.get("xgboost_version") != xgb.__version__:
            raise ValueError("XGBoost model/runtime versions differ")
        models = {}
        for name in ("entry", "clearance"):
            filename = name + ".ubj"
            path = directory / "models" / filename
            if hashlib.sha256(path.read_bytes()).hexdigest() != manifest["models"].get(filename):
                raise ValueError("XGBoost model hash mismatch")
            model = xgb.XGBRegressor(n_jobs=2)
            model.load_model(path)
            model.set_params(device="cpu", n_jobs=2)
            models[name] = model
        # Warm both predictors before accepting the Rust client's bounded requests.
        for model in models.values():
            model.predict(np.zeros((1, len(FEATURES))))
        return models, directory.name
    if schema.get("features_in_order") != FEATURES:
        raise ValueError("feature_schema.json does not match the live Rust feature contract")
    report = json.loads((directory / "evaluation_report.json").read_text(encoding="utf-8"))
    if report.get("status") != "complete":
        raise ValueError("model run did not complete grouped offline evaluation")
    environment = json.loads((directory / "environment.json").read_text(encoding="utf-8"))
    expected = {
        "numpy": np.__version__,
        "scikit_learn": sklearn.__version__,
        "joblib": joblib.__version__,
    }
    mismatches = {
        name: (environment.get(name), version)
        for name, version in expected.items()
        if environment.get(name) != version
    }
    if mismatches:
        raise ValueError(f"model/runtime package versions differ: {mismatches}")
    models = {name: joblib.load(directory / "models" / f"{name}.joblib") for name in ("entry", "clearance")}
    return models, directory.name


class Worker:
    def __init__(self, models: dict[str, Any], model_version: str) -> None:
        self.models = models
        self.model_version = model_version

    def predict(self, request: dict[str, Any]) -> dict[str, Any]:
        rows = request.get("features")
        if request.get("type") != "predict_batch" or not isinstance(rows, list) or len(rows) > 100:
            raise ValueError("expected predict_batch with at most 100 feature rows")
        vehicle_ids: list[str] = []
        matrix: list[list[float]] = []
        for row in rows:
            vehicle_id = row.get("vehicle_id")
            values = row.get("values")
            if not isinstance(vehicle_id, str) or not isinstance(values, dict):
                raise ValueError("each row needs vehicle_id and values")
            if set(values) != set(FEATURES):
                raise ValueError("feature keys do not match the trained feature allowlist")
            vehicle_ids.append(vehicle_id)
            vector = []
            for feature in FEATURES:
                value = values[feature]
                number = math.nan if value is None else float(value)
                if not math.isfinite(number) and not math.isnan(number):
                    raise ValueError(f"invalid feature {feature}")
                vector.append(number)
            matrix.append(vector)
        if not rows:
            return {"status": "ok", "model_version": self.model_version, "predictions": []}
        features = np.asarray(matrix, dtype=np.float64)
        entry = self.models["entry"].predict(features)
        clearance = self.models["clearance"].predict(features)
        if not np.isfinite(entry).all() or not np.isfinite(clearance).all():
            raise ValueError("model returned nonfinite predictions")
        predictions = []
        for index, vehicle_id in enumerate(vehicle_ids):
            predictions.append({
                "vehicle_id": vehicle_id,
                "entry_eta_s": max(0.0, float(entry[index])),
                "rear_clearance_eta_s": max(0.0, float(clearance[index])),
                "status": "predicted",
            })
        return {"status": "ok", "model_version": self.model_version, "predictions": predictions}


class Handler(socketserver.StreamRequestHandler):
    def handle(self) -> None:
        line = self.rfile.readline(256 * 1024)
        if not line.endswith(b"\n"):
            return
        try:
            request = json.loads(line)
            response = self.server.worker.predict(request)  # type: ignore[attr-defined]
        except Exception as error:
            response = {"status": "error", "model_version": None, "predictions": [], "detail": str(error)}
        self.wfile.write(json.dumps(response, separators=(",", ":"), allow_nan=False).encode("utf-8") + b"\n")


class ThreadedServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", type=Path, default=Path(os.environ.get("URIEL_ML_MODELS", "runs/ml-arrival/current")))
    parser.add_argument("--bind", default=os.environ.get("URIEL_ML_BIND", "127.0.0.1:3100"))
    args = parser.parse_args()
    host, port_text = args.bind.rsplit(":", 1)
    models, version = load_models(args.models)
    server = ThreadedServer((host, int(port_text)), Handler)
    server.worker = Worker(models, version)  # type: ignore[attr-defined]
    print(f"arrival ML worker listening on {host}:{port_text}; model={version}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
