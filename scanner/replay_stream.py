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
        super().__init__(risk_mode="replay")

    def replay_register_trade(self, strategy, trade):
        return register_trade(strategy, trade)

    def replay_update_trade(self, strategy, symbol, price):
        return update_trade(strategy, symbol, price)

    def replay_get_active_trades(self, strategy=None):
        return get_active_trades(strategy)

    def replay_get_strategies(self):
        return get_strategies()
