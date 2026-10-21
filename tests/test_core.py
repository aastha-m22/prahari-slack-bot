import pytest
from bot.core import (ParseError, format_scenario, format_score, parse_window,
                      rule_based_summary, should_alert, state_from_risk, summarize_scenario)


def test_parse_window_aliases_and_types():
    w = parse_window("h2s=9.1 co=33 hotwork=1 workers=3")
    assert w == {"h2s_ppm": 9.1, "co_ppm": 33.0, "hotwork_active": 1, "workers_in_hazard_zone": 3}
    assert isinstance(w["hotwork_active"], int)


def test_parse_window_empty_is_allowed():
    assert parse_window("") == {}


@pytest.mark.parametrize("bad", ["h2s", "bogus=1", "h2s=abc"])
def test_parse_window_rejects_bad_input(bad):
    with pytest.raises(ParseError):
        parse_window(bad)


@pytest.mark.parametrize("risk,state", [(0, "normal"), (21.9, "normal"), (22, "elevated"),
                                        (45, "confirming"), (70, "critical"), (100, "critical")])
def test_state_bands(risk, state):
    assert state_from_risk(risk) == state


def test_should_alert_threshold():
    assert should_alert({"risk": 45}, 45)
    assert not should_alert({"risk": 44}, 45)


def test_format_score_includes_baseline_and_factors():
    out = format_score({"risk": 82, "state": "critical", "baseline_alarm": False,
                        "active_terms": ["hotwork"], "verdict": "evacuate"})
    assert "82/100" in out and "silent" in out and "hotwork" in out and "evacuate" in out


def test_rule_based_summary_calls_out_silent_baseline():
    text = rule_based_summary({"risk": 80, "state": "critical", "baseline_alarm": False})
    assert "threshold alarm would still be silent" in text


def test_scenario_summary():
    s = summarize_scenario({"tick_seconds": 30, "frames": [{"risk": r} for r in (5, 25, 50, 75)]})
    assert s["peak_risk"] == 75
    assert s["minutes_to"] == {"elevated": 0.5, "confirming": 1.0, "critical": 1.5}
    assert "Peak risk: 75" in format_scenario(s)


def test_scenario_summary_empty():
    assert summarize_scenario({"frames": []}) is None
    assert "No scenario" in format_scenario(None)
