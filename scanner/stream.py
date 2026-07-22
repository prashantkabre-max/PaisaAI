import config
import upstox_client

from scanner.watchlist import get_watchlist


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

        indicators = calculate_indicators(market)

        if indicators is None:
            return

        result = calculate_score(indicators)

        if result is None:
            return

        print(
            f'{indicators["symbol"]} | '
            f'LTP: {indicators["ltp"]:.2f} | '
            f'Change: {indicators["change_percent"]:.2f}% | '
            f'Score: {result["score"]} | '
            f'Grade: {result["grade"]}'
        )

    def on_error(self, *args):
        print("ERROR:", args)

    def on_close(self, *args):
        print("Connection Closed")

    def start(self):
        print("Connecting...")
        self.streamer.connect()
