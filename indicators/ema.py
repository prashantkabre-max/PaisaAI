def calculate_ema(candles, period=9):
    """
    Calculate the latest Exponential Moving Average.

    Returns:
        float | None
    """

    result = calculate_ema_values(candles, period)

    if result is None:
        return None

    return result["current"]


def calculate_ema_values(candles, period=9):
    """
    Calculate both the current EMA and the previous candle EMA.

    Returns:
        {
            "current": float,
            "previous": float,
        }

        or None
    """

    if len(candles) < period + 1:
        return None

    closes = [c["close"] for c in candles]

    multiplier = 2 / (period + 1)

    ema = sum(closes[:period]) / period
    previous_ema = None

    for close in closes[period:]:
        previous_ema = ema
        ema = (close - ema) * multiplier + ema

    return {
        "current": round(ema, 2),
        "previous": round(previous_ema, 2),
    }
