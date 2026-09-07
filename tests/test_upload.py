from pipeline import web_search

class UploadResponse:
    def raise_for_status(self): pass
    def json(self): return {"image_id": "temporary-image-id"}

def test_local_image_is_uploaded_for_lens(monkeypatch, tmp_path):
    image = tmp_path / "face.jpg"; image.write_bytes(b"jpeg-bytes")
    captured = {}
    def fake_post(url, data, files, timeout):
        captured.update(url=url, data=data, filename=files["image"][0])
        return UploadResponse()
    monkeypatch.setattr(web_search.requests, "post", fake_post)
    assert web_search.upload_image(image, "secret") == "temporary-image-id"
    assert captured == {"url": "https://serpapi.com/image", "data": {"api_key": "secret"}, "filename": "face.jpg"}
