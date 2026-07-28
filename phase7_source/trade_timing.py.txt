def evaluate_trade_timing(indicators, risk, direction="BUY"):
    """
    Evaluates whether this is the right time to enter a trade.
    Returns a timing score, rating and reasons.
    """

    score = 0
    reasons = []

    ema9 = indicators.get("ema9")
    ema20 = indicators.get("ema20")
    ltp = indicators.get("ltp")
    vwap = indicators.get("vwap")
    rsi = indicators.get("rsi")
    rvol = indicators.get("rvol")
    atr = indicators.get("atr")

    # EMA alignment
    if ema9 is not None and ema20 is not None:
        if direction == "BUY" and ema9 > ema20:
            score += 4
            reasons.append("BUY EMA aligned")
        elif direction == "SELL" and ema9 < ema20:
            score += 4
            reasons.append("SELL EMA aligned")

    # VWAP confirmation
    if ltp is not None and vwap is not None:
        if direction == "BUY" and ltp > vwap:
            score += 3
            reasons.append("Above VWAP")
        elif direction == "SELL" and ltp < vwap:
            score += 3
            reasons.append("Below VWAP")

    # RSI sweet spot
    if rsi is not None:
        if direction == "BUY" and 55 <= rsi <= 68:
            score += 3
            reasons.append("Healthy RSI")
        elif direction == "SELL" and 32 <= rsi <= 45:
            score += 3
            reasons.append("Bearish RSI")

    # Relative volume
    if rvol is not None and rvol >= 2.0:
        score += 4
        reasons.append("Strong Volume")

    # ATR available
    if atr is not None and atr > 0:
        score += 2
        reasons.append("ATR Confirmed")

    # Risk : Reward
    if risk is not None and risk.get("risk_reward", 0) >= 2:
        score += 4
        reasons.append("Good Risk:Reward")

    if score >= 18:
        timing = "EXCELLENT"
    elif score >= 14:
        timing = "GOOD"
    elif score >= 10:
        timing = "AVERAGE"
    else:
        timing = "POOR"

    return {
        "score": score,
        "timing": timing,
        "reasons": reasons,
    }
