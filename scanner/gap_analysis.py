"""
PaisaAI Gap Analysis
"""


def calculate_gap(previous_close, today_open):
    """
    Calculate opening gap.

    Returns:
    {
        "gap_percent": float,
        "gap_type": "GAP_UP" | "GAP_DOWN" | "FLAT"
    }
    """

    if previous_close is None or today_open is None:
        return None

    gap = ((today_open - previous_close) / previous_close) * 100

    if gap >= 0.5:
        gap_type = "GAP_UP"
    elif gap <= -0.5:
        gap_type = "GAP_DOWN"
    else:
        gap_type = "FLAT"

    return {
        "gap_percent": round(gap, 2),
        "gap_type": gap_type,
    }
