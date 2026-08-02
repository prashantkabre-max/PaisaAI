def calculate_ema(candles, period=9, previous_ema=None):
    """
    EMA V2

    Backward compatible.

    If previous_ema is provided, only the latest candle is processed.
    Otherwise a normal EMA is calculated.
    """

    if len(candles) < period:
        return None

    closes = [
        candle["close"]
        for candle in candles
    ]

    multiplier = 2 / (period + 1)

    if previous_ema is not None:
        ema = (
            (closes[-1] - previous_ema)
            * multiplier
        ) + previous_ema

        return round(ema, 2)

    ema = sum(closes[:period]) / period

    for close in closes[period:]:
        ema = (
            (close - ema)
            * multiplier
        ) + ema

    return round(ema, 2)
