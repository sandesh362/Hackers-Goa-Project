from fastapi.testclient import TestClient
import app as app_module

client = TestClient(app_module.app)

def test_settings_endpoint():
    response = client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()
    assert "SERPAPI_KEY" in data
    assert "SIMILARITY_THRESHOLD" in data
    assert "MAX_WEB_RESULTS" in data
    # check that values are strings
    assert isinstance(data["SIMILARITY_THRESHOLD"], str)
    assert isinstance(data["MAX_WEB_RESULTS"], str)

def test_settings_save(monkeypatch, tmp_path):
    # Isolate tests from the developer's real .env and credentials.
    test_env = tmp_path / ".env"
    monkeypatch.setattr(app_module, "ENV_FILE", test_env)
    for key in app_module.SETTINGS: monkeypatch.delenv(key, raising=False)
    values = {
        "SIMILARITY_THRESHOLD": "0.75",
        "MAX_WEB_RESULTS": "10",
        "SERPAPI_KEY": "test-key",
        "NETWORK": "amoy"
    }
    response = client.post("/api/settings", json=values)
    assert response.status_code == 200
    assert response.json()["ok"] is True
    # Verify saved
    response = client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()
    assert data["SIMILARITY_THRESHOLD"] == "0.75"
    assert data["MAX_WEB_RESULTS"] == "10"
    assert data["SERPAPI_KEY"].endswith("-key")
    assert data["NETWORK"] == "amoy"
    assert "test-key" in test_env.read_text()
