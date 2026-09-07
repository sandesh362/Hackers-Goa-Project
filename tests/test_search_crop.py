import numpy as np
from pipeline.face_id import FaceData, save_search_crop
from PIL import Image

def test_search_crop_is_a_compact_jpeg(tmp_path):
    face = FaceData(np.array([]), "a" * 64, np.zeros((1200, 900, 3), dtype=np.uint8), "test")
    path = save_search_crop(face, tmp_path)
    assert path.suffix == ".jpg" and path.stat().st_size <= 500 * 1024
    assert Image.open(path).size[0] <= 900
