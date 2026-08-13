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

        # ========================================================
        # NEW LIVE INDICATORS
        # ========================================================

        "stochastic_k": all_indicators.get("stochastic_k"),
        "stochastic_d": all_indicators.get("stochastic_d"),
        "stochastic_direction": all_indicators.get(
            "stochastic_direction"
        ),
        "stochastic_overbought": all_indicators.get(
            "stochastic_overbought"
        ),
        "stochastic_oversold": all_indicators.get(
            "stochastic_oversold"
        ),

        "support": all_indicators.get("support"),
        "resistance": all_indicators.get("resistance"),
        "support_resistance_position": all_indicators.get(
            "support_resistance_position"
        ),

        "bb_middle": all_indicators.get("bb_middle"),
        "bb_upper": all_indicators.get("bb_upper"),
        "bb_lower": all_indicators.get("bb_lower"),
        "bb_percent_b": all_indicators.get("bb_percent_b"),
        "bb_band_width": all_indicators.get("bb_band_width"),
        "bb_bandwidth": all_indicators.get("bb_bandwidth"),
        "bb_position": all_indicators.get("bb_position"),

        "ichimoku_tenkan": all_indicators.get(
            "ichimoku_tenkan"
        ),
        "ichimoku_kijun": all_indicators.get(
            "ichimoku_kijun"
        ),
        "ichimoku_span_a": all_indicators.get(
            "ichimoku_span_a"
        ),
        "ichimoku_span_b": all_indicators.get(
            "ichimoku_span_b"
        ),
        "ichimoku_cloud_top": all_indicators.get(
            "ichimoku_cloud_top"
        ),
        "ichimoku_cloud_bottom": all_indicators.get(
            "ichimoku_cloud_bottom"
        ),
        "ichimoku_price_position": all_indicators.get(
            "ichimoku_price_position"
        ),
        "ichimoku_tk_direction": all_indicators.get(
            "ichimoku_tk_direction"
        ),
        "ichimoku_cloud_direction": all_indicators.get(
            "ichimoku_cloud_direction"
        ),
    }
