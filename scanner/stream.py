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
from scanner.live_sentiment_shadow import run_shadow
from scanner.context_scoring import calculate_context_score
from scanner.market_depth import observe as observe_market_depth

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

    def calculate_trade(
        self,
        timeframe_indicators,
        market_depth=None,
    ):

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
            direction = "SELL"
        else:
            score_result = buy_score
            direction = "BUY"

        # ========================================================
        # CONTEXT SCORE
        # Technical MTF score remains the foundation.
        # Sentiment + Market Depth now contribute directionally.
        # ========================================================

        stock_indicators = (
            timeframe_indicators.get("5m", {})
        )

        nifty_indicators = (
            (MARKET_STATE.get("NIFTY") or {}).get(
                "5m",
                {},
            )
        )

        context = calculate_context_score(
            score_result.get("confidence", 0),
            direction,
            stock_indicators,
            nifty_indicators,
            market_depth,
        )

        score_result = dict(score_result)

        score_result["technical_confidence"] = (
            context["technical_confidence"]
        )

        score_result["confidence"] = (
            context["confidence"]
        )

        score_result["grade"] = (
            context["grade"]
        )

        score_result["context_score"] = context

        indicators = timeframe_indicators.get("1m")

        if indicators is None:
            return None

        # Production ATR stop-loss uses closed 5m ATR.
        atr_5m = timeframe_indicators.get("5m", {}).get("atr")

        if atr_5m is not None:
            indicators = dict(indicators)
            indicators["atr"] = atr_5m

        trade = evaluate_trade(
            indicators,
            score_result,
        )

        if trade is not None:
            trade["context_score"] = context

        return trade


    def process_completed_market(self, market):

        # ============================================================
        # MARKET DEPTH V1
        # Observation-only.
        # Replay has no live order-book data.
        # ============================================================
        if not market.get("_replay", False):

            depth = observe_market_depth(
                market.get("symbol"),
                market.get("bids", []),
                market.get("asks", []),
                datetime.now(),
            )

            if depth is not None:

                if depth["confirmed"]:

                    print(
                        f"   ✅ DEPTH CONFIRMED : "
                        f"{depth['confirmed']}"
                    )

        event = update_trade(
            market["symbol"],
            market["ltp"],
        )

        if event:
            active_after_event = get_active_trades().get(event["symbol"])
            protected_profit = 0.0
            if active_after_event and active_after_event.get("target2_hit"):
                protected_profit = active_after_event["risk"]["recommended_qty"] * abs(
                    active_after_event["target1"] - active_after_event["entry"]
                )
            print()
            print("=" * 82)

            if event["event"] == "TARGET_1_HIT":
                self.session_stats["target1"] += 1
                print("🏆🏆 TARGET 1 ACHIEVED")
                print(f"💰 Profit Level       : ₹{event['pnl']:,.2f}")
                print("🛡️ STOP LOSS MOVED    : ENTRY")
                print("🔒 Protected Minimum  : ₹0.00")
                print("🎯 Next Target        : TARGET 2")

            elif event["event"] == "TARGET_2_HIT":
                self.session_stats["target2"] += 1
                print("🥈🥈 TARGET 2 ACHIEVED")
                print(f"💰 Profit Level       : ₹{event['pnl']:,.2f}")
                print("🛡️ STOP LOSS MOVED    : TARGET 1")
                print(f"🔒 Protected Minimum  : ₹{protected_profit:,.2f}")
                print("🎯 Next Target        : TARGET 3")

            elif event["event"] == "TARGET_3_HIT":
                self.session_stats["target3"] += 1
                self.session_stats["wins"] += 1
                self.session_stats["gross_profit"] += event["pnl"]
                self.session_stats["active"] -= 1
                print("👑👑👑 TARGET 3 ACHIEVED")
                print(f"💰 Final Profit        : ₹{event['pnl']:,.2f}")
                print()
                print("🟢🟢✅✅ TRADE CLOSED (PROFIT)")
                print()

            elif event["event"] == "STOP_LOSS_HIT":
                self.session_stats["stoploss"] += 1
                self.session_stats["losses"] += 1
                self.session_stats["gross_loss"] += abs(event["pnl"])
                self.session_stats["active"] -= 1
                print("😭😭 STOP LOSS HIT")
                print(f"💸 Loss Booked        : ₹{abs(event['pnl']):,.2f}")
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

        trade = self.calculate_trade(
            indicators,
            market_depth=depth,
        )

        if trade is None:
            return

        confirmed = self.signal_state.confirm(
            trade["symbol"],
            trade["action"],
        )

        if confirmed is None:
            return

        trade["action"] = confirmed

        # GOLDEN1 shadow remains observation-only.
        # Use the stock's CLOSED 5m indicators for sentiment.
        # NIFTY may not be ready yet, so safely use an empty dict.
        stock_sentiment_indicators = indicators.get("5m", {}) or {}
        nifty_sentiment_indicators = (
            (MARKET_STATE.get("NIFTY") or {}).get("5m", {}) or {}
        )

        self.print_trade(
            trade,
            shadow_inputs=(
                stock_sentiment_indicators,
                nifty_sentiment_indicators,
            ),
        )

        if (datetime.now() - self.last_summary).total_seconds() >= 600:
            self.print_session_summary()
            self.last_summary = datetime.now()


    def print_trade(
        self,
        trade,
        replay_mode=False,
        replay_timestamp=None,
        shadow_inputs=None,
        preserve_trade_number=False,
    ):

        if trade is None:
            return

        if trade["grade"] == "IGNORE":
            return

        if replay_mode:

            if not preserve_trade_number:

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

            # ========================================================
            # GOLDEN1 SHADOW SENTIMENT
            # Calculation is unchanged.
            #
            # It runs ONLY after the production trade is accepted.
            # Therefore duplicate/rejected candidates create no
            # shadow-sentiment noise.
            # ========================================================
            if shadow_inputs is not None:
                stock_indicators, nifty_indicators = shadow_inputs

                try:
                    shadow = run_shadow(
                        trade["symbol"],
                        trade,
                        stock_indicators or {},
                        nifty_indicators or {},
                    )

                    trade["shadow_sentiment"] = shadow

                except Exception as e:
                    print(
                        f"⚠️ SHADOW SENTIMENT ERROR: "
                        f"{type(e).__name__}: {e}"
                    )
                    trade["shadow_sentiment"] = None

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

        shadow = trade.get("shadow_sentiment")

        if shadow:
            print(
                f"🧠 SHADOW SENTIMENT : "
                f"{shadow['sentiment']} "
                f"| Score {shadow['score']:+d} "
                f"| Confidence {shadow['confidence']}%"
            )

            if shadow.get("reasons"):
                print(
                    "   └─ "
                    + " | ".join(shadow["reasons"])
                )

        depth = trade.get("market_depth")

        if depth:
            state = depth.get("state", "UNKNOWN")
            buy_qty = depth.get("buy_qty", 0)
            sell_qty = depth.get("sell_qty", 0)
            ratio = depth.get("ratio", 1.0)
            persistence = depth.get("persistence", 0)
            confirmed = depth.get("confirmed") or "NO"
            source = depth.get("source", "LIVE")

            if ratio == float("inf"):
                ratio_text = "INF"
            else:
                ratio_text = f"{ratio:.2f}"

            print("📚 MARKET DEPTH")
            print(f"   State       : {state}")
            print(f"   BUY Qty     : {buy_qty:,}")
            print(f"   SELL Qty    : {sell_qty:,}")
            print(f"   Ratio       : {ratio_text}")
            print(f"   Persistence : {persistence}/10")
            print(f"   Confirmed   : {confirmed}")
            print(f"   Source      : {source}")

        else:
            print("📚 MARKET DEPTH     : NO SAMPLE")

        print("🛡️ DYNAMIC SL      : ACTIVE")
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

        context = trade.get("context_score")

        if context:
            print(
                f"🧮 SCORE MIX       : "
                f"Technical {context['technical_confidence']} "
                f"| Sentiment {context['sentiment_adjustment']:+d} "
                f"| Depth {context['depth_adjustment']:+d}"
            )

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
            print("🟢 ACTIVE POSITIONS / DYNAMIC SL")
            protected_total = 0.0
            t1_protected = 0
            t2_protected = 0

            for trade in sorted(active.values(), key=lambda x: x["trade_number"]):
                duration = datetime.now() - trade["opened_at"]
                mins = int(duration.total_seconds() // 60)
                secs = int(duration.total_seconds() % 60)

                risk = trade["risk"]
                qty = risk["recommended_qty"]
                entry = trade["entry"]
                target1 = trade["target1"]
                stop_loss = trade["stop_loss"]

                if trade["target2_hit"]:
                    sl_state = "TARGET 1"
                    protected = qty * abs(target1 - entry)
                    t2_protected += 1
                elif trade["target1_hit"]:
                    sl_state = "ENTRY"
                    protected = 0.0
                    t1_protected += 1
                else:
                    sl_state = "ORIGINAL"
                    protected = 0.0

                protected_total += protected

                print(
                    f"#{trade['trade_number']:02d} "
                    f"{trade['action']:<4} "
                    f"{trade['display_symbol']:<15} "
                    f"SL → {sl_state:<8} "
                    f"₹{stop_loss:,.2f} "
                    f"⏱ {mins:02d}m {secs:02d}s"
                )

            print()
            print("🛡️ DYNAMIC STOP LOSS STATUS")
            print(f"🏆 T1 reached / SL → ENTRY    : {t1_protected}")
            print(f"🥈 T2 reached / SL → TARGET 1 : {t2_protected}")
            print(f"🔒 Protected Minimum Profit    : ₹{protected_total:,.2f}")
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

