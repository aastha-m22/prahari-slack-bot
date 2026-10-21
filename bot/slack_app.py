"""Slack bot (Socket Mode): /prahari status | score k=v ... | scenario | help"""
import logging

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from bot import config
from bot.core import (ParseError, format_metrics, format_scenario, format_score,
                      parse_window, summarize_scenario)
from bot.llm import summarize
from bot.prahari_client import PrahariClient, PrahariError

logging.basicConfig(level=logging.INFO)
HELP = ("*PRAHARI bot commands*\n"
        "`/prahari status` - backend health and held-out evaluation numbers\n"
        "`/prahari score h2s=9.1 co=33 pressure=1.12 slope=0.5 hotwork=1 confined=1 "
        "handoff=1 workers=3 maintenance=1 gastest=24` - score a reading\n"
        "`/prahari scenario` - replay the built-in scenario and show when risk crossed each band\n"
        "Fields you leave out use the backend defaults.")


def handle_command(text: str, client: PrahariClient, summarizer=summarize) -> str:
    """Pure command router so it can be tested without Slack."""
    parts = (text or "").strip().split(maxsplit=1)
    cmd = parts[0].lower() if parts else "help"
    rest = parts[1] if len(parts) > 1 else ""
    try:
        if cmd == "status":
            try:
                healthy = client.health().get("status") == "ok"
            except PrahariError:
                healthy = False
            metrics = client.metrics() if healthy else {}
            return format_metrics(metrics, healthy)
        if cmd == "score":
            assessment = client.score(parse_window(rest))
            return format_score(assessment) + "\n\n" + summarizer(assessment)
        if cmd == "scenario":
            return format_scenario(summarize_scenario(client.scenario()))
        return HELP
    except ParseError as exc:
        return f"Could not read that reading: {exc}\n\n{HELP}"
    except PrahariError as exc:
        return f"PRAHARI backend error: {exc}"


def build_app() -> App:
    app = App(token=config.SLACK_BOT_TOKEN)
    client = PrahariClient()

    @app.command("/prahari")
    def prahari(ack, command, respond):
        ack()
        respond(handle_command(command.get("text", ""), client))

    @app.event("app_mention")
    def mention(event, say):
        text = event.get("text", "")
        say(handle_command(text.split(">", 1)[-1].strip(), client))

    return app


if __name__ == "__main__":
    SocketModeHandler(build_app(), config.SLACK_APP_TOKEN).start()
