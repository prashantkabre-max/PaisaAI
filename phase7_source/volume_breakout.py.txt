"""
PaisaAI Volume Breakout
"""


def calculate_volume_breakout(
    current_volume,
    average_volume,
    multiplier=2.0,
):
    """
    Detect volume breakout.

    Returns:
    {
        "volume_ratio": float,
        "breakout": bool
    }
    """

    if average_volume is None or average_volume <= 0:
        return None

    ratio = current_volume / average_volume

    return {
        "volume_ratio": round(ratio, 2),
        "breakout": ratio >= multiplier,
    }
