def calculate_vwap(candles):
    """
    Calculate VWAP from a list of candles.
    Each candle must contain:
        high
        low
        close
        volume
    """

    if not candles:
        return None

    cumulative_tpv = 0
    cumulative_volume = 0

    for candle in candles:
        high = candle.get("high")
        low = candle.get("low")
        close = candle.get("close")
        volume = candle.get("volume")

        if None in (high, low, close, volume):
            continue

        typical_price = (high + low + close) / 3

        cumulative_tpv += typical_price * volume
        cumulative_volume += volume

    if cumulative_volume == 0:
        return None

    return round(cumulative_tpv / cumulative_volume, 2)
