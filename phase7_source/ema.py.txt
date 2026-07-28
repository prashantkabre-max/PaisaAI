def calculate_ema(candles, period=9):
    """
    Calculate Exponential Moving Average.

    candles : list of completed candles
    period  : EMA period

    Returns:
        float or None
    """

    if len(candles) < period:
        return None

    closes = [c["close"] for c in candles]

    multiplier = 2 / (period + 1)

    ema = sum(closes[:period]) / period

    for close in closes[period:]:
        ema = (close - ema) * multiplier + ema

    return round(ema, 2)
