def calculate_indicators(data):
    """
    Calculate basic market indicators.
    """

    if data is None:
        return None

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
        "close": data.get("close")
    }
