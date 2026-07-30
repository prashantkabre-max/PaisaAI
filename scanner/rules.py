from scanner.settings import *


def is_buy(direction):
    return direction.upper() == "BUY"


def is_sell(direction):
    return direction.upper() == "SELL"


def ema_rule(indicators, direction="BUY"):
    ema9 = indicators.get("ema9")
    ema20 = indicators.get("ema20")

    ema9_previous = indicators.get("ema9_previous")
    ema20_previous = indicators.get("ema20_previous")

    if (
        ema9 is None
        or ema20 is None
        or ema9_previous is None
        or ema20_previous is None
    ):
        return False

    if is_buy(direction):
        return (
            ema9_previous <= ema20_previous
            and ema9 > ema20
        )

    return (
        ema9_previous >= ema20_previous
        and ema9 < ema20
    )


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
    rvol = indicators.get("rvol")

    if rvol is None:
        return False

    return rvol >= 1.2


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
        return 52 <= rsi <= 72

    return 28 <= rsi <= 48
