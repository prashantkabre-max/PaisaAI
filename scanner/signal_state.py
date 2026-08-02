"""
PaisaAI Signal Stability Engine
"""

from collections import deque


class SignalState:

    def __init__(self):
        self.history = {}

    def confirm(self, symbol, signal):

        if symbol not in self.history:
            self.history[symbol] = deque(maxlen=5)

        self.history[symbol].append(signal)

        buys = sum(1 for s in self.history[symbol] if s == "BUY")
        sells = sum(1 for s in self.history[symbol] if s == "SELL")

        if buys >= 3:
            return "BUY"

        if sells >= 3:
            return "SELL"

        return None

    def clear(self, symbol):
        self.history.pop(symbol, None)
