"""
PaisaAI MACD Indicator
"""

from scanner.settings import (
    MACD_FAST,
    MACD_SLOW,
    MACD_SIGNAL,
)


def _ema(values, period):
    """Calculate EMA for a list of values."""

    if len(values) < period:
        return None

    multiplier = 2 / (period + 1)

    ema = sum(values[:period]) / period

    for price in values[period:]:
        ema = (price - ema) * multiplier + ema

    return ema


def calculate_macd(
    candles,
    fast=MACD_FAST,
    slow=MACD_SLOW,
    signal=MACD_SIGNAL,
):
    """
    Calculate MACD.

    Returns:
        {
            "macd": float,
            "signal": float,
            "histogram": float
        }
        or None
    """

    if not candles:
        return None

    closes = [c["close"] for c in candles]

    if len(closes) < slow + signal:
        return None

    macd_line = []

    for i in range(slow, len(closes) + 1):
        subset = closes[:i]

        fast_ema = _ema(subset, fast)
        slow_ema = _ema(subset, slow)

        if fast_ema is None or slow_ema is None:
            continue

        macd_line.append(fast_ema - slow_ema)

    if len(macd_line) < signal:
        return None

    signal_line = _ema(macd_line, signal)

    if signal_line is None:
        return None

    macd = macd_line[-1]
    histogram = macd - signal_line

    return {
        "macd": round(macd, 4),
        "signal": round(signal_line, 4),
        "histogram": round(histogram, 4),
    }
