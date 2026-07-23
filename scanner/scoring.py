def calculate_score(indicators):
    """
    Basic scoring engine.
    This will become our A+, A, A- engine.
    """

    if indicators is None:
        return None

    score = 0

    # EMA Trend
    if indicators.get("ema9") is not None and indicators.get("ema20") is not None:
        if indicators["ema9"] > indicators["ema20"]:
            score += 20
        elif indicators["ema9"] < indicators["ema20"]:
            score -= 20

    # Price change
    if indicators["change_percent"] > 2:
        score += 40
    elif indicators["change_percent"] > 1:
        score += 20

    # Above Open
    if indicators.get("open") is not None:
        if indicators["ltp"] > indicators["open"]:
            score += 20

    # Near High
    if indicators.get("high") is not None:
        if indicators["ltp"] >= indicators["high"]:
            score += 20

    # Near Low
    if indicators.get("low") is not None:
        if indicators["ltp"] <= indicators["low"]:
            score -= 20

    if score >= 80:
        grade = "A+"
    elif score >= 60:
        grade = "A"
    elif score >= 40:
        grade = "A-"
    else:
        grade = "IGNORE"

    return {
        "score": score,
        "grade": grade
    }
