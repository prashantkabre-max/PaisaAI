"""
PaisaAI Trade Filter

Final quality gate before a trade is accepted.
"""

from scanner.runtime import MARKET_STATE


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

    nifty = MARKET_STATE.get("NIFTY")

    if nifty:
        trade["market_bias"] = {
            "ema9": nifty.get("ema9"),
            "ema20": nifty.get("ema20"),
            "vwap": nifty.get("vwap"),
            "adx": nifty.get("adx"),
        }
    else:
        trade["market_bias"] = None

    return True, None
