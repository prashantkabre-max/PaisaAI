"""
PaisaAI ADX Indicator
"""

from scanner.settings import ATR_PERIOD


def _wilder_smoothing(values, period):
    """Apply Wilder's smoothing."""

    if len(values) < period:
        return []

    smoothed = [sum(values[:period])]

    for value in values[period:]:
        prev = smoothed[-1]
        smoothed.append(prev - (prev / period) + value)

    return smoothed


def calculate_adx(candles, period=ATR_PERIOD):
    """
    Calculate Average Directional Index (ADX).

    Returns:
    {
        "adx": float,
        "plus_di": float,
        "minus_di": float,
        "trend": "bullish" | "bearish" | "neutral"
    }
    or None
    """

    if not candles or len(candles) < (period * 2):
        return None

    plus_dm = []
    minus_dm = []
    true_range = []

    for i in range(1, len(candles)):
        current = candles[i]
        previous = candles[i - 1]

        up_move = current["high"] - previous["high"]
        down_move = previous["low"] - current["low"]

        plus_dm.append(
            up_move if up_move > down_move and up_move > 0 else 0.0
        )

        minus_dm.append(
            down_move if down_move > up_move and down_move > 0 else 0.0
        )

        tr = max(
            current["high"] - current["low"],
            abs(current["high"] - previous["close"]),
            abs(current["low"] - previous["close"]),
        )

        true_range.append(tr)

    smoothed_tr = _wilder_smoothing(true_range, period)
    smoothed_plus = _wilder_smoothing(plus_dm, period)
    smoothed_minus = _wilder_smoothing(minus_dm, period)

    if not smoothed_tr:
        return None

    dx_values = []

    for tr, plus, minus in zip(
        smoothed_tr,
        smoothed_plus,
        smoothed_minus,
    ):
        if tr == 0:
            continue

        plus_di = (plus / tr) * 100
        minus_di = (minus / tr) * 100

        total = plus_di + minus_di

        if total == 0:
            dx = 0
        else:
            dx = abs(plus_di - minus_di) / total * 100

        dx_values.append(dx)

    if len(dx_values) < period:
        return None

    adx = sum(dx_values[-period:]) / period

    plus_di = (smoothed_plus[-1] / smoothed_tr[-1]) * 100
    minus_di = (smoothed_minus[-1] / smoothed_tr[-1]) * 100

    if plus_di > minus_di:
        trend = "bullish"
    elif minus_di > plus_di:
        trend = "bearish"
    else:
        trend = "neutral"

    return {
        "adx": round(adx, 2),
        "plus_di": round(plus_di, 2),
        "minus_di": round(minus_di, 2),
        "trend": trend,
    }
