from collections import defaultdict

MAX_CANDLES = 500

TIMEFRAMES = {
    "1m": 1,
    "3m": 3,
    "5m": 5,
    "15m": 15,
    "30m": 30
}

candles = defaultdict(
    lambda: {
        "1m": [],
        "3m": [],
        "5m": [],
        "15m": [],
        "30m": []
    }
)

def get_symbol_store(symbol):
    """
    Returns the candle storage for a symbol.
    Creates it automatically if it doesn't exist.
    """
    return candles[symbol]

def update_tick(symbol, price, volume, timestamp):
    """
    Receives one live market tick.
    (Implementation will be added in the next step.)
    """
    store = get_symbol_store(symbol)

    return store

def create_new_candle(price, volume, timestamp):
    """
    Creates a new 1-minute candle.
    """

    return {
        "timestamp": timestamp,
        "open": price,
        "high": price,
        "low": price,
        "close": price,
        "volume": volume
    }
