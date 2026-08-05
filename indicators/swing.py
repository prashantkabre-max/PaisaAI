def calculate_swing_levels(candles, lookback=10):
    """
    Professional Intraday Swing Levels

    Uses the previous completed candles only.
    Excludes the live candle to avoid repainting.
    """

    result = {
        "swing_high": None,
        "swing_low": None,
    }

    if not candles or len(candles) < lookback + 2:
        return result

    completed = candles[:-1]
    recent = completed[-lookback:]

    result["swing_high"] = max(c["high"] for c in recent)
    result["swing_low"] = min(c["low"] for c in recent)

    return result
