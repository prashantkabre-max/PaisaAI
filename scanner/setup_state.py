"""
PaisaAI Setup State Manager
Stable Scanner V2
"""

IDLE = "IDLE"
ACTIVE_BUY = "ACTIVE_BUY"
ACTIVE_SELL = "ACTIVE_SELL"
COOLDOWN = "COOLDOWN"

_state = {}
_skip = {}


def allow_signal(symbol, action):
    """
    Returns True only if a new trade is allowed.
    """

    # Consume one completed candle after cooldown.
    if _skip.get(symbol, False):
        _skip[symbol] = False
        _state[symbol] = IDLE
        return False

    state = _state.get(symbol, IDLE)

    if state == ACTIVE_BUY:
        return False

    if state == ACTIVE_SELL:
        return False

    if action == "BUY":
        _state[symbol] = ACTIVE_BUY
        return True

    if action == "SELL":
        _state[symbol] = ACTIVE_SELL
        return True

    return False


def trade_closed(symbol):
    """
    Called only after TP3 or STOP LOSS.
    """
    _state[symbol] = COOLDOWN
    _skip[symbol] = True


def get_state(symbol):
    return _state.get(symbol, IDLE)
