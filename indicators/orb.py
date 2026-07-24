"""
Opening Range Breakout (ORB)
PaisaAI

Version 1:
- 5-minute Opening Range
- Detect breakout above OR High
- Detect breakdown below OR Low
"""

from datetime import datetime


# Stores ORB data for each symbol
_orb_data = {}


def calculate_orb(symbol, candles):
    """
    candles : List of completed 1-minute candles

    Candle format:
    {
        "time": datetime,
        "open": ...,
        "high": ...,
        "low": ...,
        "close": ...,
        "volume": ...
    }
    """

    if not candles:
        return {
            "orb_high": None,
            "orb_low": None,
            "orb_breakout": False,
            "orb_breakdown": False,
        }

    if symbol not in _orb_data:
        _orb_data[symbol] = {
            "orb_high": None,
            "orb_low": None,
            "locked": False,
        }

    state = _orb_data[symbol]

    # Build Opening Range from first 5 completed candles
    if not state["locked"] and len(candles) >= 5:

        first_five = candles[:5]

        state["orb_high"] = max(c["high"] for c in first_five)
        state["orb_low"] = min(c["low"] for c in first_five)
        state["locked"] = True

    latest = candles[-1]

    breakout = False
    breakdown = False

    if state["locked"]:

        if latest["close"] > state["orb_high"]:
            breakout = True

        if latest["close"] < state["orb_low"]:
            breakdown = True

    return {
        "orb_high": state["orb_high"],
        "orb_low": state["orb_low"],
        "orb_breakout": breakout,
        "orb_breakdown": breakdown,
    }


def reset_orb(symbol=None):
    """
    Reset ORB at start of a new trading day.
    """

    global _orb_data

    if symbol is None:
        _orb_data = {}
    else:
        _orb_data.pop(symbol, None)
