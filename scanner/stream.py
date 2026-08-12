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
from scanner.live_context import (
    get_nifty_context,
    get_sector_change,
    update_live_context,
)
from scanner.institutional_flow import (
    get_flow_for_timestamp,
    refresh_live,
)
from scanner.market_depth import update as update_market_depth
from scanner.nse_context import get_market_depth as get_nse_market_depth

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


def print_engine_breakdown(context):
    """
    Professional engine-by-engine score display.

    IMPORTANT:
    This function is DISPLAY ONLY.
    It does not modify scoring, confidence, grade,
    trade selection, or risk management.
    """

    context = context or {}

    technical = context.get(
        "technical_confidence",
        0,
    )

    sentiment_raw = context.get(
        "sentiment_raw_score",
        context.get("sentiment_score", 0),
    )

    sentiment_adjustment = context.get(
        "sentiment_adjustment",
        0,
    )

    sentiment = context.get(
        "sentiment",
        {},
    ) or {}

    sentiment_label = (
        sentiment.get("sentiment")
        or sentiment.get("label")
        or sentiment.get("direction")
        or "N/A"
    )

    depth_confirmed = (
        context.get("depth_confirmed")
        or "UNCONFIRMED"
    )

    depth_adjustment = context.get(
        "depth_adjustment",
        0,
    )

    relative = context.get(
        "relative_strength",
        {},
    ) or {}

    relative_raw = relative.get(
        "relative_strength",
        relative.get("score", 0),
    )

    relative_rating = (
        relative.get("strength")
        or relative.get("rating")
        or "N/A"
    )

    relative_adjustment = context.get(
        "relative_strength_adjustment",
        0,
    )

    sector = context.get(
        "sector_strength",
        {},
    ) or {}

    sector_raw = sector.get(
        "sector_strength",
        sector.get("score", 0),
    )

    sector_rating = (
        sector.get("rating")
        or sector.get("strength")
        or "N/A"
    )

    sector_adjustment = context.get(
        "sector_adjustment",
        0,
    )

    institutional = context.get(
        "institutional",
        {},
    ) or {}

    fii_net = institutional.get(
        "fii_net",
        0,
    )

    dii_net = institutional.get(
        "dii_net",
        0,
    )

    institutional_adjustment = context.get(
        "institutional_adjustment",
        institutional.get("adjustment", 0),
    )

    fii_available = institutional.get(
        "available",
        False,
    )

    fii_date = institutional.get(
        "date",
        "N/A",
    )

    fii_source = institutional.get(
        "source",
        "N/A",
    )

    final_confidence = context.get(
        "confidence",
        0,
    )

    final_grade = context.get(
        "grade",
        "N/A",
    )

    print()
    print("🧠 ENGINE SCORE BREAKDOWN")
    print("─" * 82)

    print(
        f"📊 Technical MTF     : "
        f"{technical} "
        f"(foundation)"
    )

    print(
        f"📰 Sentiment         : "
        f"{sentiment_raw:+} "
        f"→ {sentiment_adjustment:+d} "
        f"[{sentiment_label}]"
    )

    print(
        f"📚 Market Depth      : "
        f"{depth_confirmed} "
        f"→ {depth_adjustment:+d}"
    )

    print(
        f"📈 Relative Strength : "
        f"{relative_raw} "
        f"[{relative_rating}] "
        f"→ {relative_adjustment:+d}"
    )

    print(
        f"🏭 Sector Strength   : "
        f"{sector_raw} "
        f"[{sector_rating}] "
        f"→ {sector_adjustment:+d}"
    )

    if fii_available:
        print(
            f"🏦 FII/DII           : "
            f"FII {fii_net:,.2f} | "
            f"DII {dii_net:,.2f} "
            f"→ {institutional_adjustment:+d}"
        )
        print(
            f"   └─ Date: {fii_date} | "
            f"Source: {fii_source}"
        )
    else:
        print(
            f"🏦 FII/DII           : "
            f"UNAVAILABLE "
            f"→ {institutional_adjustment:+d}"
        )

    print("─" * 82)

    print(
        f"🎯 FINAL CONFIDENCE  : "
        f"{final_confidence}%"
    )

    print(
        f"🏅 FINAL GRADE       : "
        f"{final_grade}"
    )

    print("─" * 82)


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
            "protected_stop": 0,
            "breakeven": 0,
            "wins": 0,
            "losses": 0,
            "gross_profit": 0.0,
            "gross_loss": 0.0,
        }
        self.signal_state = SignalState()

        # Live market-depth sampling is observation-only.
        # Persist one depth observation per symbol per minute so the
        # 10-observation confirmation rule is not advanced by every tick.
        self._depth_snapshots = {}
        self._depth_last_sample = {}


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

        # Context market state is updated on every tick so RS/Sector inputs
        # do not depend on websocket message ordering or a simultaneous 5m
        # close. This is observation-only and does not touch trade management.
        update_live_context(market)

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
        market_timestamp=None,
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
        # UNIFIED CONTEXT SCORE
        # Technical MTF remains the foundation.
        # Sentiment + Depth + Relative Strength + Sector Strength
        # + FII/DII contribute through the same consolidated path
        # used by Replay.
        # ========================================================

        stock_indicators = (
            timeframe_indicators.get("5m", {})
        )

        nifty_indicators = get_nifty_context(
            (MARKET_STATE.get("NIFTY") or {}).get(
                "5m",
                {},
            )
        )

        # --------------------------------------------------------
        # SECTOR STRENGTH
        # --------------------------------------------------------
        sector_change = get_sector_change(
            stock_indicators.get("symbol"),
            explicit_change=stock_indicators.get("sector_change"),
            explicit_sector=stock_indicators.get("sector"),
        )

        # --------------------------------------------------------
        # FII / DII
        # --------------------------------------------------------
        institutional_flow = (
            get_flow_for_timestamp(
                market_timestamp
            )
        )

        if institutional_flow is None:
            institutional_flow = (
                MARKET_STATE.get(
                    "INSTITUTIONAL_FLOW"
                )
            )

        context = calculate_context_score(
            score_result.get("confidence", 0),
            direction,
            stock_indicators,
            nifty_indicators,
            market_depth,
            sector_change=sector_change,
            institutional_flow=institutional_flow,
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

        # Production ATR stop-loss remains unchanged:
        # use the closed 5m ATR for the trade risk layer.
        atr_5m = timeframe_indicators.get(
            "5m",
            {},
        ).get("atr")

        if atr_5m is not None:
            indicators = dict(indicators)
            indicators["atr"] = atr_5m

        trade = evaluate_trade(
            indicators,
            score_result,
        )

        if trade is not None:
            trade["context_score"] = context

            if market_depth is not None:
                trade["market_depth"] = market_depth

        return trade


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
                print("🏆🏆 TARGET 1 ACHIEVED")
                print("🛡️ STOP LOSS MOVED    : ENTRY")
                print("🔒 Protected Minimum  : ₹0.00")
                print("🎯 Next Target        : TARGET 2")
                print("ℹ️ P&L                : NOT REALIZED — TARGET 1 IS A MILESTONE")

            elif event["event"] == "TARGET_2_HIT":
                self.session_stats["target2"] += 1
                print("🥈🥈 TARGET 2 ACHIEVED")
                print("🛡️ STOP LOSS MOVED    : TARGET 1")
                print("🎯 Next Target        : TARGET 3")
                print("ℹ️ P&L                : NOT REALIZED — TARGET 2 IS A MILESTONE")

            elif event["event"] == "TARGET_3_HIT":
                realized = event["realized_pnl"]
                self.session_stats["target3"] += 1
                self.session_stats["wins"] += 1
                self.session_stats["gross_profit"] += max(realized, 0.0)
                self.session_stats["gross_loss"] += abs(min(realized, 0.0))
                self.session_stats["active"] -= 1
                print("👑👑👑 TARGET 3 ACHIEVED")
                print(f"💰 FINAL REALIZED PROFIT : ₹{realized:,.2f}")
                print()
                print("🟢🟢✅✅ TRADE CLOSED (PROFIT)")
                print()

            elif event["event"] == "PROTECTED_STOP_HIT":
                realized = event["realized_pnl"]
                self.session_stats["protected_stop"] += 1
                self.session_stats["active"] -= 1

                if realized > 0:
                    self.session_stats["wins"] += 1
                    self.session_stats["gross_profit"] += realized
                    print("🛡️🛡️ PROTECTED STOP HIT")
                    print(f"💰 REALIZED PROTECTED PROFIT : ₹{realized:,.2f}")
                    print(f"🏁 EXIT                     : {event['exit_reason']}")
                    print("🟢🟢✅✅ TRADE CLOSED (PROFIT)")
                elif realized == 0:
                    self.session_stats["breakeven"] += 1
                    print("🛡️🛡️ PROTECTED STOP HIT")
                    print("💰 REALIZED P&L             : ₹0.00")
                    print(f"🏁 EXIT                     : {event['exit_reason']}")
                    print("⚪⚪ TRADE CLOSED (BREAKEVEN)")
                else:
                    # Defensive branch: protected stops should never create
                    # a loss under the validated Dynamic-SL rules.
                    self.session_stats["losses"] += 1
                    self.session_stats["gross_loss"] += abs(realized)
                    print("⚠️ PROTECTED STOP PRODUCED NEGATIVE P&L")
                    print(f"💸 REALIZED LOSS             : ₹{abs(realized):,.2f}")
                    print(f"🏁 EXIT                     : {event['exit_reason']}")
                    print("🔴🔴❌❌ TRADE CLOSED (LOSS)")

            elif event["event"] == "STOP_LOSS_HIT":
                realized = event["realized_pnl"]
                self.session_stats["stoploss"] += 1
                self.session_stats["active"] -= 1

                if realized < 0:
                    self.session_stats["losses"] += 1
                    self.session_stats["gross_loss"] += abs(realized)
                    print("😭😭 ORIGINAL STOP LOSS HIT")
                    print(f"💸 REALIZED LOSS            : ₹{abs(realized):,.2f}")
                    print("🏁 EXIT                     : ORIGINAL STOP LOSS")
                    print("🔴🔴❌❌ TRADE CLOSED (LOSS)")
                elif realized == 0:
                    self.session_stats["breakeven"] += 1
                    print("⚪⚪ ORIGINAL STOP AT ENTRY")
                    print("💰 REALIZED P&L             : ₹0.00")
                    print("⚪⚪ TRADE CLOSED (BREAKEVEN)")
                else:
                    self.session_stats["wins"] += 1
                    self.session_stats["gross_profit"] += realized
                    print("⚠️ ORIGINAL STOP PRODUCED POSITIVE P&L")
                    print(f"💰 REALIZED PROFIT          : ₹{realized:,.2f}")
                    print("🟢🟢 TRADE CLOSED (PROFIT)")

            print()
            print(f"🔢 Trade No. : {event['trade_number']}")
            print(f"📊 Stock     : {event['display_symbol']}")
            if event["event"] in ("TARGET_3_HIT", "STOP_LOSS_HIT", "PROTECTED_STOP_HIT"):
                print(f"🏁 Exit      : {event['exit_reason']}")
                print(f"💵 Exit Price : ₹{event['exit_price']:,.2f}")
                print(f"💵 Realized P&L : ₹{event['realized_pnl']:,.2f}")
                print(f"⏱ Duration  : {event['duration']}")
            print(f"🕒 Time      : {datetime.now().strftime('%H:%M:%S')}")
            print("=" * 82)
            print()

        # ========================================================
        # MARKET DEPTH — LIVE OBSERVATION
        # One sample per symbol per minute. This preserves the
        # market_depth.py persistence semantics instead of counting
        # every websocket tick as a new observation.
        # ========================================================
        symbol = market["symbol"]
        now = datetime.now()
        sample_key = now.replace(
            second=0,
            microsecond=0,
        )

        if self._depth_last_sample.get(symbol) != sample_key:
            # NSE is preferred, but its equity-depth endpoint may return
            # HTTP 403. Never discard a usable Upstox side of the book.
            upstox_bids = market.get("bids", [])
            upstox_asks = market.get("asks", [])

            bids = upstox_bids
            asks = upstox_asks
            depth_source = "UPSTOX"

            # Try NSE only when the live Upstox book is incomplete.
            if not (bids and asks):
                nse_depth = get_nse_market_depth(symbol)

                if nse_depth:
                    nse_bids = nse_depth.get("bids", [])
                    nse_asks = nse_depth.get("asks", [])

                    # Prefer a complete NSE book.
                    if nse_bids and nse_asks:
                        bids = nse_bids
                        asks = nse_asks
                        depth_source = "NSE"
                    else:
                        # Preserve any usable Upstox side.
                        bids = upstox_bids or nse_bids
                        asks = upstox_asks or nse_asks
                        depth_source = (
                            "UPSTOX"
                            if upstox_bids or upstox_asks
                            else "NSE"
                        )

            depth = update_market_depth(
                symbol,
                bids,
                asks,
                now,
            )

            if depth:
                depth["source"] = depth_source
            self._depth_snapshots[symbol] = depth
            self._depth_last_sample[symbol] = sample_key

            if depth.get("confirmed"):
                print(
                    f"   ✅ DEPTH CONFIRMED : "
                    f"{depth['confirmed']}"
                )

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
            market_depth=self._depth_snapshots.get(
                market["symbol"]
            ),
            market_timestamp=market.get(
                "timestamp"
            ) or datetime.now().isoformat(),
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
    ):

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
            print_engine_breakdown(context)

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

        print()
        print("=" * 78)
        print("🏦 LOADING FII / DII INSTITUTIONAL FLOW")
        print("=" * 78)

        institutional = refresh_live()

        if institutional:

            fii = institutional.get("fii") or {}
            dii = institutional.get("dii") or {}

            print(
                f"FII Net : ₹{fii.get('net', 0):,.2f} Cr"
            )

            print(
                f"DII Net : ₹{dii.get('net', 0):,.2f} Cr"
            )

            print(
                f"Date    : {institutional.get('date')}"
            )

            print(
                f"Source  : {institutional.get('source', 'NSE')}"
            )

        else:
            print(
                "⚠️ FII/DII unavailable — "
                "institutional contribution will remain neutral."
            )

        print("Connecting...")
        self.streamer.connect()

    def print_session_summary(self, summary_time=None):
        closed = (
            self.session_stats["wins"]
            + self.session_stats["losses"]
            + self.session_stats["breakeven"]
        )

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
        print(f"😭 Original Stop Loss     : {self.session_stats['stoploss']}")
        print(f"🛡️ Protected Stop Hit     : {self.session_stats['protected_stop']}")
        print(f"⚪ Breakeven Trades        : {self.session_stats['breakeven']}")
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

