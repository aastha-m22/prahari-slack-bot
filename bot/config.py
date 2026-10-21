"""All settings live here and are read from environment variables."""
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:  # python-dotenv is optional at import time
    pass

PRAHARI_URL = os.getenv("PRAHARI_URL", "http://127.0.0.1:8000").rstrip("/")
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN", "")
ALERT_CHANNEL = os.getenv("ALERT_CHANNEL", "#prahari-alerts")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
ALERT_RISK_THRESHOLD = int(os.getenv("ALERT_RISK_THRESHOLD", "45"))
INGEST_SECRET = os.getenv("INGEST_SECRET", "change-me")
HTTP_TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "8"))
