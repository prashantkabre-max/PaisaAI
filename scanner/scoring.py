from scanner.settings import *

from scanner.rules import (
    ema_rule,
    vwap_rule,
    rvol_rule,
    price_change_rule,
    open_rule,
    high_low_rule,
    rsi_rule,
    macd_rule,
    adx_rule,
    supertrend_rule,
)


def calculate_score(indicators):
    """
    PaisaAI Modular Scoring Engine
    """

    if indicators is None:
        return None

    score = (
        ema_rule(indicators)
        + vwap_rule(indicators)
        + rvol_rule(indicators)
        + price_change_rule(indicators)
        + open_rule(indicators)
        + high_low_rule(indicators)
        + rsi_rule(indicators)
        + macd_rule(indicators)
        + adx_rule(indicators)
        + supertrend_rule(indicators)
    )

    if score >= A_PLUS_SCORE:
        grade = "A+"
    elif score >= A_SCORE:
        grade = "A"
    elif score >= A_MINUS_SCORE:
        grade = "A-"
    else:
        grade = "IGNORE"

    return {
        "score": score,
        "grade": grade,
    }
