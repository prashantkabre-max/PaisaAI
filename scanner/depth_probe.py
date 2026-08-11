import config
import upstox_client

configuration = upstox_client.Configuration()
configuration.access_token = config.ACCESS_TOKEN
api_client = upstox_client.ApiClient(configuration)

seen = 0


def on_open():
    print("=" * 70)
    print("PAISAAI RAW MARKET DEPTH PROBE")
    print("Symbol : HDFCBANK")
    print("Mode   : FULL")
    print("=" * 70)


def on_message(message):
    global seen

    seen += 1

    print()
    print("=" * 70)
    print(f"RAW TICK #{seen}")
    print("=" * 70)

    if not isinstance(message, dict):
        print("MESSAGE TYPE:", type(message))
        print(message)
        return

    print("TOP LEVEL KEYS:", list(message.keys()))

    feeds = message.get("feeds", {})

    if not feeds:
        print("NO FEEDS")
        return

    for instrument_key, data in feeds.items():

        print()
        print("INSTRUMENT:", instrument_key)
        print("FEED KEYS:", list(data.keys()))

        full_feed = data.get("fullFeed", {})

        if not full_feed:
            print("NO fullFeed")
            continue

        print("fullFeed KEYS:", list(full_feed.keys()))

        market = full_feed.get("marketFF", {})

        if not market:
            print("NO marketFF")
            continue

        print("marketFF KEYS:", list(market.keys()))

        ltpc = market.get("ltpc", {})
        market_level = market.get("marketLevel", {})
        quotes = market_level.get("bidAskQuote", [])

        print()
        print("LTPC PRESENT      :", bool(ltpc))
        print("MARKET LEVEL      :", bool(market_level))
        print("DEPTH QUOTES      :", len(quotes))
        print("REQUEST MODE      :", data.get("requestMode"))

        if ltpc:
            print("LTP               :", ltpc.get("ltp"))
            print("PREVIOUS CLOSE    :", ltpc.get("cp"))

        if quotes:
            print()
            print("✅ POPULATED MARKET DEPTH FOUND")
            print("-" * 70)

            for i, quote in enumerate(quotes[:5], 1):
                print(
                    f"LEVEL {i} | "
                    f"BID {quote.get('bidQ')} @ ₹{quote.get('bidP')} | "
                    f"ASK {quote.get('askQ')} @ ₹{quote.get('askP')}"
                )

            print("-" * 70)

            buy_qty = sum(
                float(q.get("bidQ", 0) or 0)
                for q in quotes[:5]
            )

            sell_qty = sum(
                float(q.get("askQ", 0) or 0)
                for q in quotes[:5]
            )

            ratio = buy_qty / sell_qty if sell_qty else 0

            print(f"5-LEVEL BUY QTY  : {buy_qty:,.0f}")
            print(f"5-LEVEL SELL QTY : {sell_qty:,.0f}")
            print(f"BUY/SELL RATIO   : {ratio:.2f}")
            print()
            print("✅ LIVE 5-LEVEL DEPTH VERIFIED")

            raise SystemExit


def on_error(*args):
    print("DEPTH PROBE ERROR:", args)


def on_close(*args):
    print("Depth probe connection closed")


streamer = upstox_client.MarketDataStreamerV3(
    api_client,
    ["NSE_EQ|HDFCBANK"],
    "full",
)

streamer.on("open", on_open)
streamer.on("message", on_message)
streamer.on("error", on_error)
streamer.on("close", on_close)

streamer.auto_reconnect(True, 5, 10)

print("Connecting to raw live depth feed...")
streamer.connect()
