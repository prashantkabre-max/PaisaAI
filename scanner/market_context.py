"""
PaisaAI Market Intelligence
"""

from scanner.runtime import MARKET_STATE


def get_market_context():

    nifty = MARKET_STATE.get("NIFTY")

    if nifty is None:
        return {
            "trend": "UNKNOWN",
            "strength": 0,
            "confidence": 0,
        }

    ema9 = nifty.get("ema9")
    ema20 = nifty.get("ema20")
    adx = nifty.get("adx")

    trend = "SIDEWAYS"

    if (
        ema9 is not None
        and ema20 is not None
    ):
        if ema9 > ema20:
            trend = "BULLISH"
        elif ema9 < ema20:
            trend = "BEARISH"

    strength = 0

    if adx is not None:
        if adx >= 30:
            strength = 100
        elif adx >= 25:
            strength = 75
        elif adx >= 20:
            strength = 50
        else:
            strength = 25

    return {
        "trend": trend,
        "strength": strength,
        "confidence": strength,
    }
