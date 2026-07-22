def calculate_indicators(data):
    """
    Calculate basic market indicators.
    """

    if data is None:
        return None

    ltp = data.get("ltp")
    previous_close = data.get("previous_close")

    if ltp is None or previous_close is None:
        return None

    change = ltp - previous_close
    change_percent = (change / previous_close) * 100

    return {
        "symbol": data["symbol"],
        "ltp": ltp,
        "change": round(change, 2),
        "change_percent": round(change_percent, 2),
        "open": data.get("open"),
        "high": data.get("high"),
        "low": data.get("low"),
        "close": data.get("close")
    }
