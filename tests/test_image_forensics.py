import numpy as np
from PIL import Image

from pipeline.blockchain import evidence_hash
from pipeline import image_forensics
from pipeline.xai import save_explanation_images


def test_heatmap_and_overlay_match_original_dimensions(tmp_path):
    original = Image.new("RGB", (93, 57), (80, 100, 120))
    attribution = np.linspace(0, 1, 32 * 24, dtype=np.float32).reshape(24, 32)
    files = save_explanation_images(original, attribution, tmp_path)
    heat = Image.open(files["heatmap"])
    overlay = Image.open(files["overlay"])
    assert heat.size == original.size == overlay.size
    values = np.asarray(heat)
    assert values.min() == 0 and values.max() == 255


def test_forensics_failure_is_structured_and_nonfatal(monkeypatch, tmp_path):
    image_path = tmp_path / "valid.png"
    Image.new("RGB", (80, 80), "white").save(image_path)
    monkeypatch.setattr(image_forensics, "_load_classifier", lambda: (_ for _ in ()).throw(OSError("offline")))
    result = image_forensics.analyze_image_forensics(image_path, tmp_path / "artifacts")
    assert result["available"] is False
    assert result["classification"] == "not_evaluated"
    assert result["explainability"]["heatmap_available"] is False


def test_forensic_fields_change_evidence_digest():
    record = {"image_sha256": "original", "image_forensics": {
        "classification": "inconclusive", "manipulation_score": 0.51,
        "explainability": {"method": "Integrated Gradients", "heatmap_sha256": "abc"}}}
    baseline = evidence_hash(record)
    record["image_forensics"]["manipulation_score"] = 0.12
    assert evidence_hash(record) != baseline
