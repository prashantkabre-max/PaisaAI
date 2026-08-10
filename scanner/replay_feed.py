"""
PaisaAI Replay Engine V2

Replay-only historical execution.

Replay rebuilds candle state sequentially from historical 1m candles.
Production LiveStreamer remains untouched.
"""

from data.candles import (
    get_history,
    update_tick,
    clear_symbol,
)

from scanner.stream import LiveStreamer
from scanner.strategy_manager import manager, STRATEGIES
from scanner.replay_strategy import STOPLOSS_MODE, PRINT_STRATEGY


class ReplayFeed:

    def __init__(self, speed=1.0):
        self.speed = speed
        self.streamer = LiveStreamer()

    def replay_symbol(self, symbol):

        # ------------------------------------------------------------
        # Capture the already-preloaded 1m historical candles.
        # ------------------------------------------------------------
        historical_candles = list(
            get_history(symbol, "1m")
        )

        if not historical_candles:
            return 0

        # ------------------------------------------------------------
        # CRITICAL:
        # Do NOT replay on top of the preloaded candle store.
        #
        # We rebuild the symbol candle state one candle at a time.
        # This prevents future candles from leaking into indicators.
        # ------------------------------------------------------------
        clear_symbol(symbol)

        processed = 0

        for candle in historical_candles:

            timestamp = candle.get("timestamp")

            # --------------------------------------------------------
            # Advance Replay candle engine.
            #
            # This is the authoritative source for determining
            # whether a 5m candle actually closed.
            # --------------------------------------------------------
            candle_update = update_tick(
                symbol=symbol,
                price=candle["close"],
                volume=candle.get("volume", 0),
                timestamp=timestamp,
            )

            if candle_update is None:
                processed += 1
                continue

            closed_timeframes = candle_update.get(
                "closed_timeframes",
                [],
            )

            market = {
                "symbol": symbol,
                "ltp": candle["close"],
                "previous_close": candle["open"],
                "open": candle["open"],
                "high": candle["high"],
                "low": candle["low"],
                "close": candle["close"],
                "volume": candle.get("volume", 0),
                "timestamp": timestamp,

                # ----------------------------------------------------
                # Replay-only flags.
                # ----------------------------------------------------
                "_replay": True,

                # Signal generation is allowed only when the
                # candle engine confirms that the 5m timeframe
                # actually closed.
                "_5m_closed": (
                    "5m" in closed_timeframes
                ),
            }

            result = self.streamer.process_completed_market(
                market
            )

            if result is not None:
                for strategy in STRATEGIES:
                    manager.register_trade(strategy)

            processed += 1

        return processed

    def replay_watchlist(self, watchlist):

        total_symbols = 0
        total_candles = 0

        print()
        print("=" * 60)
        print("🎬 PAISAAI REPLAY ENGINE V2")

        if PRINT_STRATEGY:
            print(
                f"🧠 Replay Strategy : {STOPLOSS_MODE}"
            )

        print("=" * 60)

        for symbol in watchlist:

            candles = self.replay_symbol(symbol)

            if candles == 0:
                continue

            total_symbols += 1
            total_candles += candles

            print(
                f"✅ {symbol:<30} "
                f"{candles:>4} candles"
            )

        print()
        print("=" * 60)
        print("Replay Completed")
        print(f"Symbols : {total_symbols}")
        print(f"Candles : {total_candles}")
        print("=" * 60)


def start_replay_feed():

    from scanner.watchlist import get_watchlist

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
