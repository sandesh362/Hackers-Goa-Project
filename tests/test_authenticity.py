import numpy as np

from pipeline import authenticity
from pipeline.blockchain import evidence_hash


def test_quality_is_measured_and_normalized():
    rng = np.random.default_rng(12)
    face = rng.integers(0, 256, (180, 150, 3), dtype=np.uint8)
    result = authenticity.analyze_quality(face, (600, 800), True)
    assert 0 <= result["score"] <= 100
    assert result["face_size"] == [150, 180]
    assert result["blur_variance"] > 0


def test_no_face_and_small_face_are_not_inferred():
    assert authenticity.analyze_authenticity(np.zeros((0, 0, 3)), False)["available"] is False
    small = authenticity.analyze_authenticity(np.zeros((32, 32, 3), dtype=np.uint8), True)
    assert small["available"] is False
    assert "too low" in small["message"]


def test_classifier_scores_drive_probabilities_and_band(monkeypatch):
    class FakeClassifier:
        def __call__(self, image, top_k):
            assert image.size == (80, 80)
            return [{"label": "Fake", "score": .2}, {"label": "Real", "score": .8}]
    monkeypatch.setattr(authenticity, "_load_classifier", lambda: FakeClassifier())
    result = authenticity.analyze_authenticity(np.ones((80, 80, 3), dtype=np.uint8), True)
    assert result["available"]
    assert result["manipulation_probability"] == .2
    assert result["authenticity_probability"] == .8
    assert result["label"] == "likely_authentic"
    assert result["model"]["name"] == authenticity.MODEL_ID


def test_model_exception_returns_warning(monkeypatch):
    def fail():
        raise OSError("download failed")
    monkeypatch.setattr(authenticity, "_load_classifier", fail)
    result = authenticity.analyze_authenticity(np.ones((80, 80, 3), dtype=np.uint8), True)
    assert result["available"] is False
    assert "OSError" in result["message"]


def test_authenticity_is_inside_hashable_evidence():
    record = {"face_hash": "abc", "authenticity": {"label": "likely_authentic", "manipulation_probability": .2}}
    original_hash = evidence_hash(record)
    altered = {**record, "authenticity": {**record["authenticity"], "manipulation_probability": .9}}
    assert evidence_hash(altered) != original_hash
