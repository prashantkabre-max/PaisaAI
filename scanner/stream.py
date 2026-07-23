import config
import upstox_client

from indicators.ema import calculate_ema
from indicators.timeframes import build_timeframe
from scanner.watchlist import get_watchlist
from datetime import datetime
from data.candles import update_tick, get_latest_candle, get_symbol_store, get_history


configuration = upstox_client.Configuration()
configuration.access_token = config.ACCESS_TOKEN

api_client = upstox_client.ApiClient(configuration)


class LiveStreamer:

    def __init__(self):

        self.watchlist = get_watchlist()

        self.streamer = upstox_client.MarketDataStreamerV3(
            api_client,
            self.watchlist,
            "full"
        )

        self.streamer.on("open", self.on_open)
        self.streamer.on("message", self.on_message)
        self.streamer.on("error", self.on_error)
        self.streamer.on("close", self.on_close)

        self.streamer.auto_reconnect(True, 5, 10)

    def on_open(self):

        print("\n===================================")
        print("Kabre AI Trader V2 Connected")
        print("Subscribed Symbols :", len(self.watchlist))
        print("===================================\n")

    def on_message(self, message):

        from scanner.parser import parse_market_data
        from scanner.indicators import calculate_indicators
        from scanner.scoring import calculate_score

        market = parse_market_data(message)

        if market is None:
            return


        update_tick(
            symbol=market["symbol"],
            price=market["ltp"],
            volume=market.get("volume", 0),
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

        latest = get_latest_candle(market["symbol"])
        history_1m = get_history(market["symbol"], "1m")

        ema9 = calculate_ema(history_1m, 9)
        ema20 = calculate_ema(history_1m, 20)

        if False and latest:
            print(
                f"CANDLE | "
                f"O:{latest['open']} "
                f"H:{latest['high']} "
                f"L:{latest['low']} "
                f"C:{latest['close']} "
                f"V:{latest['volume']}"
            )

        indicators = calculate_indicators(
            market,
            ema9=ema9,
            ema20=ema20
        )

        if indicators is None:
            return

        result = calculate_score(indicators)

        if result is None:
            return
        store = get_symbol_store(market["symbol"])
        history = len(store["history"]["1m"])
        last = None

        if len(store["history"]["1m"]) > 0:
            last = store["history"]["1m"][-1]

        if last:
            print(
                f"LAST 1M -> "
                f"O:{last['open']} "
                f"H:{last['high']} "
                f"L:{last['low']} "
                f"C:{last['close']} "
                f"V:{last['volume']}"
            )

        print(
            f'{indicators["symbol"]} | '
            f'LTP: {indicators["ltp"]:.2f} | '
            f'Change: {indicators["change_percent"]:.2f}% | '
            f'Score: {result["score"]} | '
            f'Grade: {result["grade"]} | '
            f'Candles: {history}'
        )

    def on_error(self, *args):
        print("ERROR:", args)

    def on_close(self, *args):
        print("Connection Closed")

    def start(self):
        print("Connecting...")
        self.streamer.connect()
