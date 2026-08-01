"""
PaisaAI ATR Indicator
"""

from scanner.settings import ATR_PERIOD


def calculate_atr(candles, period=ATR_PERIOD):
    """
    Calculate Average True Range (ATR).

    Returns:
        float or None
    """

    if not candles or len(candles) < period + 1:
        return None

    true_ranges = []

    for i in range(1, len(candles)):
        high = candles[i]["high"]
        low = candles[i]["low"]
        prev_close = candles[i - 1]["close"]

        tr = max(
            high - low,
            abs(high - prev_close),
            abs(low - prev_close),
        )

        true_ranges.append(tr)

    atr = sum(true_ranges[:period]) / period

    for tr in true_ranges[period:]:
        atr = ((atr * (period - 1)) + tr) / period

    return round(atr, 4)
