"""
PaisaAI Replay Engine V2

Replay-only execution layer.

Every generated signal is evaluated independently through:
    ATR
    SESSION
    SWING
    ORB
    SMART

Production trade_manager.py and stream.py are untouched.
"""

from datetime import datetime

from scanner.replay_runner import ReplayRunner
from scanner.indicators import calculate_indicators
from scanner.replay_trade_manager import (
    STRATEGIES,
    reset,
    register_trade,
    update_trade,
    update_candle,
    finalize_replay,
    get_report,
    print_report,
)
from scanner.scoring import calculate_score
from scanner.decision import evaluate_trade

from data.candles import get_history


class ReplayFeed:

    def __init__(self, speed=1.0):

        self.speed = speed

        self.runner = ReplayRunner()

        self.trade_number = 0

        self.total_signals = 0

        self.strategy_entries = {
            strategy: 0
            for strategy in STRATEGIES
        }

    @staticmethod
    def _date_of(candle):

        timestamp = candle.get("timestamp")

        if timestamp is None:
            return None

        return str(timestamp)[:10]

    def _previous_session_close(
        self,
        candles,
        index,
    ):
        """
        Previous completed trading session close.

        This prevents the replay from using today's close
        as the previous-day reference.
        """

        if index <= 0:
            return None

        current_date = self._date_of(
            candles[index]
        )

        for i in range(
            index - 1,
            -1,
            -1,
        ):

            candle = candles[i]

            if (
                self._date_of(candle)
                != current_date
            ):
                return candle.get(
                    "close"
                )

        return None

    def _session_ohlc(
        self,
        candles,
        index,
    ):
        """
        Session OHLC available at the current candle.

        Only candles up to the current replay point
        are considered.
        """

        current_date = self._date_of(
            candles[index]
        )

        session = []

        for i in range(
            index,
            -1,
            -1,
        ):

            candle = candles[i]

            if (
                self._date_of(candle)
                != current_date
            ):
                break

            session.append(candle)

        session.reverse()

        if not session:

            return {
                "open": None,
                "high": None,
                "low": None,
            }

        highs = [
            candle.get("high")
            for candle in session
            if candle.get("high") is not None
        ]

        lows = [
            candle.get("low")
            for candle in session
            if candle.get("low") is not None
        ]

        return {
            "open": session[0].get("open"),
            "high": max(highs) if highs else None,
            "low": min(lows) if lows else None,
        }

    def _build_market(
        self,
        symbol,
        candle,
        previous_close,
        session_ohlc,
    ):

        return {
            "symbol": symbol,
            "ltp": candle.get("close"),
            "previous_close": previous_close,
            "open": session_ohlc["open"],
            "high": session_ohlc["high"],
            "low": session_ohlc["low"],
            "close": candle.get("close"),
            "volume": candle.get(
                "volume",
                0,
            ),
        }

    def _evaluate_signal(
        self,
        symbol,
        history,
        market,
    ):
        """
        Evaluate exactly one signal at this replay point.

        Indicator/scoring logic comes from the existing
        replay pipeline.
        """

        trade = self.runner.evaluate(
            symbol,
            history,
            market,
        )

        if trade is None:
            return None

        if trade.get("action") == "IGNORE":
            return None

        if trade.get("grade") == "IGNORE":
            return None

        return trade

    def _register_all_strategies(
        self,
        trade,
        history,
        timestamp,
    ):
        """
        Fan one signal into all five independent
        stop-loss strategies.
        """

        self.trade_number += 1

        trade["trade_number"] = (
            self.trade_number
        )

        trade["timestamp"] = timestamp

        registered = 0

        for strategy in STRATEGIES:

            success = register_trade(
                strategy,
                trade,
                history,
            )

            if success:

                self.strategy_entries[
                    strategy
                ] += 1

                registered += 1

        if registered:

            self.total_signals += 1

            print()
            print("=" * 82)
            print(
                "🎯 REPLAY SIGNAL "
                f"#{self.trade_number}"
            )
            print(
                f"📊 Stock       : "
                f"{trade.get('display_symbol', trade.get('symbol'))}"
            )
            print(
                f"📈 Direction   : "
                f"{trade.get('action')}"
            )
            print(
                f"⭐ Grade       : "
                f"{trade.get('grade')}"
            )
            print(
                f"🎯 Confidence  : "
                f"{trade.get('confidence')}%"
            )
            print(
                f"🕒 Time        : "
                f"{timestamp}"
            )
            print(
                "🧪 Strategies  : "
                + ", ".join(STRATEGIES)
            )
            print("=" * 82)

        return registered

    def _update_strategies(
        self,
        symbol,
        candle,
    ):
        """
        Send the complete OHLC candle to the replay
        trade manager.

        The trade manager determines the correct
        intrabar sequence independently for BUY/SELL.
        """

        timestamp = candle.get(
            "timestamp"
        )

        high = candle.get(
            "high"
        )

        low = candle.get(
            "low"
        )

        if high is None or low is None:
            return []

        events = []

        for strategy in STRATEGIES:

            result = update_candle(
                strategy,
                symbol,
                high,
                low,
                timestamp,
            )

            if result:

                events.extend(
                    result
                    if isinstance(result, list)
                    else [result]
                )

        for event in events:
            self._print_event(event)

        return events

    @staticmethod
    def _print_event(event):

        strategy = event.get(
            "strategy",
            "UNKNOWN",
        )

        symbol = event.get(
            "display_symbol",
            event.get("symbol"),
        )

        event_name = event.get(
            "event"
        )

        pnl = event.get(
            "pnl",
            0.0,
        )

        print()
        print(
            "-" * 82
        )

        if event_name == "TARGET_1_HIT":

            print(
                f"🏆 {strategy} | "
                f"TARGET 1 HIT | "
                f"{symbol}"
            )

        elif event_name == "TARGET_2_HIT":

            print(
                f"🥈 {strategy} | "
                f"TARGET 2 HIT | "
                f"{symbol}"
            )

        elif event_name == "TARGET_3_HIT":

            print(
                f"👑 {strategy} | "
                f"TARGET 3 ACHIEVED | "
                f"{symbol}"
            )

        elif event_name == "STOP_LOSS_HIT":

            print(
                f"🛑 {strategy} | "
                f"STOP LOSS HIT | "
                f"{symbol}"
            )

        else:

            print(
                f"ℹ️ {strategy} | "
                f"{event_name} | "
                f"{symbol}"
            )

        print(
            f"Entry : ₹{event.get('entry', 0):,.2f}"
        )

        print(
            f"Exit  : ₹{event.get('exit_price', 0):,.2f}"
        )

        print(
            f"Qty   : {event.get('quantity', 0)}"
        )

        print(
            f"P&L   : ₹{pnl:,.2f}"
        )

        print(
            "-" * 82
        )

    def replay_symbol(
        self,
        symbol,
    ):
        """
        Replay one symbol chronologically.
        """

        candles = get_history(
            symbol,
            "1m",
        )

        if not candles:
            return 0

        min_history = 50

        if len(candles) <= min_history:
            return 0

        processed = 0

        for index in range(
            min_history,
            len(candles),
        ):

            current = candles[index]

            history = candles[
                : index + 1
            ]

            previous_close = (
                self._previous_session_close(
                    candles,
                    index,
                )
            )

            if previous_close in (
                None,
                0,
            ):
                continue

            session_ohlc = (
                self._session_ohlc(
                    candles,
                    index,
                )
            )

            market = self._build_market(
                symbol,
                current,
                previous_close,
                session_ohlc,
            )

            # First evaluate the currently active
            # trades against this candle.
            self._update_strategies(
                symbol,
                current,
            )

            trade = self._evaluate_signal(
                symbol,
                history,
                market,
            )

            if trade is not None:

                # Replay risk engine needs the complete
                # indicator snapshot, especially ATR.
                indicators = (
                    self.runner.state.calculate(
                        symbol,
                        history,
                    )
                )

                trade["indicators"] = (
                    indicators
                )

                self._register_all_strategies(
                    trade,
                    history,
                    current.get(
                        "timestamp"
                    ),
                )

            processed += 1

        return processed

    def replay_watchlist(
        self,
        watchlist,
    ):

        reset()

        total_symbols = 0
        total_candles = 0

        print()
        print("=" * 82)
        print(
            "🎬 PAISAAI REPLAY ENGINE V2"
        )
        print(
            "🧪 FIVE STRATEGY STOP-LOSS LAB"
        )
        print("=" * 82)

        print(
            "Strategies : "
            + ", ".join(STRATEGIES)
        )

        print(
            "Risk cap   : ₹2,000 / trade"
        )

        print("=" * 82)

        for symbol in watchlist:

            candles = self.replay_symbol(
                symbol
            )

            if candles == 0:
                continue

            total_symbols += 1
            total_candles += candles

            print(
                f"✅ {symbol:<30}"
                f"{candles:>6} candles"
            )

        finalize_replay()

        print()
        print(
            f"Replay Symbols : "
            f"{total_symbols}"
        )

        print(
            f"Replay Candles : "
            f"{total_candles}"
        )

        print(
            f"Signals        : "
            f"{self.total_signals}"
        )

        print_report()


def get_active_for_strategy(
    strategy,
):
    """
    Local helper kept separate so ReplayFeed never imports
    or touches production trade_manager.py.
    """

    from scanner.replay_trade_manager import (
        get_active_trades,
    )

    return get_active_trades(
        strategy
    )


def start_replay_feed():

    from scanner.watchlist import (
        get_watchlist,
    )

    replay = ReplayFeed()

    replay.replay_watchlist(
        get_watchlist()
    )


def run():
    """
    Entry point used by main.py.
    """

    start_replay_feed()


if __name__ == "__main__":
    run()
