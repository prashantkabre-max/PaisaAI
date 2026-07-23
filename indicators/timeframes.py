from datetime import datetime


def aggregate_candles(candles):
    """
    Combine multiple 1-minute candles into one candle.
    """

    if not candles:
        return None

    return {
        "timestamp": candles[0]["timestamp"],
        "open": candles[0]["open"],
        "high": max(c["high"] for c in candles),
        "low": min(c["low"] for c in candles),
        "close": candles[-1]["close"],
        "volume": sum(c["volume"] for c in candles),
    }


def build_timeframe(history, size):
    """
    history = completed 1-minute candles
    size = 3,5,15,30
    """

    if len(history) < size:
        return None

    candles = history[-size:]

    return aggregate_candles(candles)
