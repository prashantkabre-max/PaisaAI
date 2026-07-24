def calculate_indicators(data, all_indicators=None):
    """
    Combine live market data with calculated indicators.
    """

    if data is None:
        return None

    if all_indicators is None:
        all_indicators = {}

    ltp = data.get("ltp")
    previous_close = data.get("close")

    if ltp is None or previous_close is None:
        return None

    change = ltp - previous_close

    if previous_close != 0:
        change_percent = (change / previous_close) * 100
    else:
        change_percent = 0

    return {
        "symbol": data["symbol"],
        "ltp": ltp,
        "change": round(change, 2),
        "change_percent": round(change_percent, 2),

        "open": data.get("open"),
        "high": data.get("high"),
        "low": data.get("low"),
        "close": data.get("close"),

        "ema9": all_indicators.get("ema9"),
        "ema20": all_indicators.get("ema20"),

        "vwap": all_indicators.get("vwap"),

        "current_volume": all_indicators.get("current_volume"),
        "average_volume": all_indicators.get("average_volume"),
        "rvol": all_indicators.get("rvol"),

        "rsi": all_indicators.get("rsi"),

        "macd": all_indicators.get("macd"),
        "macd_signal": all_indicators.get("macd_signal"),
        "macd_histogram": all_indicators.get("macd_histogram"),

        "atr": all_indicators.get("atr"),

        "adx": all_indicators.get("adx"),
        "plus_di": all_indicators.get("plus_di"),
        "minus_di": all_indicators.get("minus_di"),
        "adx_trend": all_indicators.get("adx_trend"),

        "supertrend": all_indicators.get("supertrend"),
        "supertrend_trend": all_indicators.get("supertrend_trend"),
    }
