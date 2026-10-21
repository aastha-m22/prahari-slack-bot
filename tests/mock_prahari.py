"""Tiny stand-in for the PRAHARI API so the bot can be demoed and tested without it.

Mirrors the documented contract: GET /health, GET /metrics, POST /score, GET /scenario.
The risk formula here is a toy, NOT the real model. Run the real backend for real scores.
"""
from fastapi import FastAPI

app = FastAPI()


@app.get("/health")
def health():
    return {"status": "ok", "service": "prahari-mock", "model_loaded": True}


@app.get("/metrics")
def metrics():
    return {"missed_incident_rate": {"baseline": 0.615, "prahari": 0.0},
            "mean_lead_time_min": {"baseline": 0.4, "prahari": 14.0}}


@app.post("/score")
def score(w: dict):
    risk = 0
    risk += 25 if w.get("h2s_ppm", 0) > 5 else 0
    risk += 25 if w.get("hotwork_active") else 0
    risk += 25 if w.get("confined_entry_active") else 0
    risk += 15 if w.get("mins_since_gas_test", 0) > 20 else 0
    risk = min(100, risk)
    state = "critical" if risk >= 70 else "confirming" if risk >= 45 else "elevated" if risk >= 22 else "normal"
    return {"risk": risk, "state": state,
            "baseline_alarm": w.get("h2s_ppm", 0) >= 10,
            "active_terms": [n for k, n in (("hotwork_active", "hotwork"), ("confined_entry_active", "confined")) if w.get(k)],
            "p_incident": risk / 100, "verdict": "mock verdict"}


@app.get("/scenario")
def scenario():
    return {"tick_seconds": 30, "frames": [{"frame": {}, "risk": r} for r in (5, 10, 18, 25, 40, 55, 72, 90, 95)]}
