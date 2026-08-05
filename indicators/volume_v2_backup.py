def calculate_volume_metrics(candles, lookback=10):
    """
    PaisaAI Production RVOL Engine

    Standard RVOL:
        current candle volume /
        average volume of previous completed candles

    The current candle is excluded from the baseline.
    Default baseline = previous 10 candles.
    """

    empty_result = {
        "current_volume": 0,
        "average_volume": None,
        "rvol": None,
        "volume_spike": "UNKNOWN",
        "volume_trend": "UNKNOWN",
        "volume_strength": 0,
    }

    if not candles:
        return empty_result

    current = candles[-1] or {}

    try:
        current_volume = float(
            current.get("volume", 0) or 0
        )
    except (TypeError, ValueError):
        current_volume = 0.0

    result = empty_result.copy()
    result["current_volume"] = current_volume

    # Need current candle + at least one completed candle.
    if len(candles) < 2:
        return result

    previous_candles = candles[:-1][-lookback:]

    previous_volumes = []

    for candle in previous_candles:
        if not candle:
            continue

        try:
            volume = float(
                candle.get("volume", 0) or 0
            )
        except (TypeError, ValueError):
            continue

        # Zero-volume bars must not distort the baseline.
        if volume > 0:
            previous_volumes.append(volume)

    if not previous_volumes:
        return result

    average_volume = (
        sum(previous_volumes) /
        len(previous_volumes)
    )

    result["average_volume"] = round(
        average_volume,
        2,
    )

    if average_volume <= 0:
        return result

    rvol = current_volume / average_volume

    result["rvol"] = round(rvol, 2)

    # ---------------------------------------------
    # RVOL classification
    # ---------------------------------------------

    if rvol >= 3.0:
        result["volume_spike"] = "EXTREME"
        result["volume_strength"] = 5

    elif rvol >= 2.0:
        result["volume_spike"] = "VERY_HIGH"
        result["volume_strength"] = 4

    elif rvol >= 1.5:
        result["volume_spike"] = "HIGH"
        result["volume_strength"] = 3

    elif rvol >= 1.0:
        result["volume_spike"] = "NORMAL"
        result["volume_strength"] = 2

    else:
        result["volume_spike"] = "LOW"
        result["volume_strength"] = 1

    # ---------------------------------------------
    # Historical volume trend
    # ---------------------------------------------

    if len(previous_volumes) >= 5:

        recent = previous_volumes[-5:]
        recent_average = sum(recent) / len(recent)

        older = previous_volumes[:-5]

        if older:

            older_average = (
                sum(older) /
                len(older)
            )

            if recent_average > older_average * 1.10:
                result["volume_trend"] = "RISING"

            elif recent_average < older_average * 0.90:
                result["volume_trend"] = "FALLING"

            else:
                result["volume_trend"] = "STABLE"

        else:
            result["volume_trend"] = "STABLE"

    else:
        result["volume_trend"] = "STABLE"

    return result
