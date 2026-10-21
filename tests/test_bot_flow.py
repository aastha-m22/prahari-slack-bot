"""End-to-end tests against the mock PRAHARI API (no Slack, no Groq key needed)."""
import threading
import time

import pytest
import uvicorn
from fastapi.testclient import TestClient

from bot import config
from bot.ingest_api import app as ingest_app
from bot.llm import summarize
from bot.prahari_client import PrahariClient, PrahariError
from bot.slack_app import HELP, handle_command
from tests.mock_prahari import app as mock_app

PORT = 8765


@pytest.fixture(scope="module")
def client():
    server = uvicorn.Server(uvicorn.Config(mock_app, host="127.0.0.1", port=PORT, log_level="error"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    for _ in range(50):
        if server.started:
            break
        time.sleep(0.1)
    yield PrahariClient(f"http://127.0.0.1:{PORT}")
    server.should_exit = True


def test_status(client):
    out = handle_command("status", client)
    assert "healthy" in out and "missed_incident_rate" in out


def test_score_command_uses_fallback_summary_without_key(client, monkeypatch):
    monkeypatch.setattr(config, "GROQ_API_KEY", "")
    out = handle_command("score h2s=9.1 hotwork=1 confined=1 gastest=24", client)
    assert "Risk index" in out and "no single sensor" in out.lower()


def test_scenario_command(client):
    out = handle_command("scenario", client)
    assert "Peak risk: 95" in out


def test_bad_input_returns_help_not_crash(client):
    out = handle_command("score nonsense=1", client)
    assert "Could not read" in out and "prahari status" in out


def test_help(client):
    assert handle_command("", client) == HELP


def test_backend_down_is_reported():
    dead = PrahariClient("http://127.0.0.1:9", timeout=1)
    assert "UNREACHABLE" in handle_command("status", dead)
    assert "backend error" in handle_command("scenario", dead)


def test_llm_failure_falls_back():
    def boom(*a, **k):
        raise RuntimeError("model down")
    text = summarize({"risk": 90, "state": "critical", "baseline_alarm": False}, api_key="k", post=boom)
    assert "90/100" in text


def test_ingest_requires_secret(client, monkeypatch):
    monkeypatch.setattr("bot.ingest_api.client", client)
    c = TestClient(ingest_app)
    assert c.post("/ingest", json={"h2s_ppm": 9}).status_code == 401


def test_ingest_alerts_above_threshold(client, monkeypatch):
    sent = []
    monkeypatch.setattr("bot.ingest_api.client", client)
    monkeypatch.setattr("bot.ingest_api.post_to_slack", lambda t: sent.append(t) or True)
    monkeypatch.setattr(config, "GROQ_API_KEY", "")
    c = TestClient(ingest_app)
    hdr = {"X-Ingest-Secret": config.INGEST_SECRET}
    r = c.post("/ingest", json={"h2s_ppm": 9.1, "hotwork_active": 1, "confined_entry_active": 1}, headers=hdr)
    assert r.status_code == 200 and r.json()["alerted"] is True and sent
    quiet = c.post("/ingest", json={"h2s_ppm": 1}, headers=hdr)
    assert quiet.json()["alerted"] is False and len(sent) == 1
