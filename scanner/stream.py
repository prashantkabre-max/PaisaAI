import config
import upstox_client
import traceback

from datetime import datetime

from indicators.engine import calculate_all_indicators

from scanner.watchlist import get_watchlist
from scanner.risk import calculate_risk
from scanner.ranking import print_ranking

from data.candles import (
    update_tick,
    get_history,
)

configuration = upstox_client.Configuration()
configuration.access_token = config.ACCESS_TOKEN

api_client = upstox_client.ApiClient(configuration)


class LiveStreamer:

    def __init__(self):

        self.watchlist = get_watchlist()
        self.live_trades = []

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

    def process_market(self, message):

        from scanner.parser import parse_market_data

        market = parse_market_data(message)

        if market is None:
            return None

        if update_tick(
            symbol=market["symbol"],
            price=market["ltp"],
            volume=market.get("volume", 0),
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ) is None:
            return None

        return market
    def calculate_indicators(self, market):

        from scanner.indicators import calculate_indicators

        history = {
            "1m": get_history(market["symbol"], "1m"),
        }

        all_indicators = calculate_all_indicators(
            history["1m"],
            market["symbol"],
        )

        return calculate_indicators(
            market,
            all_indicators,
        )

    def calculate_trade(self, indicators):

        from scanner.scoring import calculate_score

        if indicators is None:
            return None

        result = calculate_score(indicators)

        if result is None:
            return None

        signal = "IGNORE"

        ema9 = indicators.get("ema9")
        ema20 = indicators.get("ema20")

        if (
            result["grade"] != "IGNORE"
            and ema9 is not None
            and ema20 is not None
        ):
            signal = "BUY" if ema9 > ema20 else "SELL"

        risk = None

        if signal != "IGNORE":
            risk = calculate_risk(
                indicators,
                signal,
            )

        return indicators, result, signal, risk
    def print_trade(self, indicators, result, signal, risk):

        print(indicators)
        print(indicators["display_symbol"], result)

        if result["grade"] == "IGNORE":
            return

        trade = {
            "symbol": indicators["display_symbol"],
            "signal": signal,
            "grade": result["grade"],
            "confidence": result["confidence"],
        }

        self.live_trades.append(trade)
        self.live_trades = self.live_trades[-50:]

        print_ranking(self.live_trades)

        print("=" * 70)
        print(f'STOCK      : {indicators["display_symbol"]}')
        print(f'GRADE      : {result["grade"]}')
        print(f'SIGNAL     : {signal}')
        print(f'CONFIDENCE : {result["confidence"]}%')
        print(f'PASSED     : {", ".join(result["passed"])}')

        if result["failed"]:
            print(f'FAILED     : {", ".join(result["failed"])}')

        if risk:
            print(f'ENTRY      : {risk["entry"]}')
            print(f'STOP LOSS  : {risk["stop_loss"]}')
            print(f'TARGET 1   : {risk["target1"]}')
            print(f'TARGET 2   : {risk["target2"]}')
            print(f'TARGET 3   : {risk["target3"]}')
            print(f'R:R        : {risk["risk_reward"]}:1')

        print("=" * 70)
    def on_message(self, message):

        market = self.process_market(message)

        if market is None:
            return

        indicators = self.calculate_indicators(market)

        trade = self.calculate_trade(indicators)

        if trade is None:
            return

        self.print_trade(*trade)

    def on_error(self, *args):
        print("ERROR:", args)
        traceback.print_exc()

    def on_close(self, *args):
        print("Connection Closed")

    def start(self):
        print("Connecting...")
        self.streamer.connect()

