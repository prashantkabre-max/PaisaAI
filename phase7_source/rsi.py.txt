"""
PaisaAI RSI Indicator
"""

from scanner.settings import RSI_PERIOD


def calculate_rsi(candles, period=RSI_PERIOD):
    """
    Calculate Relative Strength Index (RSI)

    Args:
        candles: List of candle dictionaries
        period: RSI period

    Returns:
        float or None
    """

    if not candles or len(candles) < period + 1:
        return None

    closes = [c["close"] for c in candles]

    gains = []
    losses = []

    for i in range(1, len(closes)):
        change = closes[i] - closes[i - 1]

        gains.append(max(change, 0))
        losses.append(max(-change, 0))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    for i in range(period, len(gains)):
        avg_gain = ((avg_gain * (period - 1)) + gains[i]) / period
        avg_loss = ((avg_loss * (period - 1)) + losses[i]) / period

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    return round(rsi, 2)
