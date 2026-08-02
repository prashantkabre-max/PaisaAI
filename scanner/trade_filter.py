"""
PaisaAI Trade Filter
"""

from scanner.market_context import get_market_context


MIN_RISK_REWARD = 2.0


def filter_trade(indicators, trade):

    if trade is None:
        return False, "No trade"

    if trade.get("grade") == "IGNORE":
        return False, "Ignored"

    market = get_market_context()
    trade["market_context"] = market

    risk = trade.get("risk")

    if risk:
        if risk.get("risk_reward", 0) < MIN_RISK_REWARD:
            return False, "Poor Risk Reward"

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
