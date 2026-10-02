from fastapi.testclient import TestClient
from src.api import app

client = TestClient(app)

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_query():
    r = client.post("/query", json={"question": "நட்பு பற்றி குறள் என்ன கூறுகிறது"})
    assert r.status_code == 200
    assert len(r.json()["results"]) > 0