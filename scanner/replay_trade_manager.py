"""
PaisaAI Replay Trade Lifecycle Manager

Replay mirror of the production dynamic stop-loss lifecycle.

Dynamic SL:
    ORIGINAL SL -> TARGET 1 -> ENTRY -> TARGET 2 -> TARGET 1 -> TARGET 3

The replay manager is isolated from the live trade manager, but the
state transitions and P&L rules intentionally mirror production.
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


def reset(strategy=None, symbol=None):
    """Reset replay lifecycle state."""
    if strategy is None and symbol is None:
        for book in _active_trades.values():
            book.clear()
        return

    strategies = [strategy.upper()] if strategy else STRATEGIES

    for name in strategies:
        book = _active_trades[name]
        if symbol is None:
            book.clear()
        else:
            book.pop(symbol, None)


def register_trade(strategy, trade, opened_at=None):
    """Register one active replay trade for a strategy."""
    strategy = strategy.upper()
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
        "original_stop_loss": risk["stop_loss"],
        "target1": risk["target1"],
        "target2": risk["target2"],
        "target3": risk["target3"],
        "risk": risk,
        "target1_hit": False,
        "target2_hit": False,
        "target3_hit": False,
        "opened_at": opened_at or datetime.now(),
    }

    return True


def _duration(opened_at, timestamp=None):
    if timestamp is None:
        current = datetime.now()
    elif isinstance(timestamp, datetime):
        current = timestamp
    else:
        text = str(timestamp).replace("Z", "+00:00")
        try:
            current = datetime.fromisoformat(text)
        except ValueError:
            current = datetime.now()

    try:
        delta = current - opened_at
    except TypeError:
        # Handle naive/aware mismatch without affecting lifecycle logic.
        delta = datetime.now() - opened_at

    seconds = max(0, int(delta.total_seconds()))
    return f"{seconds // 60:02d}m {seconds % 60:02d}s"


def update_trade(strategy, symbol, price, timestamp=None):
    """Apply the production dynamic-SL state machine to replay prices."""
    strategy = strategy.upper()

    if symbol not in _active_trades[strategy]:
        return None

    trade = _active_trades[strategy][symbol]

    def event(name):
        risk = trade["risk"]
        qty = risk["recommended_qty"]

        if name == "TARGET_1_HIT":
            pnl = qty * abs(trade["target1"] - trade["entry"])
        elif name == "TARGET_2_HIT":
            pnl = qty * abs(trade["target2"] - trade["entry"])
        elif name == "TARGET_3_HIT":
            pnl = qty * abs(trade["target3"] - trade["entry"])
        else:
            # IMPORTANT: use the CURRENT dynamic SL, not the original SL.
            # Therefore a stop after T1 protects entry, and a stop after T2
            # protects at least the T1 profit.
            pnl = -(qty * abs(trade["entry"] - trade["stop_loss"]))

        return {
            "symbol": symbol,
            "display_symbol": trade["display_symbol"],
            "trade_number": trade["trade_number"],
            "event": name,
            "duration": _duration(trade["opened_at"], timestamp),
            "exit_reason": "TARGET 3" if name == "TARGET_3_HIT" else "STOP LOSS",
            "pnl": round(pnl, 2),
            "stop_loss": trade["stop_loss"],
            "target1_hit": trade["target1_hit"],
            "target2_hit": trade["target2_hit"],
        }

    if trade["action"] == "BUY":
        if not trade["target1_hit"] and price >= trade["target1"]:
            trade["target1_hit"] = True
            trade["stop_loss"] = trade["entry"]
            return event("TARGET_1_HIT")

        if not trade["target2_hit"] and price >= trade["target2"]:
            trade["target2_hit"] = True
            trade["stop_loss"] = trade["target1"]
            return event("TARGET_2_HIT")

        if not trade["target3_hit"] and price >= trade["target3"]:
            trade["target3_hit"] = True
            result = event("TARGET_3_HIT")
            del _active_trades[strategy][symbol]
            return result

        if price <= trade["stop_loss"]:
            result = event("STOP_LOSS_HIT")
            del _active_trades[strategy][symbol]
            return result

    else:
        if not trade["target1_hit"] and price <= trade["target1"]:
            trade["target1_hit"] = True
            trade["stop_loss"] = trade["entry"]
            return event("TARGET_1_HIT")

        if not trade["target2_hit"] and price <= trade["target2"]:
            trade["target2_hit"] = True
            trade["stop_loss"] = trade["target1"]
            return event("TARGET_2_HIT")

        if not trade["target3_hit"] and price <= trade["target3"]:
            trade["target3_hit"] = True
            result = event("TARGET_3_HIT")
            del _active_trades[strategy][symbol]
            return result

        if price >= trade["stop_loss"]:
            result = event("STOP_LOSS_HIT")
            del _active_trades[strategy][symbol]
            return result

    return None


def get_active_trades(strategy=None):
    if strategy is None:
        return _active_trades
    return _active_trades.get(strategy.upper(), {})


def get_strategies():
    return STRATEGIES
