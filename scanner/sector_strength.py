"""
PaisaAI Sector Strength
"""


def calculate_sector_strength(sector_change):
    """
    Evaluate sector performance.

    Args:
        sector_change (float): Sector % change

    Returns:
        {
            "sector_strength": float,
            "rating": "STRONG" | "NEUTRAL" | "WEAK"
        }
    """

    if sector_change is None:
        return None

    if sector_change >= 1.0:
        rating = "STRONG"
    elif sector_change <= -1.0:
        rating = "WEAK"
    else:
        rating = "NEUTRAL"

    return {
        "sector_strength": round(sector_change, 2),
        "rating": rating,
    }
