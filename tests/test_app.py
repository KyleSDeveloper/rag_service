import os, sys, subprocess, pathlib
# Set env BEFORE importing the app (so API_KEY is picked up)
os.environ.setdefault("API_KEY", "test-key")
os.environ.setdefault("RATE_LIMIT_PER_MIN", "60")

# Ensure index exists for startup
idx = pathlib.Path("rag_app/index.json")
if not idx.exists():
    subprocess.check_call([sys.executable, "-m", "rag_app.index",
                           "--corpus", "./corpus", "--out", "./rag_app/index.json"])

from fastapi.testclient import TestClient
from rag_app.main import app

client = TestClient(app)

def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json().get("ok") is True

def test_ask_authorized():
    r = client.post("/ask",
                    headers={"x-api-key": "test-key"},
                    json={"question": "What is coinsurance?", "k": 3})
    assert r.status_code == 200
    j = r.json()
    assert "answer" in j and isinstance(j["answer"], str) and j["answer"]

def test_metrics():
    m = client.get("/metrics").json()
    assert "requests" in m
