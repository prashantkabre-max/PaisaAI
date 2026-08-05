def calculate_volume_metrics(candles, lookback=20):
    """
    PaisaAI Industry Standard RVOL Engine

    RVOL =
        Current (live) candle volume /
        Average volume of previous completed candles

    Baseline:
        Previous 20 completed candles

    This matches the approach used by most professional
    intraday scanners.
    """

    empty = {
        "current_volume": 0.0,
        "average_volume": None,
        "rvol": None,
        "volume_spike": "UNKNOWN",
        "volume_trend": "UNKNOWN",
        "volume_strength": 0,
    }

    if not candles or len(candles) < (lookback + 1):
        return empty

    # Industry standard:
    # Use previous completed candle volume for RVOL.
    current_volume = 0.0

    # Use the most recent completed candle that has non-zero volume.
    for candle in reversed(candles[:-1]):
        try:
            v = float(candle.get("volume", 0) or 0)
        except Exception:
            continue

        if v > 0:
            current_volume = v
            break

    previous = []

    for candle in candles[-(lookback + 1):-1]:
        try:
            volume = float(candle.get("volume", 0) or 0)
        except Exception:
            continue

        if volume > 0:
            previous.append(volume)

    if not previous:
        return empty

    average_volume = sum(previous) / len(previous)

    if average_volume <= 0:
        return empty

    rvol = current_volume / average_volume

    result = {
        "current_volume": round(current_volume, 2),
        "average_volume": round(average_volume, 2),
        "rvol": round(rvol, 2),
        "volume_spike": "LOW",
        "volume_trend": "STABLE",
        "volume_strength": 1,
    }

    if rvol >= 3.0:
        result["volume_spike"] = "EXTREME"
        result["volume_strength"] = 5
    elif rvol >= 2.0:
        result["volume_spike"] = "VERY_HIGH"
        result["volume_strength"] = 4
    elif rvol >= 1.5:
        result["volume_spike"] = "HIGH"
        result["volume_strength"] = 3
    elif rvol >= 1.2:
        result["volume_spike"] = "ABOVE_AVERAGE"
        result["volume_strength"] = 2
    else:
        result["volume_spike"] = "LOW"
        result["volume_strength"] = 1

    if len(previous) >= 10:
        recent = previous[-5:]
        older = previous[:-5]

        if older:
            recent_avg = sum(recent) / len(recent)
            older_avg = sum(older) / len(older)

            if recent_avg > older_avg * 1.10:
                result["volume_trend"] = "RISING"
            elif recent_avg < older_avg * 0.90:
                result["volume_trend"] = "FALLING"

    return result
