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


def calculate_score(indicators):

    score = 0
    passed = []
    failed = []

    rules = [
        ("ema", ema_rule),
        ("vwap", vwap_rule),
        ("supertrend", supertrend_rule),
        ("rvol", rvol_rule),
        ("adx", adx_rule),
        ("macd", macd_rule),
        ("rsi", rsi_rule),
        ("price_change", price_change_rule),
        ("open", open_rule),
        ("high_low", high_low_rule),
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
