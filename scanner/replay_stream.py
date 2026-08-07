"""
Replay Streamer

Replay-only implementation.
Production LiveStreamer remains untouched.
"""

from scanner.stream import LiveStreamer

from scanner.replay_trade_manager import (
    register_trade,
    update_trade,
    get_active_trades,
    get_strategies,
)


class ReplayStreamer(LiveStreamer):

    def __init__(self):
        super().__init__()

    def replay_register_trade(self, strategy, trade):
        return register_trade(strategy, trade)

    def replay_update_trade(self, strategy, symbol, price):
        return update_trade(strategy, symbol, price)

    def replay_get_active_trades(self, strategy=None):
        return get_active_trades(strategy)



    def process_replay_trade(self, trade):
        """
        Replay one trade through every stop-loss strategy.
        """
        from scanner.strategy_manager import STRATEGIES

        for strategy in STRATEGIES:

            print(f"🧪 Testing Strategy : {strategy}")

            self.replay_register_trade(
                strategy,
                trade.copy(),
            )


    def replay_get_strategies(self):
        return get_strategies()
