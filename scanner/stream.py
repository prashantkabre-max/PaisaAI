import config
import upstox_client
import traceback

from datetime import datetime

from indicators.engine import calculate_all_indicators

from scanner.watchlist import get_watchlist
from scanner.ranking import print_ranking

from scanner.decision import evaluate_trade
from scanner.alerts import process_alert
from scanner.trade_manager import (
    register_trade,
    update_trade,
)

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
            timestamp=datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
        ) is None:
            return None

        return market

    def calculate_indicators(self, market):

        from scanner.indicators import calculate_indicators

        history = {
            "1m": get_history(
                market["symbol"],
                "1m",
            ),
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

        score_result = calculate_score(indicators)

        if score_result is None:
            return None

        return evaluate_trade(
            indicators,
            score_result,
        )

    def print_trade(self, trade):

        if trade is None:
            return

        if trade["grade"] == "IGNORE":
            return

        alert = process_alert(trade)

        # If there is no alert, this trade is already active.
        # Don't print or rank it again.
        if alert is None:
            return

        register_trade(trade)

        print(trade)

        ranking_trade = {
            "symbol": trade["symbol"],
            "signal": trade["action"],
            "grade": trade["grade"],
            "confidence": trade["confidence"],
        }

        self.live_trades.append(ranking_trade)
        self.live_trades = self.live_trades[-50:]

        print_ranking(self.live_trades)

        print("\n🔔 ALERT")
        print(alert)

        print("=" * 70)
        print(f'STOCK      : {trade["symbol"]}')
        print(f'ACTION     : {trade["action"]}')
        print(f'GRADE      : {trade["grade"]}')
        print(f'CONFIDENCE : {trade["confidence"]}%')

        if trade["passed"]:
            print(f'PASSED     : {", ".join(trade["passed"])}')

        if trade["failed"]:
            print(f'FAILED     : {", ".join(trade["failed"])}')

        if trade["risk"]:

            risk = trade["risk"]

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

        event = update_trade(
            market["symbol"],
            market["ltp"],
        )

        if event:
            print("\n📢 TRADE UPDATE")
            print(event)

        indicators = self.calculate_indicators(market)

        trade = self.calculate_trade(indicators)

        if trade is None:
            return

        self.print_trade(trade)

    def on_error(self, *args):
        print("ERROR:", args)
        traceback.print_exc()

    def on_close(self, *args):
        print("Connection Closed")

    def start(self):
        print("Connecting...")
        self.streamer.connect()
