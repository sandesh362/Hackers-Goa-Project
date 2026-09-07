"""Single-face detection and deterministic crop hashing."""
from __future__ import annotations
import hashlib
from dataclasses import dataclass
from pathlib import Path
import numpy as np
from PIL import Image

@dataclass
class FaceData:
    encoding: np.ndarray
    face_hash: str
    crop: np.ndarray
    detection_method: str

def extract_face(image_path: str | Path) -> FaceData:
    """Find exactly one face and return its 128-dimensional dlib encoding and crop digest."""
    try:
        import face_recognition
    except BaseException as exc:
        # face_recognition calls quit() when its legacy pkg_resources dependency is absent.
        # Convert that SystemExit into a normal application error the dashboard can display.
        raise RuntimeError(
            "Face detection could not start. Install the supported dependency set with: "
            "python -m pip install -r requirements.txt"
        ) from exc
    image = face_recognition.load_image_file(str(image_path))
    locations = face_recognition.face_locations(image, number_of_times_to_upsample=1)
    if len(locations) == 0:
        # A close or strongly backlit portrait can defeat dlib's legacy HOG detector.
        # Keep the reverse-image-search workflow available, but never pretend this is a
        # confirmed face encoding: downstream similarity comparison is disabled.
        height, width = image.shape[:2]
        top, bottom = int(height * 0.04), int(height * 0.56)
        left, right = int(width * 0.20), int(width * 0.80)
        crop = image[top:bottom, left:right]
        return FaceData(np.array([], dtype=float), hashlib.sha256(crop.tobytes()).hexdigest(), crop, "image-region fallback (no confirmed face encoding)")
    if len(locations) != 1:
        raise ValueError(f"Expected exactly one face; found {len(locations)} in {image_path}.")
    top, right, bottom, left = locations[0]
    crop = image[top:bottom, left:right]
    encodings = face_recognition.face_encodings(image, known_face_locations=locations)
    if not encodings:
        raise ValueError("A face was located but could not be encoded.")
    return FaceData(np.asarray(encodings[0]), hashlib.sha256(crop.tobytes()).hexdigest(), crop, "dlib face encoding")

def save_encoding(face: FaceData, output_dir: str | Path) -> Path:
    output = Path(output_dir); output.mkdir(parents=True, exist_ok=True)
    path = output / "face_encoding.npy"; np.save(path, face.encoding)
    return path

def save_search_crop(face: FaceData, output_dir: str | Path) -> Path:
    """Write a compact face-focused image for reverse-image search, not the full outfit/photo."""
    output = Path(output_dir); output.mkdir(parents=True, exist_ok=True)
    image = Image.fromarray(face.crop)
    image.thumbnail((900, 900))
    path = output / "face_search_crop.jpg"
    image.save(path, format="JPEG", quality=82, optimize=True)
    if path.stat().st_size > 500 * 1024:
        image.thumbnail((640, 640)); image.save(path, format="JPEG", quality=72, optimize=True)
    return path
