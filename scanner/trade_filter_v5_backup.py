"""
PaisaAI Trade Filter
"""

from scanner.market_context import get_market_context


def filter_trade(indicators, trade):

    if trade is None:
        return False, "No trade"

    if trade.get("grade") == "IGNORE":
        return False, "Ignored"

    market = get_market_context()

    trade["market_context"] = market

    if (
        market["trend"] == "BULLISH"
        and trade["action"] == "SELL"
        and trade.get("confidence", 0) < 95
    ):
        return False, "Against Bullish Market"

    if (
        market["trend"] == "BEARISH"
        and trade["action"] == "BUY"
        and trade.get("confidence", 0) < 95
    ):
        return False, "Against Bearish Market"

    return True, None
