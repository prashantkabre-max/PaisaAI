"""
PaisaAI Market Depth Engine V1

Observation-only engine.

Rules:
- Five bid levels + five ask levels.
- One qualifying live sample per minute.
- BUY dominance: buyers >= 20% more than sellers.
- SELL dominance: sellers >= 20% more than buyers.
- Requires 10 consecutive qualifying observations.
- BALANCED/opposite observation resets the directional streak.
- Never changes production trades, confidence, grades,
  entries, exits, stop-losses or targets.
"""

from collections import defaultdict
from datetime import datetime


SNAPSHOT_INTERVAL_SECONDS = 60
PERSISTENCE_REQUIRED = 10

BUY_RATIO_THRESHOLD = 1.20
SELL_RATIO_THRESHOLD = 1 / 1.20

_HISTORY = defaultdict(
    lambda: {
        "state": None,
        "persistence": 0,
    }
)

_LAST_SAMPLE = {}


def _safe_number(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def calculate_depth(bids, asks):

    total_buy = 0.0
    total_sell = 0.0

    for level in (bids or [])[:5]:

        if isinstance(level, dict):

            quantity = (
                level.get("quantity")
                or level.get("qty")
                or level.get("buy_quantity")
                or 0
            )

            total_buy += _safe_number(quantity)

    for level in (asks or [])[:5]:

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

    timestamp = timestamp or datetime.now()

    depth = calculate_depth(
        bids,
        asks,
    )

    state = depth["state"]

    tracker = _HISTORY[symbol]

    if state in ("BUY", "SELL"):

        if tracker["state"] == state:
            tracker["persistence"] += 1

        else:
            tracker["state"] = state
            tracker["persistence"] = 1

    else:

        tracker["state"] = None
        tracker["persistence"] = 0

    confirmed = None

    if (
        tracker["state"] in ("BUY", "SELL")
        and tracker["persistence"] >= PERSISTENCE_REQUIRED
    ):
        confirmed = tracker["state"]

    return {
        "timestamp": timestamp.isoformat() if hasattr(timestamp, "isoformat") else str(timestamp),
        "symbol": symbol,
        "buy_qty": depth["buy_qty"],
        "sell_qty": depth["sell_qty"],
        "ratio": depth["ratio"],
        "state": state,
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


def observe(
    symbol,
    bids,
    asks,
    timestamp=None,
):
    """
    Live integration entry point.

    Samples at most once every 60 seconds per symbol.
    Returns None when:
    - depth is unavailable, or
    - the one-minute sampling interval has not elapsed.
    """

    if not bids or not asks:
        return None

    timestamp = timestamp or datetime.now()

    last_sample = _LAST_SAMPLE.get(symbol)

    if last_sample is not None:

        elapsed = (
            timestamp - last_sample
        ).total_seconds()

        if elapsed < SNAPSHOT_INTERVAL_SECONDS:
            return None

    _LAST_SAMPLE[symbol] = timestamp

    return update(
        symbol,
        bids,
        asks,
        timestamp,
    )


def reset(symbol=None):

    if symbol is None:

        _HISTORY.clear()
        _LAST_SAMPLE.clear()

    else:

        _HISTORY.pop(
            symbol,
            None,
        )

        _LAST_SAMPLE.pop(
            symbol,
            None,
        )


def get_status(symbol):

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
