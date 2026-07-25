from scanner.risk import calculate_risk


GRADE_RULES = [
    (90, "A+"),
    (80, "A"),
    (70, "A-"),
    (60, "B"),
    (0, "IGNORE"),
]


def get_grade(confidence):
    for score, grade in GRADE_RULES:
        if confidence >= score:
            return grade
    return "IGNORE"


def evaluate_trade(
    symbol,
    technical_score,
    market_sentiment,
    stock_sentiment,
    trade_timing,
    reasons,
):
    confidence = technical_score

    confidence += market_sentiment.get("score", 0)
    confidence += stock_sentiment.get("score", 0)
    confidence += trade_timing.get("score", 0)

    confidence = max(0, min(confidence, 100))

    risk = calculate_risk(
        confidence,
        market_sentiment,
        stock_sentiment,
        trade_timing,
    )

    grade = get_grade(confidence)

    if grade == "IGNORE":
        action = "IGNORE"
    elif market_sentiment["status"] == "BEARISH":
        action = "IGNORE"
    elif risk in ["HIGH", "VERY HIGH"]:
        action = "IGNORE"
    else:
        action = "BUY"

    return {
        "symbol": symbol,
        "action": action,
        "grade": grade,
        "confidence": confidence,
        "risk": risk,
        "market_sentiment": market_sentiment,
        "stock_sentiment": stock_sentiment,
        "trade_timing": trade_timing,
        "reasons": reasons,
    }
