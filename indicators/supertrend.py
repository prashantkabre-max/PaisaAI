"""
PaisaAI TradingView-style Supertrend Indicator
"""

from scanner.settings import ATR_PERIOD
from indicators.atr import calculate_atr


def calculate_supertrend(
    candles,
    period=ATR_PERIOD,
    multiplier=3,
):
    """
    TradingView-style Supertrend

    Returns:
    {
        "supertrend": float,
        "trend": "UP" | "DOWN"
    }
    """

    if len(candles) < period + 2:
        return None

    upper_band = []
    lower_band = []
    trend = []

    final_upper = None
    final_lower = None

    for i in range(period, len(candles)):

        atr = calculate_atr(candles[: i + 1], period)

        if atr is None:
            continue

        high = candles[i]["high"]
        low = candles[i]["low"]
        close = candles[i]["close"]

        hl2 = (high + low) / 2

        basic_upper = hl2 + multiplier * atr
        basic_lower = hl2 - multiplier * atr

        if final_upper is None:
            final_upper = basic_upper
            final_lower = basic_lower
            current_trend = "UP"

        else:

            previous_close = candles[i - 1]["close"]

            if (
                basic_upper < final_upper
                or previous_close > final_upper
            ):
                final_upper = basic_upper

            if (
                basic_lower > final_lower
                or previous_close < final_lower
            ):
                final_lower = basic_lower

            if trend[-1] == "DOWN":

                if close > final_upper:
                    current_trend = "UP"
                else:
                    current_trend = "DOWN"

            else:

                if close < final_lower:
                    current_trend = "DOWN"
                else:
                    current_trend = "UP"

        upper_band.append(final_upper)
        lower_band.append(final_lower)
        trend.append(current_trend)

    if not trend:
        return None

    value = (
        lower_band[-1]
        if trend[-1] == "UP"
        else upper_band[-1]
    )

    return {
        "supertrend": round(value, 2),
        "trend": trend[-1],
    }
