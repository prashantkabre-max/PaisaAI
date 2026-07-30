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

        history = {}

        for timeframe in (
            "1m",
            "3m",
            "5m",
            "15m",
            "30m",
            "60m",
        ):
            history[timeframe] = get_history(
                market["symbol"],
                timeframe,
            )

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

        buy_score = calculate_score(indicators, "BUY")
        sell_score = calculate_score(indicators, "SELL")

        if buy_score is None and sell_score is None:
            return None

        if sell_score["confidence"] > buy_score["confidence"]:
            score_result = sell_score
        else:
            score_result = buy_score

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

        if not register_trade(trade):
            return

        #print(trade)

        ranking_trade = {
            "symbol": trade["symbol"],
            "action": trade["action"],
            "grade": trade["grade"],
            "confidence": trade["confidence"],
            "risk": trade["risk"],
            "passed": trade["passed"],
            "failed": trade["failed"],
        }

        self.live_trades.append(ranking_trade)
        self.live_trades = self.live_trades[-50:]

       # print_ranking(self.live_trades)

        print()

        signal_icon = "🟢" if trade["action"] == "BUY" else "🔴"

        print("=" * 70)

        grade = trade["grade"]
        action = trade["action"]

        if action == "BUY":
            title = f"🟢🟢🟢 BUY SIGNAL ({grade})"
        else:
            title = f"🔴🔴🔴 SELL SIGNAL ({grade})"

        print(title)
        print(f"📊 Stock : {trade.get('display_symbol', trade['symbol'])}")

        print("=" * 70)

        if trade["risk"]:
            risk = trade["risk"]

            print(f"💰 Entry Price    : ₹{risk['entry']:.2f}")
            print(f"🛑 Stop Loss      : ₹{risk['stop_loss']:.2f}")
            print()

            print(f"🎯 Target 1       : ₹{risk['target1']:.2f}")
            print(f"🎯 Target 2       : ₹{risk['target2']:.2f}")
            print(f"🎯 Target 3       : ₹{risk['target3']:.2f}")
            print()

            print(f"📉 Maximum Loss   : ₹{risk['risk']:.2f}/share")
            print(f"📈 Expected Gain  : ₹{risk['reward']:.2f}/share")
            print()

            rr = risk["risk_reward"]

            if rr >= 2:
                quality = "🟢 EXCELLENT"
            elif rr >= 1.75:
                quality = "🔵 GOOD"
            elif rr >= 1.50:
                quality = "🟡 AVERAGE"
            else:
                quality = "🔴 POOR"

            print(f"⭐ Trade Quality  : {quality}")
            print(f"⚖️ Risk vs Reward : Risk ₹1 → Reward ₹{rr:.1f}")
            print()

        print(f"🎯 Confidence     : {trade['confidence']}%")
        print(f"🏅 Grade          : {trade['grade']}")

        if trade["passed"]:
            print(f"✅ Confirmations  : {', '.join(trade['passed'])}")

        if trade["failed"]:
            print(f"❌ Missing        : {', '.join(trade['failed'])}")

        if alert.get("generated_at"):
            print(f"🕒 Time           : {alert['generated_at']}")

        print("=" * 70)



    def on_message(self, message):

        market = self.process_market(message)

        if market is None:
            return

        event = update_trade(
            market["symbol"],
            market["ltp"],
        )
#         print(f"DEBUG: {market['symbol']} LTP={market['ltp']} EVENT={event}")

        if event:
            print()
            print("=" * 70)

            if event["event"] == "TARGET_1_HIT":
                print(f"🏆🏆 TARGET 1 HIT : {event.get('display_symbol', event['symbol'])}")

            elif event["event"] == "TARGET_2_HIT":
                print(f"🥈🥈 TARGET 2 HIT : {event.get('display_symbol', event['symbol'])}")

            elif event["event"] == "TARGET_3_HIT":
                print(f"👑👑👑 TARGET 3 ACHIEVED : {event.get('display_symbol', event['symbol'])}")

            elif event["event"] == "STOP_LOSS_HIT":
                print(f"😭😭 STOP LOSS HIT : {event.get('display_symbol', event['symbol'])}")

            print(f"🕒 Time : {datetime.now().strftime('%H:%M:%S')}")
            print("=" * 70)
            print()

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
