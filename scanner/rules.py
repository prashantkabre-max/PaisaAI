from scanner.settings import *


def ema_rule(indicators):
    """
    EMA Trend Rule
    """
    if indicators.get("ema9") is None or indicators.get("ema20") is None:
        return 0

    if indicators["ema9"] > indicators["ema20"]:
        return 20

    if indicators["ema9"] < indicators["ema20"]:
        return -20

    return 0


def vwap_rule(indicators):
    """
    VWAP Rule
    """
    if indicators.get("vwap") is None:
        return 0

    if indicators["ltp"] > indicators["vwap"]:
        return 15

    return -15


def rvol_rule(indicators):
    """
    Relative Volume Rule
    """
    rvol = indicators.get("rvol")

    if rvol is None:
        return 0

    if rvol >= RVOL_HIGH:
        return 15

    if rvol >= RVOL_MEDIUM:
        return 10

    if rvol >= RVOL_LOW:
        return 5

    return 0


def price_change_rule(indicators):
    """
    Price Change Rule
    """
    change = indicators.get("change_percent", 0)

    if change > PRICE_CHANGE_HIGH:
        return 30

    if change > PRICE_CHANGE_MEDIUM:
        return 15

    return 0


def open_rule(indicators):
    """
    Price Above Open
    """
    if indicators.get("open") is None:
        return 0

    if indicators["ltp"] > indicators["open"]:
        return 10

    return 0


def high_low_rule(indicators):
    """
    Near High / Near Low
    """
    score = 0

    if indicators.get("high") is not None:
        if indicators["ltp"] >= indicators["high"]:
            score += 10

    if indicators.get("low") is not None:
        if indicators["ltp"] <= indicators["low"]:
            score -= 10

    return score


def rsi_rule(indicators):
    """
    RSI Rule
    """
    rsi = indicators.get("rsi")

    if rsi is None:
        return 0

    if 55 <= rsi <= 70:
        return 10

    if rsi > 70:
        return 5

    if rsi < 30:
        return -10

    return 0


def macd_rule(indicators):
    """
    MACD Rule
    """
    macd = indicators.get("macd")
    signal = indicators.get("macd_signal")

    if macd is None or signal is None:
        return 0

    if macd > signal:
        return 10

    if macd < signal:
        return -10

    return 0


def adx_rule(indicators):
    """
    ADX Rule
    """
    adx = indicators.get("adx")

    if adx is None:
        return 0

    if adx >= 25:
        return 15

    if adx >= 20:
        return 10

    return 0


def supertrend_rule(indicators):
    """
    Supertrend Rule
    """
    trend = indicators.get("supertrend_trend")

    if trend == "UP":
        return 15

    if trend == "DOWN":
        return -15

    return 0
