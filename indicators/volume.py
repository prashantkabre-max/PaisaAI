def calculate_volume_metrics(candles, lookback=20):
    """
    Calculates:
    - Current Volume
    - Average Volume
    - Relative Volume (RVOL)
    """

    if not candles:
        return None

    if len(candles) < 2:
        return {
            "current_volume": candles[-1].get("volume", 0),
            "average_volume": None,
            "rvol": None
        }

    current_volume = candles[-1].get("volume", 0)

    previous = candles[:-1]

    if len(previous) > lookback:
        previous = previous[-lookback:]

    volumes = [c.get("volume", 0) for c in previous]

    if len(volumes) == 0:
        return {
            "current_volume": current_volume,
            "average_volume": None,
            "rvol": None
        }

    average_volume = sum(volumes) / len(volumes)

    if average_volume == 0:
        rvol = None
    else:
        rvol = round(current_volume / average_volume, 2)

    return {
        "current_volume": current_volume,
        "average_volume": round(average_volume, 2),
        "rvol": rvol
    }
