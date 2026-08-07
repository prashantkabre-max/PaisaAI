"""
PaisaAI Trade Lifecycle Manager
"""

from datetime import datetime


STRATEGIES = [
    "ATR",
    "SESSION",
    "SWING",
    "ORB",
    "SMART",
]

_active_trades = {
    strategy: {}
    for strategy in STRATEGIES
}



def register_trade(strategy, trade):
    """
    Register a new active trade.
    Returns True if registered, False if already active.
    """

    symbol = trade["symbol"]

    if symbol in _active_trades[strategy]:
        return False

    risk = trade["risk"]

    _active_trades[strategy][symbol] = {
        "action": trade["action"],
        "display_symbol": trade.get("display_symbol", symbol),
        "trade_number": trade["trade_number"],
        "entry": risk["entry"],
        "stop_loss": risk["stop_loss"],
        "target1": risk["target1"],
        "target2": risk["target2"],
        "target3": risk["target3"],
        "risk": risk,
        "target1_hit": False,
        "target2_hit": False,
        "target3_hit": False,
        "opened_at": datetime.now(),
    }

    return True


def update_trade(strategy, symbol, price):
    """
    Update an active trade using the latest market price.
    Returns an event dictionary when something important happens.
    """

    if symbol not in _active_trades[strategy]:
        return None

    trade = _active_trades[strategy][symbol]

    def event(name):
        duration = datetime.now() - trade["opened_at"]
        minutes = int(duration.total_seconds() // 60)
        seconds = int(duration.total_seconds() % 60)

        risk = trade["risk"]

        qty = risk["recommended_qty"]

        if name == "TARGET_1_HIT":
            pnl = qty * abs(trade["target1"] - trade["entry"])
        elif name == "TARGET_2_HIT":
            pnl = qty * abs(trade["target2"] - trade["entry"])
        elif name == "TARGET_3_HIT":
            pnl = qty * abs(trade["target3"] - trade["entry"])
        else:
            pnl = -(qty * abs(trade["entry"] - trade["stop_loss"]))

        return {
            "symbol": symbol,
            "display_symbol": trade["display_symbol"],
            "trade_number": trade["trade_number"],
            "event": name,
            "duration": f"{minutes:02d}m {seconds:02d}s",
            "exit_reason": "TARGET 3" if name == "TARGET_3_HIT" else "STOP LOSS",
            "pnl": round(pnl, 2),
        }

    if trade["action"] == "BUY":

        if not trade["target1_hit"] and price >= trade["target1"]:
            trade["target1_hit"] = True
            return event("TARGET_1_HIT")

        if not trade["target2_hit"] and price >= trade["target2"]:
            trade["target2_hit"] = True
            return event("TARGET_2_HIT")

        if not trade["target3_hit"] and price >= trade["target3"]:
            trade["target3_hit"] = True
            del _active_trades[strategy][symbol]
            return event("TARGET_3_HIT")

        if price <= trade["stop_loss"]:
            del _active_trades[strategy][symbol]
            return event("STOP_LOSS_HIT")

    else:

        if not trade["target1_hit"] and price <= trade["target1"]:
            trade["target1_hit"] = True
            return event("TARGET_1_HIT")

        if not trade["target2_hit"] and price <= trade["target2"]:
            trade["target2_hit"] = True
            return event("TARGET_2_HIT")

        if not trade["target3_hit"] and price <= trade["target3"]:
            trade["target3_hit"] = True
            del _active_trades[strategy][symbol]
            return event("TARGET_3_HIT")

        if price >= trade["stop_loss"]:
            del _active_trades[strategy][symbol]
            return event("STOP_LOSS_HIT")

    return None


def get_active_trades(strategy=None):
    if strategy is None:
        return _active_trades
    return _active_trades.get(strategy, {})


def get_strategies():
    return STRATEGIES
