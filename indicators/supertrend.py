"""
PaisaAI Supertrend Indicator
"""

from scanner.settings import ATR_PERIOD
from indicators.atr import calculate_atr


def calculate_supertrend(
    candles,
    period=ATR_PERIOD,
    multiplier=3,
):
    """
    Calculate Supertrend.

    Returns:
    {
        "supertrend": float,
        "trend": "UP" | "DOWN"
    }
    """

    if not candles or len(candles) < period + 1:
        return None

    atr = calculate_atr(candles, period)

    if atr is None:
        return None

    upper_final = None
    lower_final = None
    trend = "UP"

    for i in range(period, len(candles)):
        high = candles[i]["high"]
        low = candles[i]["low"]
        close = candles[i]["close"]
        prev_close = candles[i - 1]["close"]

        hl2 = (high + low) / 2

        basic_upper = hl2 + (multiplier * atr)
        basic_lower = hl2 - (multiplier * atr)

        if upper_final is None:
            upper_final = basic_upper
            lower_final = basic_lower
        else:
            if basic_upper < upper_final or prev_close > upper_final:
                upper_final = basic_upper

            if basic_lower > lower_final or prev_close < lower_final:
                lower_final = basic_lower

        if trend == "DOWN":
            if close > upper_final:
                trend = "UP"
        else:
            if close < lower_final:
                trend = "DOWN"

    value = lower_final if trend == "UP" else upper_final

    return {
        "supertrend": round(value, 2),
        "trend": trend,
    }
