"""Non-repainting pivot-based intraday support/resistance."""

PIVOT_LEFT = 3
PIVOT_RIGHT = 3
LOOKBACK = 120


def _pivot_high(candles, index):
    if index < PIVOT_LEFT:
        return False

    if index + PIVOT_RIGHT >= len(candles):
        return False

    high = candles[index]["high"]

    left = candles[
        index - PIVOT_LEFT:index
    ]

    right = candles[
        index + 1:index + PIVOT_RIGHT + 1
    ]

    return (
        all(high > c["high"] for c in left)
        and all(high >= c["high"] for c in right)
    )


def _pivot_low(candles, index):
    if index < PIVOT_LEFT:
        return False

    if index + PIVOT_RIGHT >= len(candles):
        return False

    low = candles[index]["low"]

    left = candles[
        index - PIVOT_LEFT:index
    ]

    right = candles[
        index + 1:index + PIVOT_RIGHT + 1
    ]

    return (
        all(low < c["low"] for c in left)
        and all(low <= c["low"] for c in right)
    )


def calculate_support_resistance(
    candles,
    lookback=LOOKBACK,
):
    if not candles:
        return None

    data = candles[-lookback:]
    current = data[-1]["close"]

    supports = []
    resistances = []

    # Only confirmed pivots are used.
    for i in range(PIVOT_LEFT, len(data) - PIVOT_RIGHT):
        if _pivot_low(data, i):
            level = float(data[i]["low"])
            if level <= current:
                supports.append(level)

        if _pivot_high(data, i):
            level = float(data[i]["high"])
            if level >= current:
                resistances.append(level)

    support = max(supports) if supports else None
    resistance = min(resistances) if resistances else None

    if support is not None and resistance is not None:
        if current > resistance:
            position = "BREAKOUT"
        elif current < support:
            position = "BREAKDOWN"
        elif current >= resistance:
            position = "AT_RESISTANCE"
        elif current <= support:
            position = "AT_SUPPORT"
        else:
            midpoint = (support + resistance) / 2

            if current >= midpoint:
                position = "UPPER_RANGE"
            else:
                position = "LOWER_RANGE"
    elif resistance is not None:
        position = (
            "BREAKOUT"
            if current > resistance
            else "UPPER_RANGE"
        )
    elif support is not None:
        position = (
            "BREAKDOWN"
            if current < support
            else "LOWER_RANGE"
        )
    else:
        position = "UNAVAILABLE"

    return {
        "support": (
            round(support, 4)
            if support is not None
            else None
        ),
        "resistance": (
            round(resistance, 4)
            if resistance is not None
            else None
        ),
        "position": position,
    }
