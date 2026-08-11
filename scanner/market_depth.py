"""
PaisaAI Market Depth Engine V1

Observation-only engine.

Rules:
- Uses 5 bid levels and 5 ask levels.
- Caller provides one sampled snapshot per minute.
- Requires 10 consecutive qualifying snapshots.
- BUY dominance  : buyers >= 20% more than sellers.
- SELL dominance : sellers >= 20% more than buyers.
- Anything between those thresholds is BALANCED.
- A BALANCED/opposite observation resets the current streak.
- Does not modify production trades, confidence, grades,
  entries, exits, stop-losses, or targets.
"""

from collections import defaultdict
from datetime import datetime


SNAPSHOT_INTERVAL_SECONDS = 60
PERSISTENCE_REQUIRED = 10

# 20% imbalance threshold
BUY_RATIO_THRESHOLD = 1.20
SELL_RATIO_THRESHOLD = 1 / 1.20

_HISTORY = defaultdict(
    lambda: {
        "state": None,
        "persistence": 0,
    }
)


def _safe_number(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def calculate_depth(bids, asks):
    """
    Calculate total five-level bid/ask depth.

    bids and asks are expected to contain up to five levels.
    """

    total_buy = 0.0
    total_sell = 0.0

    for level in bids or []:
        if isinstance(level, dict):
            quantity = (
                level.get("quantity")
                or level.get("qty")
                or level.get("buy_quantity")
                or 0
            )
            total_buy += _safe_number(quantity)

    for level in asks or []:
        if isinstance(level, dict):
            quantity = (
                level.get("quantity")
                or level.get("qty")
                or level.get("sell_quantity")
                or 0
            )
            total_sell += _safe_number(quantity)

    if total_sell > 0:
        ratio = total_buy / total_sell
    elif total_buy > 0:
        ratio = float("inf")
    else:
        ratio = 1.0

    if ratio >= BUY_RATIO_THRESHOLD:
        state = "BUY"
    elif ratio <= SELL_RATIO_THRESHOLD:
        state = "SELL"
    else:
        state = "BALANCED"

    return {
        "buy_qty": int(total_buy),
        "sell_qty": int(total_sell),
        "ratio": ratio,
        "state": state,
    }


def update(symbol, bids, asks, timestamp=None):
    """
    Add one already-sampled depth observation.

    Persistence is CONSECUTIVE.

    Example:
        BUY 1/10
        BUY 2/10
        BUY 3/10
        SELL -> BUY streak resets
        BUY 1/10

    Confirmation occurs only after 10 consecutive BUY or SELL
    observations.
    """

    if timestamp is None:
        timestamp = datetime.now()

    depth = calculate_depth(bids, asks)
    state = depth["state"]

    tracker = _HISTORY[symbol]

    if state in ("BUY", "SELL"):
        if tracker["state"] == state:
            tracker["persistence"] += 1
        else:
            tracker["state"] = state
            tracker["persistence"] = 1
    else:
        # BALANCED breaks both directional streaks.
        tracker["state"] = None
        tracker["persistence"] = 0

    confirmed = None

    if (
        tracker["state"] in ("BUY", "SELL")
        and tracker["persistence"] >= PERSISTENCE_REQUIRED
    ):
        confirmed = tracker["state"]

    buy_persistence = (
        tracker["persistence"]
        if tracker["state"] == "BUY"
        else 0
    )

    sell_persistence = (
        tracker["persistence"]
        if tracker["state"] == "SELL"
        else 0
    )

    return {
        "timestamp": timestamp.isoformat(),
        "symbol": symbol,
        "buy_qty": depth["buy_qty"],
        "sell_qty": depth["sell_qty"],
        "ratio": depth["ratio"],
        "state": state,
        "persistence": tracker["persistence"],
        "buy_persistence": buy_persistence,
        "sell_persistence": sell_persistence,
        "confirmed": confirmed,
    }


def reset(symbol=None):
    """
    Reset one symbol or the entire observation history.
    """

    if symbol is None:
        _HISTORY.clear()
    else:
        _HISTORY.pop(symbol, None)


def get_status(symbol):
    """
    Return the current consecutive persistence state.
    """

    tracker = _HISTORY.get(symbol)

    if not tracker:
        return {
            "symbol": symbol,
            "persistence": 0,
            "buy_persistence": 0,
            "sell_persistence": 0,
            "confirmed": None,
        }

    confirmed = None

    if (
        tracker["state"] in ("BUY", "SELL")
        and tracker["persistence"] >= PERSISTENCE_REQUIRED
    ):
        confirmed = tracker["state"]

    return {
        "symbol": symbol,
        "persistence": tracker["persistence"],
        "buy_persistence": (
            tracker["persistence"]
            if tracker["state"] == "BUY"
            else 0
        ),
        "sell_persistence": (
            tracker["persistence"]
            if tracker["state"] == "SELL"
            else 0
        ),
        "confirmed": confirmed,
    }
