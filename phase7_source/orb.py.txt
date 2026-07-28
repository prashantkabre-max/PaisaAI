"""
PaisaAI Opening Range Breakout (ORB)
"""


def calculate_orb(candles, opening_minutes=15):
    """
    Calculates the Opening Range Breakout.

    Returns:
    {
        "orb_high": float,
        "orb_low": float,
        "breakout": "UP" | "DOWN" | None
    }
    """

    if not candles:
        return None

    opening = candles[:opening_minutes]

    if len(opening) < opening_minutes:
        return None

    orb_high = max(c["high"] for c in opening)
    orb_low = min(c["low"] for c in opening)

    current_close = candles[-1]["close"]

    breakout = None

    if current_close > orb_high:
        breakout = "UP"

    elif current_close < orb_low:
        breakout = "DOWN"

    return {
        "orb_high": round(orb_high, 2),
        "orb_low": round(orb_low, 2),
        "breakout": breakout,
    }
