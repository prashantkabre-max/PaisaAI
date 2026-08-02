"""
PaisaAI Trade Filter

Final quality gate before a trade is accepted.
"""

def filter_trade(indicators, trade):
    """
    Returns:
        (True, None)   -> Trade accepted
        (False, reason)-> Trade rejected
    """

    if trade is None:
        return False, "No trade"

    if trade.get("grade") == "IGNORE":
        return False, "Ignored"

    return True, None
