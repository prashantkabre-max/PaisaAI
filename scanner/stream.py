import config
import upstox_client
import traceback

from indicators.engine import calculate_all_indicators
from scanner.watchlist import get_watchlist
from datetime import datetime

from data.candles import (
    update_tick,
    get_symbol_store,
    get_history,
)

configuration = upstox_client.Configuration()
configuration.access_token = config.ACCESS_TOKEN

api_client = upstox_client.ApiClient(configuration)


class LiveStreamer:

    def __init__(self):

        self.watchlist = get_watchlist()

        self.streamer = upstox_client.MarketDataStreamerV3(
            api_client,
            self.watchlist,
            "full",
        )

        self.streamer.on("open", self.on_open)
        self.streamer.on("message", self.on_message)
        self.streamer.on("error", self.on_error)
        self.streamer.on("close", self.on_close)

        self.streamer.auto_reconnect(True, 5, 10)

    def on_open(self):

        print("\n===================================")
        print("PaisaAI Connected")
        print("Subscribed Symbols :", len(self.watchlist))
        print("===================================\n")

    def on_message(self, message):

        from scanner.parser import parse_market_data
        from scanner.indicators import calculate_indicators
        from scanner.scoring import calculate_score

        market = parse_market_data(message)

        if market is None:
            return

        if update_tick(
            symbol=market["symbol"],
            price=market["ltp"],
            volume=market.get("volume", 0),
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ) is None:
            return

        history = {
            "1m": get_history(market["symbol"], "1m"),
        }

        all_indicators = calculate_all_indicators(
            history["1m"],
            market["symbol"],
        )

        indicators = calculate_indicators(
            market,
            all_indicators,
        )

        if indicators is None:
            return

        result = calculate_score(indicators)
        print(indicators)

        print(indicators["display_symbol"], result)

        if result is None:
            return

        signal = "IGNORE"

        ema9 = indicators.get("ema9")
        ema20 = indicators.get("ema20")

        if result["grade"] != "IGNORE" and ema9 is not None and ema20 is not None:
            if ema9 > ema20:
                signal = "BUY"
            else:
                signal = "SELL"

        if result["grade"] != "IGNORE":
            print("=" * 70)
            print(f'STOCK      : {indicators["display_symbol"]}')
            print(f'GRADE      : {result["grade"]}')
            print(f'SIGNAL     : {signal}')
            print(f'CONFIDENCE : {result["confidence"]}%')
            print(f'PASSED     : {", ".join(result["passed"])}')

            if result["failed"]:
                print(f'FAILED     : {", ".join(result["failed"])}')

            print("=" * 70)

    def on_error(self, *args):
        print("ERROR:", args)
        traceback.print_exc()

    def on_close(self, *args):
        print("Connection Closed")

    def start(self):
        print("Connecting...")
        self.streamer.connect()
