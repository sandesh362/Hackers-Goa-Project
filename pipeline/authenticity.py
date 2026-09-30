"""Face crop quality metrics and optional local deepfake image classification."""
from __future__ import annotations

from functools import lru_cache
from typing import Any

import numpy as np
from PIL import Image

MODEL_ID = "prithivMLmods/Deep-Fake-Detector-v2-Model"
MODEL_REVISION = "3a99ae26f52c7ac7c3a53103b6cf3a8b617f7093"  # Pinned Hugging Face commit for reproducibility.
FRAMEWORK = "transformers (PyTorch backend)"
# Conservative display bands, not calibrated certainty claims. The source model is
# a general image classifier rather than a forensic detector validated on this dataset.
MANIPULATION_THRESHOLD = 0.65
AUTHENTIC_THRESHOLD = 0.35
MIN_FACE_SIDE = 64


def analyze_quality(crop: np.ndarray, image_size: tuple[int, int], face_detected: bool) -> dict[str, Any]:
    """Return a transparent deterministic quality score from 0–100 and its components."""
    if crop.size == 0 or not face_detected:
        return {"score": 0, "face_detected": face_detected, "face_size": [0, 0],
                "image_size": list(image_size), "blur_variance": 0.0, "brightness": 0.0,
                "warnings": ["No detected face available for quality analysis."]}
    rgb = np.asarray(crop, dtype=np.float32)
    gray = rgb.mean(axis=2)
    h, w = gray.shape
    # Variance of a discrete Laplacian is a simple, reproducible sharpness proxy.
    lap = -4 * gray[1:-1, 1:-1] + gray[:-2, 1:-1] + gray[2:, 1:-1] + gray[1:-1, :-2] + gray[1:-1, 2:]
    blur = float(lap.var()) if lap.size else 0.0
    brightness = float(gray.mean() / 255.0)
    contrast = float(gray.std() / 128.0)
    face_fraction = (w * h) / max(1, image_size[0] * image_size[1])
    resolution_score = min(1.0, min(w, h) / 160.0)
    sharpness_score = min(1.0, blur / 250.0)
    exposure_score = max(0.0, 1.0 - abs(brightness - 0.5) / 0.5)
    contrast_score = min(1.0, contrast)
    size_score = min(1.0, face_fraction / 0.12)
    score = round(100 * (0.30 * resolution_score + 0.25 * sharpness_score +
                         0.15 * exposure_score + 0.15 * contrast_score + 0.15 * size_score))
    warnings = []
    if min(w, h) < MIN_FACE_SIDE:
        warnings.append("Face crop is very small; model output may be unreliable.")
    if sharpness_score < 0.2:
        warnings.append("Face crop appears blurred.")
    if brightness < 0.12 or brightness > 0.9:
        warnings.append("Face crop has extreme brightness.")
    return {"score": score, "face_detected": True, "face_size": [w, h], "image_size": list(image_size),
            "blur_variance": round(blur, 2), "brightness": round(brightness, 3), "contrast": round(contrast, 3),
            "warnings": warnings}


@lru_cache(maxsize=1)
def _load_classifier():
    """Load the pretrained classifier once on first use; optional deps are isolated."""
    import torch
    from transformers import pipeline
    device = 0 if torch.cuda.is_available() else -1
    return pipeline("image-classification", model=MODEL_ID, revision=MODEL_REVISION, device=device)


def analyze_authenticity(crop: np.ndarray, face_detected: bool) -> dict[str, Any]:
    """Classify a detected face crop; failures produce an explicit unavailable result."""
    metadata = {"name": MODEL_ID, "version": MODEL_REVISION, "framework": FRAMEWORK,
                "task": "face_manipulation_detection"}
    if not face_detected or crop.size == 0:
        return {"available": False, "label": "not_evaluated", "message": "No detected face to evaluate.", "model": metadata}
    if min(crop.shape[:2]) < MIN_FACE_SIDE:
        return {"available": False, "label": "not_evaluated", "message": "Face resolution is too low for reliable analysis.", "model": metadata}
    try:
        image = Image.fromarray(np.asarray(crop, dtype=np.uint8)).convert("RGB")
        predictions = _load_classifier()(image, top_k=None)
        scores = {str(item["label"]).lower(): float(item["score"]) for item in predictions}
        fake_score = next((value for key, value in scores.items() if any(word in key for word in ("fake", "manipulat", "synthetic"))), None)
        real_score = next((value for key, value in scores.items() if any(word in key for word in ("real", "authentic", "genuine"))), None)
        if fake_score is None or real_score is None:
            return {"available": False, "label": "not_evaluated", "message": "Model returned unrecognized class labels.", "model": metadata}
        total = fake_score + real_score
        manipulation = fake_score / total if total else 0.5
        authenticity = real_score / total if total else 0.5
        label = "potentially_manipulated" if manipulation >= MANIPULATION_THRESHOLD else (
            "likely_authentic" if manipulation <= AUTHENTIC_THRESHOLD else "inconclusive")
        return {"available": True, "label": label, "manipulation_probability": round(manipulation, 6),
                "authenticity_probability": round(authenticity, 6), "confidence": round(max(manipulation, authenticity), 6),
                "thresholds": {"authentic_max_manipulation": AUTHENTIC_THRESHOLD,
                               "manipulated_min_manipulation": MANIPULATION_THRESHOLD}, "model": metadata,
                "disclaimer": "Probabilistic model output; not proof of authenticity or manipulation."}
    except Exception as exc:
        # Never expose filesystem paths or dependency traceback through the API.
        return {"available": False, "label": "not_evaluated",
                "message": f"Authenticity model unavailable ({exc.__class__.__name__}). Install optional ML dependencies and check model access.",
                "model": metadata}
