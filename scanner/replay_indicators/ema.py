class EMAState:

    def __init__(self, period):
        self.period = period
        self.multiplier = 2 / (period + 1)
        self.value = None

    def update(self, close, seed=None):

        if self.value is None:
            if seed is None:
                return None

            self.value = seed
            return round(self.value, 2)

        self.value = (
            (close - self.value)
            * self.multiplier
        ) + self.value

        return round(self.value, 2)


def calculate_ema(candles, period=9, previous_ema=None):

    if len(candles) < period:
        return None

    if previous_ema is not None:
        multiplier = 2 / (period + 1)

        ema = (
            (candles[-1]["close"] - previous_ema)
            * multiplier
        ) + previous_ema

        return round(ema, 2)

    closes = [
        c["close"]
        for c in candles
    ]

    ema = sum(closes[:period]) / period

    multiplier = 2 / (period + 1)

    for close in closes[period:]:
        ema = (
            (close - ema)
            * multiplier
        ) + ema

    return round(ema, 2)
