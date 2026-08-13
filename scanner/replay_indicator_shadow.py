"""Replay-only shadow scoring for the newly added technical indicators.

This module deliberately does not change the existing production/replay score.
It lets Replay compare the current baseline against the proposed upgrade.
"""


def _buy(indicators):
    checks = {
        "stochastic": indicators.get("stochastic_k") is not None
        and indicators.get("stochastic_d") is not None
        and indicators.get("stochastic_k") > indicators.get("stochastic_d"),
        "support_resistance": indicators.get("support_resistance_position")
        in {"BREAKOUT", "UPPER_RANGE"},
        "bollinger": indicators.get("bb_position") == "ABOVE_UPPER"
        or (
            indicators.get("bb_percent_b") is not None
            and indicators.get("bb_percent_b") >= 0.50
        ),
        "ichimoku": indicators.get("ichimoku_price_position") == "ABOVE_CLOUD"
        and indicators.get("ichimoku_tk_direction") == "BULLISH",
    }
    return checks


def _sell(indicators):
    checks = {
        "stochastic": indicators.get("stochastic_k") is not None
        and indicators.get("stochastic_d") is not None
        and indicators.get("stochastic_k") < indicators.get("stochastic_d"),
        "support_resistance": indicators.get("support_resistance_position")
        in {"BREAKDOWN", "LOWER_RANGE"},
        "bollinger": indicators.get("bb_position") == "BELOW_LOWER"
        or (
            indicators.get("bb_percent_b") is not None
            and indicators.get("bb_percent_b") <= 0.50
        ),
        "ichimoku": indicators.get("ichimoku_price_position") == "BELOW_CLOUD"
        and indicators.get("ichimoku_tk_direction") == "BEARISH",
    }
    return checks


def calculate_shadow_score(indicators, direction="BUY"):
    checks = _buy(indicators) if direction.upper() == "BUY" else _sell(indicators)
    passed = [name for name, ok in checks.items() if ok]
    failed = [name for name, ok in checks.items() if not ok]

    return {
        "score": len(passed),
        "max_score": len(checks),
        "confidence": round(len(passed) / len(checks) * 100, 1),
        "passed": passed,
        "failed": failed,
    }
