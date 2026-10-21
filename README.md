# PRAHARI Slack Bot

A Slack bot and webhook that put [PRAHARI](https://github.com/aastha-m22/PRAHARI)'s compound-risk
scores where operators already work. It turns raw sensor readings into a plain-language answer
in a Slack channel, and alerts the channel when risk crosses a threshold.

## What it does

| Feature | How |
| --- | --- |
| `/prahari status` | Backend health plus the held-out evaluation numbers from `/metrics` |
| `/prahari score h2s=9.1 co=33 hotwork=1 ...` | Scores a reading through `/score` and explains it in plain language |
| `/prahari scenario` | Replays the built-in scenario and reports when risk crossed each band |
| `POST /ingest` (webhook) | Receives a sensor reading, scores it, posts a Slack alert if risk >= threshold |
| `@mention` | Same commands via an app mention |

## Design decisions

- **Rule-based fallback.** The LLM (Groq, Llama 3.3 70B) only writes the plain-language summary,
  and is told to use only the numbers it is given. If there is no API key or the call fails, a
  deterministic summary is used, so the bot always answers.
- **Pure core.** Parsing and formatting live in `bot/core.py` with no Slack or network code,
  which is why they are fully unit-tested.
- **Webhook is authenticated** with a shared secret (constant-time comparison).
- **Failures are explicit.** If the PRAHARI backend is down the bot says so instead of crashing.

## Run it

```bash
pip install -r requirements.txt
cp .env.example .env        # fill in tokens

# 1. start PRAHARI (from the PRAHARI repo)         python -m backend.main
#    ...or the bundled mock if you only want to try the bot:
#    uvicorn tests.mock_prahari:app --port 8000

# 2. Slack bot (Socket Mode)
python -m bot.slack_app

# 3. Alert webhook
uvicorn bot.ingest_api:app --port 9000
curl -X POST localhost:9000/ingest -H "X-Ingest-Secret: change-me" \
  -H "Content-Type: application/json" \
  -d '{"h2s_ppm": 9.1, "hotwork_active": 1, "confined_entry_active": 1, "mins_since_gas_test": 24}'
```

### Slack app setup

1. Create an app at api.slack.com/apps and enable **Socket Mode** (this gives `SLACK_APP_TOKEN`).
2. Add the bot scopes `commands`, `chat:write`, `app_mentions:read`; install it (gives `SLACK_BOT_TOKEN`).
3. Create a slash command `/prahari` and subscribe to the `app_mention` event.
4. Invite the bot to `ALERT_CHANNEL`.

## Tests

```bash
python -m pytest -q
```

The end-to-end tests run against `tests/mock_prahari.py`, a stand-in that follows the documented
PRAHARI API contract. Its risk formula is a toy; run the real backend for real scores.

## Limits and next steps

- The `/score` response fields (`risk`, `state`, `active_terms`, `verdict`, `baseline_alarm`) were
  checked against PRAHARI's `backend/fusion.py`; missing fields are skipped rather than crashing.
- No persistence or alert de-duplication yet: a sustained high reading alerts on every ingest.
- Next: alert cooldown, a Grafana dashboard fed from the same endpoints.
