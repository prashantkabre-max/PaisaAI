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
            "rvol": None,
        }

    current_volume = candles[-1].get("volume", 0)

    previous = candles[:-1][-lookback:]

    volumes = [
        c.get("volume", 0)
        for c in previous
        if c.get("volume", 0) > 0
    ]

    if not volumes:
        return {
            "current_volume": current_volume,
            "average_volume": None,
            "rvol": None,
        }

    average_volume = sum(volumes) / len(volumes)
    rvol = round(current_volume / average_volume, 2)

    return {
        "current_volume": current_volume,
        "average_volume": round(average_volume, 2),
        "rvol": rvol,
    }
