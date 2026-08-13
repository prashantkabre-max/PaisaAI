from scanner.settings import *


def is_buy(direction):
    return direction.upper() == "BUY"


def is_sell(direction):
    return direction.upper() == "SELL"


def ema_rule(indicators, direction="BUY"):
    ema9 = indicators.get("ema9")
    ema20 = indicators.get("ema20")

    if ema9 is None or ema20 is None:
        return False

    if is_buy(direction):
        return ema9 > ema20

    return ema9 < ema20


def vwap_rule(indicators, direction="BUY"):
    vwap = indicators.get("vwap")
    ltp = indicators.get("ltp")

    if vwap is None or ltp is None:
        return False

    if is_buy(direction):
        return ltp > vwap

    return ltp < vwap


def macd_rule(indicators, direction="BUY"):
    macd = indicators.get("macd")
    signal = indicators.get("macd_signal")

    if macd is None or signal is None:
        return False

    if is_buy(direction):
        return macd > signal

    return macd < signal


def adx_rule(indicators):
    adx = indicators.get("adx")

    if adx is None:
        return False

    return adx >= 20


def supertrend_rule(indicators, direction="BUY"):
    trend = indicators.get("supertrend_trend")

    if trend is None:
        return False

    if is_buy(direction):
        return trend == "UP"

    return trend == "DOWN"


def rvol_rule(indicators):
    """
    PaisaAI Core RVOL Rule.

    Confirmation:
        RVOL >= 1.20
    """
    rvol = indicators.get("rvol")

    if rvol is None:
        return False

    return rvol >= RVOL_MIN

def price_change_rule(indicators, direction="BUY"):
    change = indicators.get("change_percent")

    if change is None:
        return False

    if is_buy(direction):
        return 0.5 <= change <= 5

    return -5 <= change <= -0.5


def open_rule(indicators, direction="BUY"):
    ltp = indicators.get("ltp")
    day_open = indicators.get("open")

    if ltp is None or day_open is None:
        return False

    if is_buy(direction):
        return ltp > day_open

    return ltp < day_open


def high_low_rule(indicators, direction="BUY"):
    ltp = indicators.get("ltp")
    day_high = indicators.get("high")
    day_low = indicators.get("low")

    if ltp is None or day_high is None or day_low is None:
        return False

    midpoint = (day_high + day_low) / 2

    if is_buy(direction):
        return ltp > midpoint

    return ltp < midpoint


def rsi_rule(indicators, direction="BUY"):
    rsi = indicators.get("rsi")

    if rsi is None:
        return False

    if is_buy(direction):
        return RSI_BUY_MIN <= rsi <= RSI_BUY_MAX

    return RSI_SELL_MIN <= rsi <= RSI_SELL_MAX


# ============================================================
# INDUSTRY-STANDARD INDICATOR CONFIRMATIONS
# ============================================================

def stochastic_rule(indicators, direction="BUY"):
    k = indicators.get("stochastic_k")
    d = indicators.get("stochastic_d")

    if k is None or d is None:
        return False

    if is_buy(direction):
        return k > d

    return k < d


def support_resistance_rule(indicators, direction="BUY"):
    position = indicators.get(
        "support_resistance_position"
    )

    if is_buy(direction):
        return position in {
            "BREAKOUT",
            "UPPER_RANGE",
        }

    return position in {
        "BREAKDOWN",
        "LOWER_RANGE",
    }


def bollinger_rule(indicators, direction="BUY"):
    position = indicators.get("bb_position")
    percent_b = indicators.get("bb_percent_b")

    if is_buy(direction):
        return (
            position == "ABOVE_MIDDLE"
            or (
                percent_b is not None
                and percent_b >= 0.50
            )
        )

    return (
        position == "BELOW_MIDDLE"
        or (
            percent_b is not None
            and percent_b <= 0.50
        )
    )


def bollinger_bandwidth_rule(indicators):
    bandwidth = indicators.get("bb_bandwidth")

    if bandwidth is None:
        return False

    return bandwidth > 0


def ichimoku_rule(indicators, direction="BUY"):
    price_position = indicators.get(
        "ichimoku_price_position"
    )
    tk_direction = indicators.get(
        "ichimoku_tk_direction"
    )

    if is_buy(direction):
        return (
            price_position == "ABOVE_CLOUD"
            and tk_direction == "BULLISH"
        )

    return (
        price_position == "BELOW_CLOUD"
        and tk_direction == "BEARISH"
    )
