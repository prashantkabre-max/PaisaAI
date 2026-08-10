import config
import upstox_client
import traceback

from datetime import datetime

from indicators.engine import calculate_all_indicators

from scanner.watchlist import get_watchlist

from scanner.decision import evaluate_trade
from scanner.alerts import process_alert
from scanner.runtime import MARKET_STATE
from scanner.signal_state import SignalState

from scanner.trade_manager import (
    register_trade,
    update_trade,
    get_active_trades,
)

from data.candles import (
    update_tick,
    get_history,
    get_closed_history,
)

configuration = upstox_client.Configuration()
configuration.access_token = config.ACCESS_TOKEN

api_client = upstox_client.ApiClient(configuration)


class LiveStreamer:

    def __init__(self, risk_mode="production"):

        self.risk_mode = risk_mode

        self.watchlist = get_watchlist()
        self.live_trades = []
        self.trade_number = 0
        self.session_start = datetime.now()
        self.last_summary = datetime.now()

        self.session_stats = {
            "total": 0,
            "buy": 0,
            "sell": 0,
            "a_plus": 0,
            "a": 0,
            "active": 0,
            "target1": 0,
            "target2": 0,
            "target3": 0,
            "stoploss": 0,
            "wins": 0,
            "losses": 0,
            "gross_profit": 0.0,
            "gross_loss": 0.0,
        }
        self.signal_state = SignalState()


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

        candle_update = update_tick(
            symbol=market["symbol"],
            price=market["ltp"],
            volume=market.get("volume", 0),
            timestamp=datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
        )

        if candle_update is None:
            return None

        # Exit monitoring must run on every live tick.
        # Signal generation remains restricted to closed 5m candles.
        market["_5m_closed"] = (
            "5m" in candle_update.get("closed_timeframes", [])
        )

        return market

    def process_replay_market(self, market):

        """
        Replay V2 entry point.

        Receives a completed market snapshot generated from
        historical candles and processes it through the
        exact same pipeline used by live trading.
        """

        return self.process_completed_market(market)


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

            if timeframe == "5m":
                history[timeframe] = get_closed_history(
                    market["symbol"],
                    timeframe,
                )
            else:
                history[timeframe] = get_history(
                    market["symbol"],
                    timeframe,
                )

        all_indicators = calculate_all_indicators(
            history,
            market["symbol"],
        )

        timeframe_indicators = {}

        for timeframe, indicator_values in all_indicators.items():
            timeframe_indicators[timeframe] = calculate_indicators(
                market,
                indicator_values,
            )

        return timeframe_indicators

    def calculate_trade(self, timeframe_indicators):

        from scanner.mtf import calculate_mtf_score

        if timeframe_indicators is None:
            return None

        buy_score = calculate_mtf_score(
            timeframe_indicators,
            "BUY",
        )

        sell_score = calculate_mtf_score(
            timeframe_indicators,
            "SELL",
        )

        if sell_score["confidence"] > buy_score["confidence"]:
            score_result = sell_score
        else:
            score_result = buy_score

        indicators = timeframe_indicators.get("1m")

        if indicators is None:
            return None

        # Production ATR stop-loss uses the closed 5m ATR.
        # Entry/MTF signal logic remains unchanged.
        atr_5m = timeframe_indicators.get("5m", {}).get("atr")

        if atr_5m is not None:
            indicators = dict(indicators)
            indicators["atr"] = atr_5m

        return evaluate_trade(
            indicators,
            score_result,
        )


    def process_completed_market(self, market):

        event = update_trade(
            market["symbol"],
            market["ltp"],
        )

        if event:
            print()
            print("=" * 82)

            if event["event"] == "TARGET_1_HIT":
                self.session_stats["target1"] += 1
                print("🏆🏆 TARGET 1 HIT")
                print(f"💰 Profit Booked : ₹{event['pnl']:,.2f}")

            elif event["event"] == "TARGET_2_HIT":
                self.session_stats["target2"] += 1
                print("🥈🥈 TARGET 2 HIT")
                print(f"💰 Profit Booked : ₹{event['pnl']:,.2f}")

            elif event["event"] == "TARGET_3_HIT":
                self.session_stats["target3"] += 1
                self.session_stats["wins"] += 1
                self.session_stats["gross_profit"] += event["pnl"]
                self.session_stats["active"] -= 1
                print("👑👑👑 TARGET 3 ACHIEVED")
                print(f"💰 Final Profit : ₹{event['pnl']:,.2f}")
                print()
                print("🟢🟢✅✅ TRADE CLOSED (PROFIT)")
                print()

            elif event["event"] == "STOP_LOSS_HIT":
                self.session_stats["stoploss"] += 1
                self.session_stats["losses"] += 1
                self.session_stats["gross_loss"] += abs(event["pnl"])
                self.session_stats["active"] -= 1
                print("😭😭 STOP LOSS HIT")
                print(f"💸 Loss Booked : ₹{abs(event['pnl']):,.2f}")
                print()
                print("🔴🔴❌❌ TRADE CLOSED (LOSS)")
                print()

            print()
            print(f"🔢 Trade No. : {event['trade_number']}")
            print(f"📊 Stock     : {event['display_symbol']}")
            if event["event"] in ("TARGET_3_HIT", "STOP_LOSS_HIT"):
                print(f"🏁 Exit      : {event['exit_reason']}")
                print(f"⏱ Duration  : {event['duration']}")
            print(f"🕒 Time      : {datetime.now().strftime('%H:%M:%S')}")
            print("=" * 82)
            print()

        # Do not run the signal engine on every tick.
        # Open trades have already been checked above.
        if not market.get("_5m_closed", False):
            return

        indicators = self.calculate_indicators(market)

        if market["symbol"] == "NSE_INDEX|Nifty 50":
            MARKET_STATE["NIFTY"] = indicators
        elif market["symbol"] == "NSE_INDEX|Nifty Bank":
            MARKET_STATE["BANKNIFTY"] = indicators

        trade = self.calculate_trade(indicators)

        if trade is None:
            return

        confirmed = self.signal_state.confirm(
            trade["symbol"],
            trade["action"],
        )

        if confirmed is None:
            return

        trade["action"] = confirmed

        self.print_trade(trade)

        if (datetime.now() - self.last_summary).total_seconds() >= 600:
            self.print_session_summary()
            self.last_summary = datetime.now()


    def print_trade(self, trade, replay_mode=False, replay_timestamp=None):

        if trade is None:
            return

        if trade["grade"] == "IGNORE":
            return

        if replay_mode:

            self.trade_number += 1
            trade["trade_number"] = self.trade_number

            alert = {
                "generated_at": replay_timestamp,
            }

        else:
            alert = process_alert(trade)

            # If there is no alert, this trade is already active.
            # Don't print or rank it again.
            if alert is None:
                return

            self.trade_number += 1
            trade["trade_number"] = self.trade_number
            if not register_trade(trade):
                return

            self.session_stats["total"] += 1
            self.session_stats["active"] += 1

            if trade["action"] == "BUY":
                self.session_stats["buy"] += 1
            else:
                self.session_stats["sell"] += 1

            if trade["grade"] == "A+":
                self.session_stats["a_plus"] += 1
            elif trade["grade"] == "A":
                self.session_stats["a"] += 1

        #print(trade)

        ranking_trade = {
            "trade_number": trade["trade_number"],
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

        print("=" * 82)

        grade = trade["grade"]
        action = trade["action"]

        if action == "BUY":
            title = f"🟢🟢🟢 BUY SIGNAL ({grade})"
        else:
            title = f"🔴🔴🔴 SELL SIGNAL ({grade})"

        print(title)
        print(f"📊 Stock : {trade.get('display_symbol', trade['symbol'])}")
        print(f"🔢 Trade No.     : {trade['trade_number']}")

        print("=" * 82)

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
            print(f"📉 Per Share Risk : ₹{risk['per_share_risk']:.2f}")
            print(f"💼 Max Risk       : ₹2,000")
            print(f"📦 Recommended Qty: {risk['recommended_qty']}")
            print(f"💵 Position Value : ₹{risk['capital_required']:,.2f}")
            print(f"⚡ Margin Needed  : ₹{risk['capital_required']/5:,.2f} (5×)")
            print(f"📈 Expected Gain  : ₹{risk['reward']:.2f}/share")
            print()

            rr = risk["risk_reward"]

            if rr >= 2.0:
                quality = "🟢 EXCELLENT"
            elif rr >= 1.5:
                quality = "🟡 VERY GOOD"
            elif rr >= 1.0:
                quality = "🔵 GOOD"
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
            print(f"❌ Missing        : {' , '.join(trade['failed'])} | RVOL={trade.get('rvol')} | RSI={trade.get('rsi')}")

        status=[]
        for tf in ("1m","3m","5m","15m","30m","60m"):
            status.append(f"✓{tf}" if tf in trade.get("aligned_timeframes",[]) else f"✗{tf}")
        print("🕒 MTF : " + " ".join(status))

        if alert.get("generated_at"):
            print()
            print(f"🕒 Time           : {alert['generated_at']}")

        print("=" * 82)



    def on_message(self, message):

        market = self.process_market(message)

        if market is None:
            return

        self.process_completed_market(market)

    def on_error(self, *args):
        print("ERROR:", args)
        traceback.print_exc()

    def on_close(self, *args):
        print("Connection Closed")

    def start(self):
        print("Connecting...")
        self.streamer.connect()

    def print_session_summary(self, summary_time=None):
        closed = self.session_stats["wins"] + self.session_stats["losses"]

        win_rate = 0.0
        if closed > 0:
            win_rate = (self.session_stats["wins"] / closed) * 100

        print()
        print("=" * 78)
        print(f"📊 PAISAAI LIVE SESSION SUMMARY ({(summary_time or datetime.now()).strftime('%H:%M')})")
        print()
        print(f"📈 Total Trades Generated : {self.session_stats['total']}")
        print(f"🟢 Active Trades          : {self.session_stats['active']}")
        print()

        active = get_active_trades()

        if active:
            print("🟢 ACTIVE POSITIONS")
            for trade in sorted(active.values(), key=lambda x: x["trade_number"]):
                duration = datetime.now() - trade["opened_at"]
                mins = int(duration.total_seconds() // 60)
                secs = int(duration.total_seconds() % 60)

                print(
                    f"#{trade['trade_number']:02d} "
                    f"{trade['action']:<4} "
                    f"{trade['display_symbol']:<15} "
                    f"⏱ {mins:02d}m {secs:02d}s"
                )

            print()
        print(f"🏆 Target 1 Hit           : {self.session_stats['target1']}")
        print(f"🥈 Target 2 Hit           : {self.session_stats['target2']}")
        print(f"👑 Target 3 Hit           : {self.session_stats['target3']}")
        print(f"😭 Stop Loss Hit          : {self.session_stats['stoploss']}")
        print()
        print(f"📦 Closed Trades          : {closed}")
        print(f"🔥 Win Rate (Closed)      : {win_rate:.1f}%")
        net = self.session_stats["gross_profit"] - self.session_stats["gross_loss"]
        print(f"💰 Gross Profit          : ₹{self.session_stats['gross_profit']:,.2f}")
        print(f"💸 Gross Loss            : ₹{self.session_stats['gross_loss']:,.2f}")
        print(f"📊 Net P&L               : ₹{net:,.2f}")
        print()
        print(f"⭐ A+ Trades              : {self.session_stats['a_plus']}")
        print(f"🥇 A Trades               : {self.session_stats['a']}")
        print()
        print(f"📊 BUY Trades             : {self.session_stats['buy']}")
        print(f"📉 SELL Trades            : {self.session_stats['sell']}")
        print("=" * 78)
        print()

