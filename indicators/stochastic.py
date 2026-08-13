"""Standard Stochastic Oscillator: 14, 3, 3."""

STOCH_K_PERIOD = 14
STOCH_K_SMOOTH = 3
STOCH_D_PERIOD = 3


def _sma(values, period):
    if len(values) < period:
        return None
    return sum(values[-period:]) / period


def calculate_stochastic(
    candles,
    k_period=STOCH_K_PERIOD,
    k_smooth=STOCH_K_SMOOTH,
    d_period=STOCH_D_PERIOD,
):
    if not candles:
        return None

    if len(candles) < k_period + k_smooth + d_period - 2:
        return None

    raw_k = []

    for i in range(k_period - 1, len(candles)):
        window = candles[i - k_period + 1:i + 1]

        highest = max(c["high"] for c in window)
        lowest = min(c["low"] for c in window)
        close = candles[i]["close"]

        denominator = highest - lowest

        if denominator == 0:
            value = 0.0
        else:
            value = ((close - lowest) / denominator) * 100.0

        raw_k.append(value)

    smooth_k = []

    for i in range(k_smooth - 1, len(raw_k)):
        value = _sma(raw_k[:i + 1], k_smooth)
        if value is not None:
            smooth_k.append(value)

    if len(smooth_k) < d_period:
        return None

    k = smooth_k[-1]
    d = _sma(smooth_k, d_period)

    if d is None:
        return None

    if k > d:
        direction = "BULLISH"
    elif k < d:
        direction = "BEARISH"
    else:
        direction = "NEUTRAL"

    return {
        "k": round(k, 2),
        "d": round(d, 2),
        "direction": direction,
        "overbought": k >= 80,
        "oversold": k <= 20,
    }
