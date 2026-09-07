import numpy as np
from pipeline import web_search, face_match, blockchain

class Response:
    content = b"not-used"
    def raise_for_status(self): pass
    def json(self): return {"visual_matches": [{"link": "https://reddit.com/r/demo", "title": "A post", "relevance": .5}]}

def test_serpapi_call_is_mocked_at_http_boundary(monkeypatch):
    captured = {}
    def fake_get(url, params, timeout):
        captured.update(url=url, params=params, timeout=timeout)
        return Response()
    monkeypatch.setattr(web_search.requests, "get", fake_get)
    results = web_search.reverse_image_search("https://images.example/face.jpg", api_key="test-key")
    assert captured["url"] == "https://serpapi.com/search.json"
    assert captured["params"]["engine"] == "google_lens"
    assert results[0]["source_domain"] == "reddit.com"

def test_candidate_download_is_mocked_and_compared(monkeypatch):
    monkeypatch.setattr(face_match.requests, "get", lambda *args, **kwargs: Response())
    monkeypatch.setattr(face_match, "extract_face", lambda path: type("Face", (), {"encoding": np.array([0.1, 0.1])})())
    result = face_match.compare_candidate(np.array([0.1, 0.1]), "https://images.example/face.jpg")
    assert result["available"] is True
    assert result["distance"] == 0.0

def test_web3_contract_read_is_mocked(monkeypatch):
    class Call: 
        def call(self): return (bytes.fromhex("ab" * 32), "0x0", 0)
    class Functions:
        def getRecord(self, record_id): return Call()
    fake_contract = type("Contract", (), {"functions": Functions()})()
    monkeypatch.setattr(blockchain, "_contract", lambda: (None, fake_contract))
    assert blockchain.fetch_record_hash(0) == "ab" * 32
