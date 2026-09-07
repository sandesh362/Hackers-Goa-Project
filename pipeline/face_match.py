"""Advisory face-embedding comparison for a discovered candidate image."""
from __future__ import annotations
import tempfile
from pathlib import Path
import numpy as np, requests, os
try:
    from .face_id import extract_face
except ImportError:  # supports `python pipeline/face_match.py` style execution
    from face_id import extract_face

def similarity_label(distance: float, threshold: float) -> str:
    if distance <= threshold: return "likely same person (advisory only)"
    return "inconclusive or different person (advisory only)"

def compare_candidate(original_encoding: np.ndarray, image_url: str | None) -> dict:
    if original_encoding.size == 0:
        return {"available": False, "message": "Face embedding was not available for this photo; reverse-image results are shown without an identity similarity score."}
    if not image_url:
        return {"available": False, "message": "No fetchable candidate image was provided; similarity was not evaluated."}
    try:
        response = requests.get(image_url, timeout=25); response.raise_for_status()
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            tmp.write(response.content); filename = tmp.name
        candidate = extract_face(filename)
        Path(filename).unlink(missing_ok=True)
        distance = float(np.linalg.norm(original_encoding - candidate.encoding))
        threshold = float(os.getenv("SIMILARITY_THRESHOLD", "0.6"))
        return {"available": True, "distance": round(distance, 4), "threshold": threshold,
                "assessment": similarity_label(distance, threshold), "disclaimer": "Embedding distance is probabilistic, not identity proof."}
    except Exception as exc:
        return {"available": False, "message": f"Candidate image could not be compared: {exc}"}
