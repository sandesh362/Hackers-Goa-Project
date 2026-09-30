"""Full-image manipulation classification with optional Integrated Gradients."""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from .authenticity import (AUTHENTIC_THRESHOLD, FRAMEWORK, MANIPULATION_THRESHOLD,
                           MODEL_ID, MODEL_REVISION, _load_classifier)
from .xai import integrated_gradients, save_explanation_images


def _class_scores(logits: Any, labels: dict[int, str]) -> tuple[float, float, int]:
    import torch
    probs = torch.softmax(logits[0].float(), dim=-1).detach().cpu().numpy()
    indexed = {int(idx): str(label).lower() for idx, label in labels.items()}
    fake_idx = next((i for i, label in indexed.items() if any(word in label for word in ("fake", "deepfake", "manipulat", "synthetic"))), None)
    real_idx = next((i for i, label in indexed.items() if any(word in label for word in ("real", "realism", "authentic", "genuine"))), None)
    if fake_idx is None or real_idx is None:
        raise ValueError("Model class labels do not identify real and manipulated classes.")
    total = float(probs[fake_idx] + probs[real_idx])
    if total <= 0:
        raise ValueError("Model returned invalid class scores.")
    return float(probs[fake_idx]) / total, float(probs[real_idx]) / total, fake_idx


def analyze_image_forensics(image_path: str | Path, output_dir: str | Path) -> dict[str, Any]:
    """Run full-image prediction, then independently attempt explanation generation."""
    model_info = {"name": MODEL_ID, "version": MODEL_REVISION, "framework": FRAMEWORK,
                  "task": "full_image_manipulation_classification"}
    try:
        with Image.open(image_path) as source:
            source.load()
            original = source.convert("RGB")
        classifier = _load_classifier()
        model = classifier.model
        processor = getattr(classifier, "image_processor", None) or getattr(classifier, "feature_extractor", None)
        if processor is None:
            raise RuntimeError("The model image processor is unavailable.")
        inputs = processor(images=original, return_tensors="pt")
        device = next(model.parameters()).device
        pixel_values = inputs["pixel_values"].to(device)
        import torch
        model.eval()
        with torch.inference_mode():
            logits = model(pixel_values=pixel_values).logits
        labels = model.config.id2label
        fake_score, authentic_score, fake_class = _class_scores(logits, labels)
        classification = "potentially_manipulated" if fake_score >= MANIPULATION_THRESHOLD else (
            "likely_authentic" if fake_score <= AUTHENTIC_THRESHOLD else "inconclusive")
        result: dict[str, Any] = {
            "available": True,
            "classification": classification,
            "manipulation_score": round(fake_score, 6),
            "authenticity_score": round(authentic_score, 6),
            "model": model_info,
            "input_size": list(inputs["pixel_values"].shape[-2:][::-1]),
            "thresholds": {"authentic_max_manipulation": AUTHENTIC_THRESHOLD,
                           "manipulated_min_manipulation": MANIPULATION_THRESHOLD},
            "disclaimer": "Model score is a learned class score, not an objective probability or proof.",
        }
        explanation: dict[str, Any] = {"method": "Integrated Gradients", "heatmap_available": False,
                                       "overlay_available": False,
                                       "interpretation": "Regions influencing the model prediction; not pixel-level manipulation ground truth."}
        try:
            attribution = integrated_gradients(model, processor, original, fake_class)
            paths = save_explanation_images(original, attribution, output_dir)
            explanation.update(heatmap_available=True, overlay_available=True,
                               target="manipulated-class score", steps=16,
                               heatmap_sha256=_sha256(paths["heatmap"]), overlay_sha256=_sha256(paths["overlay"]))
            # Paths are intentionally omitted from the public analysis object; the API supplies safe run-scoped URLs.
            result["_artifact_paths"] = {name: str(path) for name, path in paths.items()}
        except Exception as exc:
            explanation["message"] = f"Explanation unavailable ({exc.__class__.__name__})."
        result["explainability"] = explanation
        return result
    except Exception as exc:
        return {"available": False, "classification": "not_evaluated", "model": model_info,
                "message": f"Image forensics unavailable ({exc.__class__.__name__}).",
                "explainability": {"method": "Integrated Gradients", "heatmap_available": False,
                                   "overlay_available": False}}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()
