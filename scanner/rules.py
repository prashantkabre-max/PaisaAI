from scanner.settings import *


def ema_rule(indicators):
    ema9 = indicators.get("ema9")
    ema20 = indicators.get("ema20")

    if ema9 is None or ema20 is None:
        return False

    return ema9 > ema20


def vwap_rule(indicators):
    vwap = indicators.get("vwap")
    ltp = indicators.get("ltp")

    if vwap is None or ltp is None:
        return False

    return ltp > vwap


def macd_rule(indicators):
    macd = indicators.get("macd")
    signal = indicators.get("macd_signal")

    if macd is None or signal is None:
        return False

    return macd > signal


def adx_rule(indicators):
    adx = indicators.get("adx")

    if adx is None:
        return False

    return adx >= 20


def supertrend_rule(indicators):
    return indicators.get("supertrend_trend") == "UP"


def rvol_rule(indicators):
    rvol = indicators.get("rvol")

    if rvol is None:
        return False

    return rvol >= 1.5


def price_change_rule(indicators):
    change = indicators.get("change_percent")

    if change is None:
        return False

    return 0.5 <= change <= 5.0


def open_rule(indicators):
    ltp = indicators.get("ltp")
    open_price = indicators.get("open")

    if ltp is None or open_price is None:
        return False

    return ltp > open_price


def high_low_rule(indicators):
    high = indicators.get("high")
    ltp = indicators.get("ltp")

    if high is None or ltp is None:
        return False

    return ltp >= high * 0.995


def rsi_rule(indicators):
    rsi = indicators.get("rsi")

    if rsi is None:
        return False

    return 55 <= rsi <= 70
