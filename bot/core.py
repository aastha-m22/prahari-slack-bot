"""Pure functions: parse input, shape PRAHARI output into readable Slack text.

Kept free of Slack and network code so every function is unit-testable.
"""
from typing import Optional

# Short names users can type in a command -> field names the /score endpoint expects.
ALIASES = {
    "h2s": "h2s_ppm",
    "co": "co_ppm",
    "pressure": "cog_pressure_bar",
    "slope": "h2s_slope",
    "hotwork": "hotwork_active",
    "confined": "confined_entry_active",
    "handoff": "shift_handoff_gap",
    "workers": "workers_in_hazard_zone",
    "maintenance": "maintenance_active",
    "gastest": "mins_since_gas_test",
}
VALID_FIELDS = set(ALIASES.values())
INT_FIELDS = {"hotwork_active", "confined_entry_active", "shift_handoff_gap",
              "workers_in_hazard_zone", "maintenance_active"}

STATE_ORDER = ["normal", "elevated", "confirming", "critical"]


class ParseError(ValueError):
    pass


def parse_window(text: str) -> dict:
    """'h2s=9.1 co=33 hotwork=1' -> {'h2s_ppm': 9.1, 'co_ppm': 33.0, 'hotwork_active': 1}"""
    window = {}
    for token in (text or "").split():
        if "=" not in token:
            raise ParseError(f"'{token}' is not key=value")
        key, _, raw = token.partition("=")
        key = ALIASES.get(key.lower(), key.lower())
        if key not in VALID_FIELDS:
            raise ParseError(f"unknown field '{key}'")
        try:
            value = float(raw)
        except ValueError:
            raise ParseError(f"value for '{key}' must be a number, got '{raw}'")
        window[key] = int(value) if key in INT_FIELDS else value
    return window


def state_from_risk(risk: float) -> str:
    """Same bands the PRAHARI dashboard uses."""
    if risk >= 70:
        return "critical"
    if risk >= 45:
        return "confirming"
    if risk >= 22:
        return "elevated"
    return "normal"


def should_alert(assessment: dict, threshold: int) -> bool:
    return float(assessment.get("risk", 0)) >= threshold


def format_score(assessment: dict) -> str:
    risk = assessment.get("risk", "n/a")
    state = assessment.get("state") or state_from_risk(float(assessment.get("risk", 0)))
    lines = [f"*Risk index:* {risk}/100  |  *State:* {state}"]
    if "baseline_alarm" in assessment:
        baseline = "FIRING" if assessment["baseline_alarm"] else "silent"
        lines.append(f"*Single-sensor alarm:* {baseline}")
    factors = assessment.get("active_terms") or assessment.get("factors") or []
    if factors:
        names = [f if isinstance(f, str) else f.get("name", str(f)) for f in factors]
        lines.append("*Active risk factors:* " + ", ".join(names))
    if assessment.get("verdict"):
        lines.append(f"*Verdict:* {assessment['verdict']}")
    return "\n".join(lines)


def format_metrics(metrics: dict, healthy: bool) -> str:
    """Render whatever held-out numbers the backend exposes, without assuming exact keys."""
    head = "PRAHARI backend: " + ("healthy" if healthy else "UNREACHABLE")
    if not metrics:
        return head + "\nNo evaluation metrics available."
    lines = [head, "*Held-out evaluation:*"]
    for key, value in metrics.items():
        if isinstance(value, dict):
            inner = ", ".join(f"{k}: {v}" for k, v in value.items())
            lines.append(f"- {key}: {inner}")
        else:
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def summarize_scenario(scenario: dict) -> Optional[dict]:
    """Peak risk and the first frames that cross the elevated/confirming/critical bands."""
    frames = scenario.get("frames") or []
    if not frames:
        return None
    tick = scenario.get("tick_seconds", 30)
    risks = [f.get("risk", 0) for f in frames]
    peak = max(risks)
    first = {}
    for band, cutoff in (("elevated", 22), ("confirming", 45), ("critical", 70)):
        idx = next((i for i, r in enumerate(risks) if r >= cutoff), None)
        first[band] = None if idx is None else round(idx * tick / 60, 1)
    return {"peak_risk": peak, "frames": len(frames), "minutes_to": first}


def format_scenario(summary: Optional[dict]) -> str:
    if not summary:
        return "No scenario data returned."
    mt = summary["minutes_to"]
    def fmt(v):
        return "never" if v is None else f"{v} min"
    return (f"*Scenario replay* ({summary['frames']} frames)\n"
            f"Peak risk: {summary['peak_risk']}/100\n"
            f"First elevated: {fmt(mt['elevated'])}  |  confirming: {fmt(mt['confirming'])}  |  critical: {fmt(mt['critical'])}")


def rule_based_summary(assessment: dict) -> str:
    """Deterministic plain-language fallback used whenever the LLM is unavailable or untrusted."""
    risk = float(assessment.get("risk", 0))
    state = assessment.get("state") or state_from_risk(risk)
    baseline = assessment.get("baseline_alarm")
    text = f"Compound risk is {risk:.0f}/100 ({state})."
    if baseline is False and risk >= 45:
        text += " No single sensor has crossed its own alarm limit, so a threshold alarm would still be silent."
    if state in ("confirming", "critical"):
        text += " Recommend confirming conditions on site and preparing the response sequence."
    elif state == "elevated":
        text += " Keep watching the trend."
    else:
        text += " No action needed."
    return text
