"""
PaisaAI Replay Engine V2
"""

from datetime import datetime
from data.candles import get_history
from scanner.stream import LiveStreamer
from scanner.strategy_manager import manager, STRATEGIES
from scanner.replay_strategy import STOPLOSS_MODE, PRINT_STRATEGY


class ReplayFeed:

    def __init__(self, speed=1.0):
        self.speed = speed
        self.streamer = LiveStreamer()

    def replay_symbol(self, symbol):

        candles = get_history(symbol, "1m")

        if not candles:
            return 0

        processed = 0

        for candle in candles:

            market = {
                "symbol": symbol,
                "ltp": candle["close"],
                "previous_close": candle["open"],
                "open": candle["open"],
                "high": candle["high"],
                "low": candle["low"],
                "close": candle["close"],
                "volume": candle["volume"],
            }

            result = self.streamer.process_completed_market(market)

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
            print(f"🧠 Replay Strategy : {STOPLOSS_MODE}")
        print("=" * 60)

        for symbol in watchlist:

            candles = self.replay_symbol(symbol)

            if candles == 0:
                continue

            total_symbols += 1
            total_candles += candles

            print(f"✅ {symbol:<30} {candles:>4} candles")

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
    Entry point used by main.py
    """

    start_replay_feed()


if __name__ == "__main__":
    run()

