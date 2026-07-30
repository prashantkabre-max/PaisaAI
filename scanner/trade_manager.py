"""
PaisaAI Trade Lifecycle Manager
Stable Scanner V2
"""

from datetime import datetime

_active_trades = {}


def register_trade(trade):
    """
    Register a new trade.
    Only one active trade per symbol.
    """

    symbol = trade["symbol"]

    if symbol in _active_trades:
        return False

    risk = trade["risk"]

    _active_trades[symbol] = {
        "action": trade["action"],
        "entry": risk["entry"],
        "stop_loss": risk["stop_loss"],
        "target1": risk["target1"],
        "target2": risk["target2"],
        "target3": risk["target3"],
        "target1_hit": False,
        "target2_hit": False,
        "target3_hit": False,
        "opened_at": datetime.now(),
    }

    return True


def update_trade(symbol, price):
    """
    Update an active trade.

    Trade remains ACTIVE until:
      • Target 3 is achieved, OR
      • Stop Loss is hit
    """

    if symbol not in _active_trades:
        return None

    trade = _active_trades[symbol]

    if trade["action"] == "BUY":

        if (not trade["target1_hit"]) and price >= trade["target1"]:
            trade["target1_hit"] = True
            return {"symbol": symbol, "event": "TARGET_1_HIT"}

        if trade["target1_hit"] and (not trade["target2_hit"]) and price >= trade["target2"]:
            trade["target2_hit"] = True
            return {"symbol": symbol, "event": "TARGET_2_HIT"}

        if trade["target2_hit"] and (not trade["target3_hit"]) and price >= trade["target3"]:
            trade["target3_hit"] = True
            del _active_trades[symbol]
            return {"symbol": symbol, "event": "TARGET_3_HIT"}

        if price <= trade["stop_loss"]:
            del _active_trades[symbol]
            return {"symbol": symbol, "event": "STOP_LOSS_HIT"}

    else:  # SELL

        if (not trade["target1_hit"]) and price <= trade["target1"]:
            trade["target1_hit"] = True
            return {"symbol": symbol, "event": "TARGET_1_HIT"}

        if trade["target1_hit"] and (not trade["target2_hit"]) and price <= trade["target2"]:
            trade["target2_hit"] = True
            return {"symbol": symbol, "event": "TARGET_2_HIT"}

        if trade["target2_hit"] and (not trade["target3_hit"]) and price <= trade["target3"]:
            trade["target3_hit"] = True
            del _active_trades[symbol]
            return {"symbol": symbol, "event": "TARGET_3_HIT"}

        if price >= trade["stop_loss"]:
            del _active_trades[symbol]
            return {"symbol": symbol, "event": "STOP_LOSS_HIT"}

    return None


def get_active_trades():
    return _active_trades
