"""
PaisaAI Replay Engine V2

Replay-only execution path.

IMPORTANT:
Production trade management is NEVER used here.

Replay uses a private historical warm-up phase so the MTF indicator
engine has enough 1m/3m/5m/15m/30m/60m history before the actual
replay window begins.
"""

import config
import upstox_client
import os

from datetime import date, datetime

from data.candles import (
    clear_symbol,
    update_tick,
)

from scanner.stream import LiveStreamer
from scanner.replay_strategy import (
    STOPLOSS_MODE,
    PRINT_STRATEGY,
)
from scanner.replay_trade_manager import (
    register_trade,
    update_trade,
    reset as reset_replay_trades,
)

from scanner.live_sentiment_shadow import run_shadow
from scanner.runtime import MARKET_STATE
from scanner.strategy_manager import manager
from scanner.market_depth import (
    reset as reset_market_depth,
    update as update_market_depth,
)
from scanner.replay_depth import build_snapshot as build_replay_depth


# ---------------------------------------------------------------------------
# Replay-only historical API client.
# Production streaming/API objects are not modified.
# ---------------------------------------------------------------------------

_configuration = upstox_client.Configuration()
_configuration.access_token = config.ACCESS_TOKEN
_api_client = upstox_client.ApiClient(_configuration)
_history_api = upstox_client.HistoryApi(_api_client)


class ReplayFeed:

    def __init__(self, speed=1.0):
        self.speed = speed

        # Build a LiveStreamer object so Replay uses the same indicator,
        # MTF and decision pipeline.
        #
        # No live connection is started.
        self.streamer = LiveStreamer(risk_mode="replay")

        self.trade_number = 0
        self.active_strategy = STOPLOSS_MODE.upper()

        # Replay session statistics mirror the production summary.
        # Global replay summary cadence.
        # Summaries are based on replay time, not per-symbol candle count.
        self._last_summary_timestamp = None

        self.session_stats = {
            "total": 0,
            "active": 0,
            "target1": 0,
            "target2": 0,
            "target3": 0,
            "stoploss": 0,
            "wins": 0,
            "losses": 0,
            "gross_profit": 0.0,
            "gross_loss": 0.0,
            "depth_confirmed_buy": 0,
            "depth_confirmed_sell": 0,
            "sentiment_snapshots": 0,
        }

    def _next_trade_number(self):
        self.trade_number += 1
        return self.trade_number

    def _process_exit(self, strategy, symbol, price, timestamp=None):

        event = update_trade(
            strategy,
            symbol,
            price,
            timestamp,
        )

        if event is None:
            return

        if event["event"] == "TARGET_1_HIT":
            self.session_stats["target1"] += 1
            print()
            print("=" * 82)
            print("🏆🏆 TARGET 1 ACHIEVED")
            print(f"💰 Profit Level       : ₹{event['pnl']:,.2f}")
            print("🛡️ STOP LOSS MOVED    : ENTRY")
            print("🔒 Protected Minimum  : ₹0.00")
            print("🎯 Next Target        : TARGET 2")

        elif event["event"] == "TARGET_2_HIT":
            self.session_stats["target2"] += 1
            print()
            print("=" * 82)
            print("🥈🥈 TARGET 2 ACHIEVED")
            print(f"💰 Profit Level       : ₹{event['pnl']:,.2f}")
            print("🛡️ STOP LOSS MOVED    : TARGET 1")
            print("🎯 Next Target        : TARGET 3")

        elif event["event"] == "TARGET_3_HIT":
            self.session_stats["target3"] += 1
            self.session_stats["wins"] += 1
            self.session_stats["gross_profit"] += event["pnl"]
            self.session_stats["active"] = max(
                0, self.session_stats["active"] - 1
            )
            manager.register_win(strategy, event["pnl"])
            print()
            print("=" * 82)
            print("👑👑👑 TARGET 3 ACHIEVED")
            print(f"💰 Final Profit        : ₹{event['pnl']:,.2f}")
            print("🟢🟢✅✅ TRADE CLOSED (PROFIT)")

        elif event["event"] == "STOP_LOSS_HIT":
            self.session_stats["stoploss"] += 1
            self.session_stats["losses"] += 1
            self.session_stats["gross_loss"] += abs(event["pnl"])
            self.session_stats["active"] = max(
                0, self.session_stats["active"] - 1
            )
            manager.register_loss(strategy, event["pnl"])
            print()
            print("=" * 82)
            print("😭😭 STOP LOSS HIT")
            print(f"💸 Loss Booked        : ₹{abs(event['pnl']):,.2f}")
            print("🔴🔴❌❌ TRADE CLOSED (LOSS)")

        else:
            return

        print(f"🔢 Trade No. : {event['trade_number']}")
        print(f"📊 Stock     : {event['display_symbol']}")

        if event["event"] in ("TARGET_3_HIT", "STOP_LOSS_HIT"):
            print(f"🏁 Exit      : {event['exit_reason']}")
            print(f"⏱ Duration  : {event['duration']}")

        print(f"🕒 Time      : {timestamp}")
        print("=" * 82)
        print()

    def _build_market(
        self,
        symbol,
        candle,
        five_minute_closed,
    ):

        return {
            "symbol": symbol,
            "ltp": candle["close"],
            "previous_close": candle["open"],
            "open": candle["open"],
            "high": candle["high"],
            "low": candle["low"],
            "close": candle["close"],
            "volume": candle.get("volume", 0),
            "timestamp": candle.get("timestamp"),

            # Replay-only marker.
            "_replay": True,

            # Authoritative signal gate.
            "_5m_closed": five_minute_closed,

            # Same five-level depth engine as production. Historical OHLCV
            # has no real order book, so the adapter uses supplied depth when
            # available and otherwise a clearly marked deterministic proxy.
            "bids": candle.get("bids", []),
            "asks": candle.get("asks", []),
            "_depth_replay": True,
        }

    def _fetch_historical_candles(self, symbol):

        """
        Fetch the complete 1-minute historical set directly from Upstox.

        This deliberately bypasses data.preload.preload_history(),
        because the shared candle store keeps only MAX_CANDLES entries.

        Replay needs the older candles for indicator warm-up before the
        actual replay window starts.
        """

        try:

            response = _history_api.get_historical_candle_data(
                symbol,
                "1minute",
                date.today().strftime("%Y-%m-%d"),
                "2.0",
            )

            raw_candles = list(response.data.candles)

            # Upstox returns newest -> oldest.
            raw_candles.reverse()

            candles = []

            for c in raw_candles:

                candles.append(
                    {
                        "timestamp": c[0],
                        "open": c[1],
                        "high": c[2],
                        "low": c[3],
                        "close": c[4],
                        "volume": c[5],
                    }
                )

            return candles

        except Exception as exc:

            print(
                f"❌ Replay history fetch failed for "
                f"{symbol}: {exc}"
            )

            return []

    @staticmethod
    def _as_datetime(timestamp):
        if isinstance(timestamp, datetime):
            return timestamp
        if timestamp is None:
            return datetime.now()
        try:
            return datetime.fromisoformat(
                str(timestamp).replace("Z", "+00:00")
            )
        except ValueError:
            return datetime.now()

    def _print_replay_summary(self, symbol, replay_timestamp):
        """Print only high-level replay/session KPIs.

        Detailed trading-state information belongs to the professional
        trade banner or event banner, not to the recurring summary.

        ``symbol`` is intentionally accepted for call-site compatibility,
        but is not displayed here.
        """
        del symbol

        s = self.session_stats
        closed = s["wins"] + s["losses"]
        win_rate = (s["wins"] / closed) * 100 if closed else 0.0
        net = s["gross_profit"] - s["gross_loss"]

        print()
        print("=" * 82)
        print(
            f"📊 PAISAAI REPLAY SESSION SUMMARY "
            f"({str(replay_timestamp)[:19]})"
        )
        print()
        print(f"📈 Total Trades Generated : {s['total']}")
        print(f"🟢 Active Trades          : {s['active']}")
        print(f"🏆 Target 1 Hits          : {s['target1']}")
        print(f"🥈 Target 2 Hits          : {s['target2']}")
        print(f"👑 Target 3 Hits          : {s['target3']}")
        print(f"🛑 Stop Loss Hits         : {s['stoploss']}")
        print(f"📊 Closed Trades          : {closed}")
        print(f"🎯 Win Rate               : {win_rate:.1f}%")
        print(f"💰 Gross Profit           : ₹{s['gross_profit']:,.2f}")
        print(f"💸 Gross Loss             : ₹{s['gross_loss']:,.2f}")
        print(f"💵 Net P&L                : ₹{net:,.2f}")
        print("=" * 82)
        print()

    def replay_symbol(self, symbol):

        # ------------------------------------------------------------------
        # Fetch the complete historical set BEFORE touching the runtime
        # candle store.
        #
        # This gives Replay:
        #
        #     historical warm-up
        #             +
        #     actual replay window
        #
        # without future leakage.
        # ------------------------------------------------------------------

        all_candles = self._fetch_historical_candles(
            symbol
        )

        if not all_candles:
            return 0

        # Full Replay is now the default. Keep a dedicated historical
        # warm-up section so MTF indicators are established before the
        # first tradeable replay candle. A finite replay can still be
        # requested explicitly with REPLAY_CANDLE_LIMIT for diagnostics.
        warmup_target = max(
            0,
            int(os.getenv("REPLAY_WARMUP_CANDLES", "500"))
        )
        candle_limit = max(
            0,
            int(os.getenv("REPLAY_CANDLE_LIMIT", "0"))
        )

        if candle_limit > 0:
            replay_count = min(candle_limit, len(all_candles))
            warmup_candles = all_candles[:-replay_count]
            replay_candles = all_candles[-replay_count:]
        else:
            warmup_count = min(
                warmup_target,
                max(0, len(all_candles) - 1)
            )
            warmup_candles = all_candles[:warmup_count]
            replay_candles = all_candles[warmup_count:]

        if len(replay_candles) < 2:
            return 0

        # ------------------------------------------------------------------
        # Start Replay from a clean symbol/depth/trade state.
        # ------------------------------------------------------------------

        clear_symbol(symbol)
        reset_market_depth(symbol)
        reset_replay_trades(strategy=self.active_strategy, symbol=symbol)

        # ------------------------------------------------------------------
        # INDICATOR WARM-UP
        #
        # No signals.
        # No trades.
        # No exits.
        #
        # These candles exist only to establish proper historical state
        # for all MTF indicators.
        # ------------------------------------------------------------------

        for candle in warmup_candles:

            update_tick(
                symbol=symbol,
                price=candle["close"],
                volume=candle.get("volume", 0),
                timestamp=candle["timestamp"],
            )

        print(
            f"🧠 Replay warm-up : "
            f"{len(warmup_candles)} candles"
        )

        print(
            f"🎬 Replay window  : "
            f"{len(replay_candles)} candles"
        )

        processed = 0
        strategy = self.active_strategy

        # ------------------------------------------------------------------
        # ACTUAL REPLAY WINDOW
        # ------------------------------------------------------------------

        for candle in replay_candles:

            candle_update = update_tick(
                symbol=symbol,
                price=candle["close"],
                volume=candle.get("volume", 0),
                timestamp=candle["timestamp"],
            )

            # --------------------------------------------------------------
            # EXIT MONITORING
            #
            # Open trades are checked on every historical candle.
            # This mirrors production's every-tick exit monitoring.
            # --------------------------------------------------------------

            self._process_exit(
                strategy,
                symbol,
                candle["close"],
                candle.get("timestamp"),
            )

            # --------------------------------------------------------------
            # AUTHORITATIVE 5M SIGNAL GATE
            # --------------------------------------------------------------

            five_minute_closed = False

            if candle_update is not None:

                closed_timeframes = candle_update.get(
                    "closed_timeframes",
                    [],
                )

                five_minute_closed = (
                    "5m" in closed_timeframes
                )

            depth_bids, depth_asks, synthetic_depth = build_replay_depth(candle)

            replay_candle = dict(candle)
            replay_candle["bids"] = depth_bids
            replay_candle["asks"] = depth_asks

            market = self._build_market(
                symbol,
                replay_candle,
                five_minute_closed,
            )

            depth = update_market_depth(
                symbol,
                depth_bids,
                depth_asks,
                self._as_datetime(candle.get("timestamp")),
            )

            if synthetic_depth:
                market["_depth_synthetic"] = True
                depth["source"] = "SYNTHETIC"
            else:
                depth["source"] = "HISTORICAL"

            if depth["confirmed"]:
                source = "SYNTHETIC" if synthetic_depth else "HISTORICAL"
                if depth["confirmed"] == "BUY":
                    self.session_stats["depth_confirmed_buy"] += 1
                elif depth["confirmed"] == "SELL":
                    self.session_stats["depth_confirmed_sell"] += 1
                # Depth is attached to an opened trade and displayed
                # inside the professional trade banner.

            # --------------------------------------------------------------
            # SIGNAL GENERATION
            # --------------------------------------------------------------

            if five_minute_closed:

                timeframe_indicators = (
                    self.streamer.calculate_indicators(
                        market
                    )
                )

                trade = self.streamer.calculate_trade(
                    timeframe_indicators,
                    market_depth=depth,
                    market_timestamp=candle.get(
                        "timestamp"
                    ),
                )

                if trade is not None:
                    trade["market_depth"] = depth

                if trade is not None:
                    # Preserve the full Replay depth result for the
                    # professional trade banner.
                    trade["market_depth"] = depth

                # Replay shadow is observation-only and is displayed ONLY
                # when a real Replay trade is actually opened. This keeps the
                # shadow directly above the professional trade banner instead
                # of printing it on every candidate candle.

                if trade is not None:

                    # Retain production SignalState confirmation logic.
                    confirmed = (
                        self.streamer.signal_state.confirm(
                            trade["symbol"],
                            trade["action"],
                        )
                    )

                    if confirmed is not None:

                        trade["action"] = confirmed

                        # Replay requires valid risk.
                        if trade.get("risk") is not None:

                            trade["trade_number"] = (
                                self._next_trade_number()
                            )

                            opened_at = None
                            if candle.get("timestamp"):
                                try:
                                    opened_at = datetime.fromisoformat(
                                        str(candle["timestamp"]).replace("Z", "+00:00")
                                    )
                                except ValueError:
                                    opened_at = None

                            registered = register_trade(
                                strategy,
                                trade,
                                opened_at=opened_at,
                            )

                            if registered:

                                self.session_stats["total"] += 1
                                self.session_stats["active"] += 1

                                manager.register_trade(
                                    strategy
                                )

                                # ======================================================
                                # REPLAY SHADOW SENTIMENT
                                # ======================================================
                                # Observation only.
                                # Printed once, immediately before the actual trade
                                # banner. It never changes the trade decision.
                                # ======================================================
                                stock_sentiment_indicators = (
                                    timeframe_indicators.get("5m", {})
                                    if isinstance(timeframe_indicators, dict)
                                    else {}
                                )

                                if symbol == "NSE_INDEX|Nifty 50":
                                    MARKET_STATE["NIFTY"] = timeframe_indicators

                                nifty_sentiment_indicators = (
                                    (MARKET_STATE.get("NIFTY") or {}).get(
                                        "5m",
                                        {},
                                    )
                                )

                                replay_shadow = run_shadow(
                                    trade["symbol"],
                                    trade,
                                    stock_sentiment_indicators,
                                    nifty_sentiment_indicators,
                                    record=False,
                                )

                                # Store Shadow Sentiment on the trade so the
                                # professional trade banner displays it.
                                # Do NOT print it separately.
                                trade["shadow_sentiment"] = replay_shadow

                                self.session_stats["sentiment_snapshots"] += 1

                                # Use the same professional trade banner as production.
                                # Replay keeps its own trade number because the replay
                                # lifecycle is already registering the trade here.
                                trade["replay_strategy"] = strategy

                                self.streamer.print_trade(
                                    trade,
                                    replay_mode=True,
                                    replay_timestamp=candle["timestamp"],
                                    preserve_trade_number=True,
                                )

            processed += 1

            # ----------------------------------------------------------
            # GLOBAL REPLAY SUMMARY CADENCE
            #
            # One summary every 10 replay minutes.
            # Unlike the old implementation, this is NOT emitted once
            # per symbol. The timestamp guard prevents 25x duplication
            # when multiple symbols share the same replay timeline.
            # ----------------------------------------------------------
            replay_ts = self._as_datetime(candle.get("timestamp"))

            if replay_ts is not None:

                    self._last_summary_timestamp = replay_ts

        return processed

    def replay_watchlist(self, watchlist):

        total_symbols = 0
        total_candles = 0

        print()
        print("=" * 78)
        print("🎬 PAISAAI REPLAY ENGINE V2")
        print("=" * 78)

        if PRINT_STRATEGY:

            print(
                f"🧠 Replay Strategy : "
                f"{self.active_strategy}"
            )

        print("=" * 78)

        limit = int(os.getenv("REPLAY_SYMBOL_LIMIT", "0"))
        if limit > 0:
            watchlist = list(watchlist)[:limit]
            print()
            print("=" * 78)
            print(f"⚡ REPLAY SHORT TEST : {len(watchlist)} SYMBOLS")
            print("🛡️ Dynamic SL + 🧠 Sentiment + 📊 Market Depth ACTIVE")
            print("=" * 78)

        for symbol in watchlist:

            candles = self.replay_symbol(
                symbol
            )

            if candles == 0:
                continue

            total_symbols += 1
            total_candles += candles

            print(
                f"✅ {symbol:<30} "
                f"{candles:>4} candles"
            )

        print()
        print("=" * 78)
        print("Replay Completed")

        print(
            f"Symbols : {total_symbols}"
        )

        print(
            f"Candles : {total_candles}"
        )

        print("=" * 78)

        self._print_replay_summary(
            "ALL",
            "FINAL",
        )

        manager.summary(self.active_strategy)


def start_replay_feed():

    from scanner.watchlist import get_watchlist

    replay = ReplayFeed()

    replay.replay_watchlist(
        get_watchlist()
    )


def run():
    start_replay_feed()

if __name__ == "__main__":
    run()
