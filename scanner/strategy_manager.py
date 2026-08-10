"""
Replay Strategy Manager

Each strategy maintains its own independent
statistics during replay.
"""

STRATEGIES = [
    "ATR",
    "SESSION",
    "SWING",
    "ORB",
    "SMART",
]


class StrategyManager:

    def __init__(self):

        self.stats = {}

        for strategy in STRATEGIES:
            self.stats[strategy] = {
                "trades": 0,
                "wins": 0,
                "losses": 0,
                "gross_profit": 0.0,
                "gross_loss": 0.0,
            }

    def register_trade(self, strategy):
        self.stats[strategy]["trades"] += 1

    def register_win(self, strategy, pnl):
        self.stats[strategy]["wins"] += 1
        self.stats[strategy]["gross_profit"] += pnl

    def register_loss(self, strategy, pnl):
        self.stats[strategy]["losses"] += 1
        self.stats[strategy]["gross_loss"] += abs(pnl)

    def summary(self, strategy="ATR"):

        strategy = strategy.upper()
        s = self.stats.get(strategy)

        if s is None:
            return

        trades = s["trades"]
        closed = s["wins"] + s["losses"]
        winrate = (s["wins"] / closed) * 100 if closed else 0
        net = s["gross_profit"] - s["gross_loss"]

        print()
        print("=" * 78)
        print("REPLAY RESULT")
        print("=" * 78)
        print(f"Stop Loss : {strategy}")
        print(f"Trades    : {trades}")
        print(f"Wins      : {s['wins']}")
        print(f"Losses    : {s['losses']}")
        print(f"Win Rate  : {winrate:.1f}%")
        print(f"Net P&L   : ₹{net:,.2f}")
        print("=" * 78)

manager = StrategyManager()
