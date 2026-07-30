from collections import defaultdict
from datetime import datetime

MAX_CANDLES = 500

TIMEFRAME_MAP = {
    "1m": 1,
    "3m": 3,
    "5m": 5,
    "15m": 15,
    "30m": 30,
    "60m":60,
}

candles = defaultdict(
    lambda: {
        "current": {
            tf: None for tf in TIMEFRAME_MAP
        },
        "history": {
            tf: [] for tf in TIMEFRAME_MAP
        },
    }
)


def get_symbol_store(symbol):
    return candles[symbol]


def create_new_candle(price, volume, timestamp):
    return {
        "timestamp": timestamp,
        "open": price,
        "high": price,
        "low": price,
        "close": price,
        "volume": int(volume) if volume else 0,
    }


def minute_number(timestamp):
    """
    Converts timestamp into minute number.
    Works with ISO timestamps coming from Upstox.
    """

    if isinstance(timestamp, datetime):
        dt = timestamp
    else:
        try:
            dt = datetime.fromisoformat(
                timestamp.replace("Z", "+00:00")
            )
        except Exception:
            return None

    return int(dt.timestamp() // 60)


def is_new_timeframe(previous_timestamp, current_timestamp, minutes):

    old = minute_number(previous_timestamp)
    new = minute_number(current_timestamp)

    if old is None or new is None:
        return False

    return (new // minutes) != (old // minutes)


def append_history(store, timeframe, candle):

    history = store["history"][timeframe]

    history.append(candle)

    if len(history) > MAX_CANDLES:
        history.pop(0)
def update_tick(symbol, price, volume, timestamp):

    store = get_symbol_store(symbol)

    if price is None:
        return None

    if volume is None:
        volume = 0
    else:
        volume = int(volume)

    current = store["current"]["1m"]

    # -----------------------------
    # Build 1 Minute Candle
    # -----------------------------
    if current is None:

        store["current"]["1m"] = create_new_candle(
            price,
            volume,
            timestamp
        )

        return store["current"]["1m"]

    if not is_new_timeframe(
        current["timestamp"],
        timestamp,
        1
    ):

        current["high"] = max(current["high"], price)
        current["low"] = min(current["low"], price)
        current["close"] = price
        current["volume"] += volume

        return None

    # -----------------------------
    # One-minute candle completed
    # -----------------------------
    completed = current

    append_history(
        store,
        "1m",
        completed
    )

    # -----------------------------
    # Update higher timeframes
    # from completed 1m candle
    # -----------------------------
    for tf, minutes in TIMEFRAME_MAP.items():

        if tf == "1m":
            continue

        tf_current = store["current"][tf]

        if tf_current is None:

            store["current"][tf] = completed.copy()
            continue

        if is_new_timeframe(
            tf_current["timestamp"],
            completed["timestamp"],
            minutes
        ):

            append_history(
                store,
                tf,
                tf_current
            )

            store["current"][tf] = completed.copy()

        else:

            tf_current["high"] = max(
                tf_current["high"],
                completed["high"]
            )

            tf_current["low"] = min(
                tf_current["low"],
                completed["low"]
            )

            tf_current["close"] = completed["close"]
            tf_current["volume"] += completed["volume"]

    # -----------------------------
    # Start next 1m candle
    # -----------------------------
    store["current"]["1m"] = create_new_candle(
        price,
        volume,
        timestamp
    )

    return completed
def get_latest_candle(symbol):

    store = get_symbol_store(symbol)

    return store["current"]["1m"]


def get_history(symbol, timeframe="1m"):

    store = get_symbol_store(symbol)

    if timeframe not in TIMEFRAME_MAP:
        return []

    history = list(store["history"][timeframe])

    current = store["current"][timeframe]

    if current is not None:
        history.append(current)

    return history


def clear_symbol(symbol):

    if symbol in candles:
        del candles[symbol]


def clear_all():

    candles.clear()


def get_available_timeframes():

    return list(TIMEFRAME_MAP.keys())
