from scanner.rules import (
    ema_rule,
    vwap_rule,
    macd_rule,
    adx_rule,
    supertrend_rule,
    rvol_rule,
    rsi_rule,
    price_change_rule,
    open_rule,
    high_low_rule,
)

WEIGHTS = {
    "ema": 20,
    "vwap": 15,
    "supertrend": 15,
    "rvol": 15,
    "adx": 10,
    "macd": 10,
    "rsi": 5,
    "price_change": 5,
    "open": 3,
    "high_low": 2,
}


def calculate_score(indicators, direction="BUY"):
    """
    Calculates PaisaAI confidence score.

    direction:
        BUY  -> Bullish scoring
        SELL -> Bearish scoring

    The current rules are direction-agnostic. Future rule updates
    will use the direction parameter for separate BUY/SELL logic.
    """

    score = 0
    passed = []
    failed = []

    rules = [
        ("ema", lambda indicators: ema_rule(indicators, direction)),
        ("vwap", lambda indicators: vwap_rule(indicators, direction)),
        ("supertrend", lambda indicators: supertrend_rule(indicators, direction)),
        ("rvol", rvol_rule),
        ("adx", adx_rule),
        ("macd", lambda indicators: macd_rule(indicators, direction)),
        ("rsi", lambda indicators: rsi_rule(indicators, direction)),
        ("price_change", lambda indicators: price_change_rule(indicators, direction)),
        ("open", lambda indicators: open_rule(indicators, direction)),
        ("high_low", lambda indicators: high_low_rule(indicators, direction)),
    ]

    for name, rule in rules:
        if rule(indicators):
            score += WEIGHTS[name]
            passed.append(name)
        else:
            failed.append(name)

    if score >= 90:
        grade = "A+"
    elif score >= 75:
        grade = "A"
    elif score >= 60:
        grade = "A-"
    else:
        grade = "IGNORE"

    return {
        "grade": grade,
        "confidence": score,
        "passed": passed,
        "failed": failed,
    }
