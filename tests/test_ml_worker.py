import unittest

from scripts.ml_worker import FEATURES, Worker


class ConstantModel:
    def __init__(self, value: float) -> None:
        self.value = value

    def predict(self, _rows):
        return [self.value]


class ArrivalWorkerTests(unittest.TestCase):
    def test_uses_ordered_feature_allowlist_and_returns_versioned_predictions(self):
        worker = Worker({"entry": ConstantModel(1.25), "clearance": ConstantModel(2.5)}, "test-model")
        values = {feature: None for feature in FEATURES}
        response = worker.predict({"type": "predict_batch", "features": [{"vehicle_id": "car-a", "values": values}]})
        self.assertEqual(response["status"], "ok")
        self.assertEqual(response["model_version"], "test-model")
        self.assertEqual(response["predictions"][0]["vehicle_id"], "car-a")
        self.assertEqual(response["predictions"][0]["entry_eta_s"], 1.25)
        self.assertEqual(response["predictions"][0]["rear_clearance_eta_s"], 2.5)

    def test_rejects_missing_or_extra_features(self):
        worker = Worker({"entry": ConstantModel(1), "clearance": ConstantModel(1)}, "test-model")
        for values in ({}, {**{feature: None for feature in FEATURES}, "future_leak": 9}):
            with self.assertRaisesRegex(ValueError, "feature keys"):
                worker.predict({"type": "predict_batch", "features": [{"vehicle_id": "car-a", "values": values}]})

    def test_rejects_nonfinite_model_outputs(self):
        worker = Worker({"entry": ConstantModel(float("nan")), "clearance": ConstantModel(1)}, "bad-model")
        values = {feature: None for feature in FEATURES}
        with self.assertRaisesRegex(ValueError, "nonfinite"):
            worker.predict({"type": "predict_batch", "features": [{"vehicle_id": "car-a", "values": values}]})

    def test_rejects_batches_over_limit(self):
        worker = Worker({"entry": ConstantModel(1), "clearance": ConstantModel(1)}, "test-model")
        with self.assertRaisesRegex(ValueError, "at most 100"):
            worker.predict({"type": "predict_batch", "features": [{}] * 101})


if __name__ == "__main__":
    unittest.main()
