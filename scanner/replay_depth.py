"""Replay adapter for the observation-only market-depth engine."""


def _qty(value, fallback):
    try:
        value = float(value)
        return max(1.0, value)
    except (TypeError, ValueError):
        return float(fallback)


def build_snapshot(candle):
    """Return five-level depth from candle-provided depth or OHLCV proxy.

    If historical candles already contain ``bids``/``asks``, they are used
    unchanged. Otherwise we create a deterministic proxy from candle
    direction and volume. The proxy is ONLY for validating replay plumbing;
    it is never treated as historical real order-book data.
    """
    bids = candle.get("bids") if isinstance(candle, dict) else None
    asks = candle.get("asks") if isinstance(candle, dict) else None

    if bids and asks:
        return list(bids)[:5], list(asks)[:5], False

    open_price = _qty(candle.get("open"), 1)
    close_price = _qty(candle.get("close"), open_price)
    volume = _qty(candle.get("volume"), 100)
    base = max(20.0, volume / 5.0)

    if close_price > open_price:
        bid_total = base * 1.35
        ask_total = base
    elif close_price < open_price:
        bid_total = base
        ask_total = base * 1.35
    else:
        bid_total = base
        ask_total = base

    bid_each = bid_total / 5.0
    ask_each = ask_total / 5.0
    price = close_price

    generated_bids = [
        {"quantity": bid_each, "price": price - (i + 1) * 0.05}
        for i in range(5)
    ]
    generated_asks = [
        {"quantity": ask_each, "price": price + (i + 1) * 0.05}
        for i in range(5)
    ]

    return generated_bids, generated_asks, True
