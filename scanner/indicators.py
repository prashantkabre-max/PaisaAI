from data.nifty200 import SYMBOL_MAP


def calculate_indicators(data, all_indicators=None):
    """
    Combine live market data with calculated indicators.

    Price change standard:
    Daily % Change = (LTP - Previous Day Close) / Previous Day Close * 100
    """

    if data is None:
        return None

    if all_indicators is None:
        all_indicators = {}

    ltp = data.get("ltp")

    previous_close = data.get("previous_close")

    if previous_close is None:
        previous_close = data.get("change_percent")

    if previous_close is None:
        previous_close = data.get("close")

    if ltp is None or previous_close in (None, 0):
        return None

    change = ltp - previous_close
    change_percent = (change / previous_close) * 100

    return {
        "display_symbol": SYMBOL_MAP.get(data["symbol"], data["symbol"]),
        "symbol": data["symbol"],

        "ltp": ltp,

        "previous_close": previous_close,
        "change": round(change, 2),
        "change_percent": round(change_percent, 2),

        # Optional context-engine data.
        # Real sector feeds can populate these fields without
        # changing the technical indicator engine.
        "sector": data.get("sector"),
        "sector_change": data.get("sector_change"),

        "open": data.get("open"),
        "high": data.get("high"),
        "low": data.get("low"),
        "close": data.get("close"),

        # EMA
        "ema9": all_indicators.get("ema9"),
        "ema20": all_indicators.get("ema20"),

        # VWAP
        "vwap": all_indicators.get("vwap"),

        # Volume
        "current_volume": all_indicators.get("current_volume"),
        "average_volume": all_indicators.get("average_volume"),
        "rvol": all_indicators.get("rvol"),
        "volume_spike": all_indicators.get("volume_spike"),
        "volume_trend": all_indicators.get("volume_trend"),
        "volume_strength": all_indicators.get("volume_strength"),

        # RSI
        "rsi": all_indicators.get("rsi"),

        # MACD
        "macd": all_indicators.get("macd"),
        "macd_signal": all_indicators.get("macd_signal"),
        "macd_histogram": all_indicators.get("macd_histogram"),

        # ATR
        "atr": all_indicators.get("atr"),

        # ADX
        "adx": all_indicators.get("adx"),
        "plus_di": all_indicators.get("plus_di"),
        "minus_di": all_indicators.get("minus_di"),
        "adx_trend": all_indicators.get("adx_trend"),

        # Supertrend
        "supertrend": all_indicators.get("supertrend"),
        "supertrend_trend": all_indicators.get("supertrend_trend"),

        # ORB
        "orb_high": all_indicators.get("orb_high"),
        "orb_low": all_indicators.get("orb_low"),
        "orb_breakout": all_indicators.get("orb_breakout"),
        "orb_breakdown": all_indicators.get("orb_breakdown"),

        # Swing
        "swing_high": all_indicators.get("swing_high"),
        "swing_low": all_indicators.get("swing_low"),
    }
