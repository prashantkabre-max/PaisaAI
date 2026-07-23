from collections import defaultdict
from datetime import datetime

MAX_CANDLES = 500

TIMEFRAMES = ["1m", "3m", "5m", "15m", "30m"]

candles = defaultdict(lambda: {
    "current": None,
    "history": {
        "1m": [],
        "3m": [],
        "5m": [],
        "15m": [],
        "30m": []
    }
})


def get_symbol_store(symbol):
    return candles[symbol]


def create_new_candle(price, volume, timestamp):
    return {
        "timestamp": timestamp,
        "open": price,
        "high": price,
        "low": price,
        "close": price,
        "volume": volume
    }
def update_tick(symbol, price, volume, timestamp):
    store = get_symbol_store(symbol)

    if price is None:
        return

    if volume is None:
        volume = 0
    else:
        volume = int(volume)

    current = store["current"]

    # First candle for this symbol
    if current is None:
        store["current"] = create_new_candle(price, volume, timestamp)
        return store["current"]

    # Same minute → update existing candle
    if current["timestamp"][:16] == timestamp[:16]:
        current["high"] = max(current["high"], price)
        current["low"] = min(current["low"], price)
        current["close"] = price
        current["volume"] += volume
        return current

    # Minute changed → store completed candle
    store["history"]["1m"].append(current)

    if len(store["history"]["1m"]) > MAX_CANDLES:
        store["history"]["1m"].pop(0)

    # Start a new candle
    store["current"] = create_new_candle(price, volume, timestamp)

    return store["current"]
def get_latest_candle(symbol):
    store = get_symbol_store(symbol)
    return store["current"]

def get_history(symbol, timeframe="1m"):
    store = get_symbol_store(symbol)
    return store["history"][timeframe]

