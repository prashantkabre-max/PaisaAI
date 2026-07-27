"""
PaisaAI Alert Engine with Trade Lifecycle
"""

from datetime import datetime

# Active trades currently being managed
_active_trades = {}


def should_alert(trade):
    """
    Allow only one active BUY/SELL trade per stock.
    """

    if trade is None:
        return False

    if trade["action"] == "IGNORE":
        return False

    symbol = trade["symbol"]

    # Already managing this stock
    if symbol in _active_trades:
        return False

    _active_trades[symbol] = {
        "status": "ACTIVE",
        "entry": trade["risk"]["entry"],
        "stop_loss": trade["risk"]["stop_loss"],
        "target1": trade["risk"]["target1"],
        "target2": trade["risk"]["target2"],
        "target3": trade["risk"]["target3"],
        "target1_hit": False,
        "target2_hit": False,
        "target3_hit": False,
        "opened_at": datetime.now(),
    }

    return True


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
    if not should_alert(trade):
        return None

    return build_alert(trade)


def get_active_trades():
    """
    Returns currently active trades.
    """
    return _active_trades

