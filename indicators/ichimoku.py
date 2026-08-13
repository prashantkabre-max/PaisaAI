"""Canonical Ichimoku Cloud: 9 / 26 / 52 / 26."""

TENKAN_PERIOD = 9
KIJUN_PERIOD = 26
SENKOU_B_PERIOD = 52
DISPLACEMENT = 26


def _midpoint(candles):
    high = max(c["high"] for c in candles)
    low = min(c["low"] for c in candles)
    return (high + low) / 2


def calculate_ichimoku(
    candles,
    tenkan_period=TENKAN_PERIOD,
    kijun_period=KIJUN_PERIOD,
    senkou_b_period=SENKOU_B_PERIOD,
    displacement=DISPLACEMENT,
):
    if not candles:
        return None

    minimum = max(
        tenkan_period,
        kijun_period,
        senkou_b_period,
    )

    if len(candles) < minimum:
        return None

    tenkan = _midpoint(
        candles[-tenkan_period:]
    )

    kijun = _midpoint(
        candles[-kijun_period:]
    )

    span_a = (tenkan + kijun) / 2

    span_b = _midpoint(
        candles[-senkou_b_period:]
    )

    close = candles[-1]["close"]

    cloud_top = max(span_a, span_b)
    cloud_bottom = min(span_a, span_b)

    if close > cloud_top:
        price_position = "ABOVE_CLOUD"
    elif close < cloud_bottom:
        price_position = "BELOW_CLOUD"
    else:
        price_position = "INSIDE_CLOUD"

    if tenkan > kijun:
        tk_direction = "BULLISH"
    elif tenkan < kijun:
        tk_direction = "BEARISH"
    else:
        tk_direction = "NEUTRAL"

    if span_a > span_b:
        cloud_direction = "BULLISH"
    elif span_a < span_b:
        cloud_direction = "BEARISH"
    else:
        cloud_direction = "NEUTRAL"

    return {
        "tenkan": round(tenkan, 4),
        "kijun": round(kijun, 4),
        "span_a": round(span_a, 4),
        "span_b": round(span_b, 4),
        "cloud_top": round(cloud_top, 4),
        "cloud_bottom": round(cloud_bottom, 4),
        "price_position": price_position,
        "tk_direction": tk_direction,
        "cloud_direction": cloud_direction,
        "displacement": displacement,
    }
