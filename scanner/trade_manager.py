"""
PaisaAI Trade Lifecycle Manager
"""

from datetime import datetime

_active_trades = {}


def register_trade(trade):
    """
    Register a new active trade.
    Returns True if registered, False if already active.
    """

    symbol = trade["symbol"]

    if symbol in _active_trades:
        return False

    risk = trade["risk"]

    _active_trades[symbol] = {
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
        "opened_at": datetime.now(),
    }

    return True


def update_trade(symbol, price):
    """
    Update an active trade using the latest market price.

    Dynamic stop-loss:
      Entry -> original stop loss
      Target 1 -> stop loss moves to entry
      Target 2 -> stop loss moves to Target 1
      Target 3 -> trade closes

    Accounting rule:
      Target 1/2 are milestones only; they do not realize P&L.
      The final exit price determines the one and only realized P&L.
      A protected stop therefore realizes the profit locked by that
      stop, while an entry stop realizes zero and the original stop
      realizes the actual loss.
    """

    if symbol not in _active_trades:
        return None

    trade = _active_trades[symbol]

    def duration():
        elapsed = datetime.now() - trade["opened_at"]
        minutes = int(elapsed.total_seconds() // 60)
        seconds = int(elapsed.total_seconds() % 60)
        return f"{minutes:02d}m {seconds:02d}s"

    def realized_pnl(exit_price):
        qty = trade["risk"]["recommended_qty"]
        if trade["action"] == "BUY":
            return round(qty * (exit_price - trade["entry"]), 2)
        return round(qty * (trade["entry"] - exit_price), 2)

    def milestone_event(name):
        return {
            "symbol": symbol,
            "display_symbol": trade["display_symbol"],
            "trade_number": trade["trade_number"],
            "event": name,
            "duration": duration(),
            "pnl": None,
            "realized_pnl": None,
            "exit_reason": None,
            "stop_loss": trade["stop_loss"],
        }

    def close_event(event_name, exit_reason):
        exit_price = trade["stop_loss"]
        pnl = realized_pnl(exit_price)

        if trade["target2_hit"]:
            accounting_type = "PROTECTED_STOP_T1"
        elif trade["target1_hit"]:
            accounting_type = "PROTECTED_STOP_ENTRY"
        else:
            accounting_type = "ORIGINAL_STOP"

        event = {
            "symbol": symbol,
            "display_symbol": trade["display_symbol"],
            "trade_number": trade["trade_number"],
            "event": event_name,
            "duration": duration(),
            "exit_reason": exit_reason,
            "exit_price": exit_price,
            "pnl": pnl,
            "realized_pnl": pnl,
            "accounting_type": accounting_type,
            "stop_loss": trade["stop_loss"],
        }

        del _active_trades[symbol]
        return event

    def target3_event():
        exit_price = trade["target3"]
        pnl = realized_pnl(exit_price)

        event = {
            "symbol": symbol,
            "display_symbol": trade["display_symbol"],
            "trade_number": trade["trade_number"],
            "event": "TARGET_3_HIT",
            "duration": duration(),
            "exit_reason": "TARGET 3",
            "exit_price": exit_price,
            "pnl": pnl,
            "realized_pnl": pnl,
            "accounting_type": "TARGET_3",
            "stop_loss": trade["stop_loss"],
        }

        del _active_trades[symbol]
        return event

    if trade["action"] == "BUY":

        # Target 1 is a milestone only. No P&L is realized here.
        if not trade["target1_hit"] and price >= trade["target1"]:
            trade["target1_hit"] = True
            trade["stop_loss"] = trade["entry"]
            return milestone_event("TARGET_1_HIT")

        # Target 2 is a milestone only. No P&L is realized here.
        if not trade["target2_hit"] and price >= trade["target2"]:
            trade["target2_hit"] = True
            trade["stop_loss"] = trade["target1"]
            return milestone_event("TARGET_2_HIT")

        # Target 3 is the final realized exit.
        if not trade["target3_hit"] and price >= trade["target3"]:
            trade["target3_hit"] = True
            return target3_event()

        # Current dynamic/original stop loss.
        if price <= trade["stop_loss"]:
            if trade["target1_hit"]:
                reason = (
                    "PROTECTED STOP → TARGET 1"
                    if trade["target2_hit"]
                    else "PROTECTED STOP → ENTRY"
                )
                return close_event("PROTECTED_STOP_HIT", reason)
            return close_event("STOP_LOSS_HIT", "ORIGINAL STOP LOSS")

    else:

        # Target 1 is a milestone only. No P&L is realized here.
        if not trade["target1_hit"] and price <= trade["target1"]:
            trade["target1_hit"] = True
            trade["stop_loss"] = trade["entry"]
            return milestone_event("TARGET_1_HIT")

        # Target 2 is a milestone only. No P&L is realized here.
        if not trade["target2_hit"] and price <= trade["target2"]:
            trade["target2_hit"] = True
            trade["stop_loss"] = trade["target1"]
            return milestone_event("TARGET_2_HIT")

        # Target 3 is the final realized exit.
        if not trade["target3_hit"] and price <= trade["target3"]:
            trade["target3_hit"] = True
            return target3_event()

        # Current dynamic/original stop loss.
        if price >= trade["stop_loss"]:
            if trade["target1_hit"]:
                reason = (
                    "PROTECTED STOP → TARGET 1"
                    if trade["target2_hit"]
                    else "PROTECTED STOP → ENTRY"
                )
                return close_event("PROTECTED_STOP_HIT", reason)
            return close_event("STOP_LOSS_HIT", "ORIGINAL STOP LOSS")

    return None


def get_active_trades():
    return _active_trades
