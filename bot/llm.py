"""Plain-language summaries via Groq, with a deterministic fallback.

The fallback is intentional: for a safety signal the bot must always answer,
even when the model is down, unconfigured, or returns something unusable.
"""
import json
import requests

from bot import config
from bot.core import rule_based_summary

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
SYSTEM_PROMPT = (
    "You summarize industrial safety risk assessments for plant operators. "
    "Use only the numbers and fields given. Do not invent readings, causes, or actions. "
    "Answer in at most 3 short sentences."
)


def summarize(assessment: dict, api_key: str = None, post=requests.post) -> str:
    key = api_key if api_key is not None else config.GROQ_API_KEY
    if not key:
        return rule_based_summary(assessment)
    payload = {
        "model": config.GROQ_MODEL,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(assessment)},
        ],
    }
    try:
        resp = post(GROQ_URL, headers={"Authorization": f"Bearer {key}"},
                    json=payload, timeout=config.HTTP_TIMEOUT)
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"].strip()
        return text or rule_based_summary(assessment)
    except Exception:
        return rule_based_summary(assessment)
