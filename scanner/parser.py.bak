_last_vtt = {}


def parse_market_data(message):
    try:
        if not isinstance(message, dict):
            return None

        feeds = message.get("feeds", {})
        if not feeds:
            return None

        parsed = []

        for instrument_key, data in feeds.items():

            feed = data.get("fullFeed", {})
            market = feed.get("marketFF", {})
            ltpc = market.get("ltpc", {})
            ohlc = market.get("marketOHLC", {}).get("ohlc", [])

            candle = ohlc[0] if ohlc else {}

            ltp = ltpc.get("ltp")

            # Upstox LTPC `cp` = previous trading-session close price.
            previous_close = ltpc.get("cp")

            current_vtt = int(market.get("vtt", 0) or 0)
            previous_vtt = _last_vtt.get(
                instrument_key,
                current_vtt,
            )

            incremental_volume = max(
                0,
                current_vtt - previous_vtt,
            )

            _last_vtt[instrument_key] = current_vtt

            if instrument_key == "NSE_EQ|HDFCBANK":
                print(f"VTT={current_vtt} PREV={previous_vtt} INC={incremental_volume}")

            parsed.append({
                "symbol": instrument_key,
                "ltp": ltp,

                # Explicit professional price-change baseline
                "previous_close": previous_close,

                "open": candle.get("open"),
                "high": candle.get("high"),
                "low": candle.get("low"),
                "close": candle.get("close"),

                # Incremental traded volume for candle builder
                "volume": incremental_volume,
            })

        if not parsed:
            return None

        return parsed[0]

    except Exception as e:
        print("Parser Error:", e)
        return None
