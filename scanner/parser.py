def parse_market_data(message):
    try:
        if not isinstance(message, dict):
            return None

        if "feeds" not in message:
            return None

        parsed = []

        for instrument_key, data in message["feeds"].items():

            feed = data.get("fullFeed", {})
            market = feed.get("marketFF", {})
            ltpc = market.get("ltpc", {})
            ohlc = market.get("marketOHLC", {}).get("ohlc", [])

            candle = {}

            if len(ohlc) > 0:
                candle = ohlc[0]

            parsed.append({
                "symbol": instrument_key,
                "ltp": ltpc.get("ltp"),
                "change_percent": ltpc.get("cp"),
                "open": candle.get("open"),
                "high": candle.get("high"),
                "low": candle.get("low"),
                "close": candle.get("close"),
                "volume": ltpc.get("ltq", 0)
            })

        if len(parsed) == 0:
            return None

        return parsed[0]

    except Exception as e:
        print("Parser Error:", e)
        return None
