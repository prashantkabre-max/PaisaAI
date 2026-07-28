"""
PaisaAI Relative Strength vs Nifty
"""


def calculate_relative_strength(stock_change, nifty_change):
    """
    Compare stock performance against Nifty.

    Returns:
    {
        "relative_strength": float,
        "strength": "STRONG" | "WEAK" | "NEUTRAL"
    }
    """

    if stock_change is None or nifty_change is None:
        return None

    rs = stock_change - nifty_change

    if rs > 0.5:
        strength = "STRONG"
    elif rs < -0.5:
        strength = "WEAK"
    else:
        strength = "NEUTRAL"

    return {
        "relative_strength": round(rs, 2),
        "strength": strength,
    }
