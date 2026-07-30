"""
PaisaAI Alert Engine
"""

from datetime import datetime


def build_alert(trade):
    return {
        "type": "NEW_TRADE",
        "symbol": trade["symbol"],
        "action": trade["action"],
        "grade": trade["grade"],
        "confidence": trade["confidence"],
        "risk": trade["risk"],
        "market_sentiment": trade["market_sentiment"],
        "stock_sentiment": trade["stock_sentiment"],
        "trade_timing": trade["trade_timing"],
        "passed": trade["passed"],
        "failed": trade["failed"],
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def process_alert(trade):
    if trade is None:
        return None

    if trade["grade"] == "IGNORE":
        return None

    return build_alert(trade)
