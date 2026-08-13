"""Standard Bollinger Bands, %B and BandWidth."""

import math


BB_PERIOD = 20
BB_STDDEV = 2.0


def calculate_bollinger(
    candles,
    period=BB_PERIOD,
    stddev=BB_STDDEV,
):
    if not candles or len(candles) < period:
        return None

    closes = [
        float(c["close"])
        for c in candles[-period:]
    ]

    middle = sum(closes) / period

    variance = sum(
        (price - middle) ** 2
        for price in closes
    ) / period

    deviation = math.sqrt(variance)

    upper = middle + (stddev * deviation)
    lower = middle - (stddev * deviation)

    close = closes[-1]

    width = upper - lower

    if width == 0:
        percent_b = 0.5
    else:
        percent_b = (close - lower) / width

    if middle == 0:
        bandwidth = 0.0
    else:
        bandwidth = (width / middle) * 100.0

    if close > upper:
        position = "ABOVE_UPPER"
    elif close < lower:
        position = "BELOW_LOWER"
    elif close >= middle:
        position = "ABOVE_MIDDLE"
    else:
        position = "BELOW_MIDDLE"

    return {
        "middle": round(middle, 4),
        "upper": round(upper, 4),
        "lower": round(lower, 4),
        "percent_b": round(percent_b, 4),
        "bandwidth": round(bandwidth, 4),
        "position": position,
    }
