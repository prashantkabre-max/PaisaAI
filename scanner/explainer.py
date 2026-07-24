def explain(indicators):
    """
    Explain why a stock received its score.
    """

    reasons = []

    if indicators.get("ema9") is not None and indicators.get("ema20") is not None:
        if indicators["ema9"] > indicators["ema20"]:
            reasons.append("EMA9 > EMA20 (Bullish)")
        else:
            reasons.append("EMA9 < EMA20 (Bearish)")

    if indicators.get("vwap") is not None:
        if indicators["ltp"] > indicators["vwap"]:
            reasons.append("Price Above VWAP")
        else:
            reasons.append("Price Below VWAP")

    if indicators.get("rvol") is not None:
        reasons.append(f"RVOL = {indicators['rvol']:.2f}")

    if indicators.get("open") is not None:
        if indicators["ltp"] > indicators["open"]:
            reasons.append("Above Open")
        else:
            reasons.append("Below Open")

    if indicators.get("high") is not None:
        if indicators["ltp"] >= indicators["high"]:
            reasons.append("Near Day High")

    if indicators.get("low") is not None:
        if indicators["ltp"] <= indicators["low"]:
            reasons.append("Near Day Low")

    return reasons
