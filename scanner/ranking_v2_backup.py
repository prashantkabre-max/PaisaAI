"""
PaisaAI Ranking Engine
"""

class RankingEngine:

    def __init__(self):
        self.trades = []

    def add_trade(self, trade):

        if trade is None:
            return

        if trade.get("grade") == "IGNORE":
            return

        self.trades.append(trade)

        self.trades.sort(
            key=lambda t: t.get("confidence", 0),
            reverse=True,
        )

        self.trades = self.trades[:10]

    def get_top_trades(self):
        return self.trades
