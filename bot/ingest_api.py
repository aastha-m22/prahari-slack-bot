"""Webhook-style ingest: POST a sensor reading, get it scored, alert Slack when risk is high.

    POST /ingest   header X-Ingest-Secret: <INGEST_SECRET>
    body: {"h2s_ppm": 9.1, "co_ppm": 33, ...}
"""
import hmac

from fastapi import FastAPI, Header, HTTPException

from bot import config
from bot.core import format_score, should_alert
from bot.llm import summarize
from bot.prahari_client import PrahariClient, PrahariError

app = FastAPI(title="PRAHARI Slack ingest")
client = PrahariClient()

_slack = None


def post_to_slack(text: str) -> bool:
    """Send an alert to Slack. Returns False (instead of crashing) if Slack is not configured."""
    global _slack
    if not config.SLACK_BOT_TOKEN:
        return False
    if _slack is None:
        from slack_sdk import WebClient
        _slack = WebClient(token=config.SLACK_BOT_TOKEN)
    _slack.chat_postMessage(channel=config.ALERT_CHANNEL, text=text)
    return True


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ingest")
def ingest(window: dict, x_ingest_secret: str = Header(default="")):
    if not hmac.compare_digest(x_ingest_secret, config.INGEST_SECRET):
        raise HTTPException(status_code=401, detail="bad secret")
    try:
        assessment = client.score(window)
    except PrahariError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    alerted = False
    if should_alert(assessment, config.ALERT_RISK_THRESHOLD):
        message = "*PRAHARI alert*\n" + format_score(assessment) + "\n\n" + summarize(assessment)
        alerted = post_to_slack(message)
    return {"risk": assessment.get("risk"), "state": assessment.get("state"), "alerted": alerted}
