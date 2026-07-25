import json
import uuid
from pathlib import Path
from datetime import datetime

LEARNING_FILE = Path("data/learning_history.json")


def _load_history():
    if not LEARNING_FILE.exists():
        return []

    try:
        with open(LEARNING_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []


def _save_history(history):
    LEARNING_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(LEARNING_FILE, "w") as f:
        json.dump(history, f, indent=4)


def create_trade(
    symbol,
    action,
    grade,
    confidence,
    risk,
    market_sentiment,
    stock_sentiment,
    trade_timing,
    entry_price=None,
    stop_loss=None,
    target1=None,
    target2=None,
):

    return {
        "trade_id": str(uuid.uuid4()),
        "symbol": symbol,
        "action": action,
        "grade": grade,
        "confidence": confidence,
        "risk": risk,
        "market_sentiment": market_sentiment,
        "stock_sentiment": stock_sentiment,
        "trade_timing": trade_timing,
        "entry_price": entry_price,
        "stop_loss": stop_loss,
        "target1": target1,
        "target2": target2,
        "entry_time": datetime.now().isoformat(),
        "exit_time": None,
        "exit_price": None,
        "exit_reason": None,
        "result": "OPEN",
        "profit_loss": 0.0,
        "mfe": 0.0,
        "mae": 0.0,
        "notes": "",
        "logged_at": datetime.now().isoformat(),
    }


def log_trade(trade):
    history = _load_history()
    history.append(trade)
    _save_history(history)


def update_trade(
    trade_id,
    result,
    exit_price,
    exit_reason,
    profit_loss,
    mfe=0.0,
    mae=0.0,
    notes="",
):

    history = _load_history()

    for trade in history:

        if trade["trade_id"] == trade_id:

            trade["result"] = result
            trade["exit_price"] = exit_price
            trade["exit_reason"] = exit_reason
            trade["profit_loss"] = profit_loss
            trade["mfe"] = mfe
            trade["mae"] = mae
            trade["notes"] = notes
            trade["exit_time"] = datetime.now().isoformat()

            break

    _save_history(history)


def get_history():
    return _load_history()


def get_statistics():

    history = _load_history()

    total = len(history)

    wins = sum(
        1
        for t in history
        if t["result"] in ["TARGET1", "TARGET2"]
    )

    losses = sum(
        1
        for t in history
        if t["result"] == "STOPLOSS"
    )

    open_trades = sum(
        1
        for t in history
        if t["result"] == "OPEN"
    )

    pnl = round(
        sum(t.get("profit_loss", 0) for t in history),
        2,
    )

    win_rate = round(
        (wins / total) * 100,
        2,
    ) if total else 0

    return {
        "total_trades": total,
        "wins": wins,
        "losses": losses,
        "open_trades": open_trades,
        "win_rate": win_rate,
        "net_profit_loss": pnl,
    }
