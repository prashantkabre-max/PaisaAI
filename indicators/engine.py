from indicators.ema import calculate_ema
from indicators.vwap import calculate_vwap
from indicators.volume import calculate_volume_metrics
from indicators.rsi import calculate_rsi
from indicators.macd import calculate_macd
from indicators.atr import calculate_atr
from indicators.adx import calculate_adx
from indicators.supertrend import calculate_supertrend
from indicators.orb import calculate_orb

from indicators.stochastic import calculate_stochastic
from indicators.bollinger import calculate_bollinger
from indicators.support_resistance import calculate_support_resistance
from indicators.ichimoku import calculate_ichimoku


def calculate_all_indicators(candles, symbol=None):
    """
    Production indicator engine.

    Existing indicators remain intact.
    New industry-standard indicators:
        - Stochastic 14/3/3
        - Support/Resistance via confirmed pivots
        - Bollinger 20/2
        - Bollinger %B
        - Bollinger BandWidth
        - Ichimoku 9/26/52/26
    """

    if not candles:
        return {}

    if isinstance(candles, dict):
        results = {}

        for timeframe, tf_candles in candles.items():
            results[timeframe] = calculate_all_indicators(
                tf_candles,
                symbol,
            )

        return results

    ema9 = calculate_ema(candles, 9)
    ema20 = calculate_ema(candles, 20)

    vwap = calculate_vwap(candles)
    volume = calculate_volume_metrics(candles)
    rsi = calculate_rsi(candles)
    macd = calculate_macd(candles)
    atr = calculate_atr(candles)
    adx = calculate_adx(candles)
    supertrend = calculate_supertrend(candles)
    orb = calculate_orb(symbol, candles) if symbol else None

    stochastic = calculate_stochastic(candles)
    bollinger = calculate_bollinger(candles)
    support_resistance = calculate_support_resistance(candles)
    ichimoku = calculate_ichimoku(candles)

    return {
        "ema9": ema9,
        "ema20": ema20,

        "vwap": vwap,

        "current_volume": volume.get("current_volume"),
        "average_volume": volume.get("average_volume"),
        "rvol": volume.get("rvol"),
        "volume_spike": volume.get("volume_spike"),
        "volume_trend": volume.get("volume_trend"),
        "volume_strength": volume.get("volume_strength"),

        "rsi": rsi,

        "macd": macd.get("macd") if macd else None,
        "macd_signal": macd.get("signal") if macd else None,
        "macd_histogram": macd.get("histogram") if macd else None,

        "atr": atr,

        "adx": adx.get("adx") if adx else None,
        "plus_di": adx.get("plus_di") if adx else None,
        "minus_di": adx.get("minus_di") if adx else None,
        "adx_trend": adx.get("trend") if adx else None,

        "supertrend": (
            supertrend.get("supertrend")
            if supertrend else None
        ),
        "supertrend_trend": (
            supertrend.get("trend")
            if supertrend else None
        ),

        "orb_high": (
            orb.get("orb_high")
            if orb else None
        ),
        "orb_low": (
            orb.get("orb_low")
            if orb else None
        ),
        "orb_breakout": (
            orb.get("orb_breakout", False)
            if orb else False
        ),
        "orb_breakdown": (
            orb.get("orb_breakdown", False)
            if orb else False
        ),

        # ========================================================
        # NEW LIVE INDICATORS
        # ========================================================

        # Stochastic
        "stochastic_k": (
            stochastic.get("k")
            if stochastic else None
        ),
        "stochastic_d": (
            stochastic.get("d")
            if stochastic else None
        ),
        "stochastic_direction": (
            stochastic.get("direction")
            if stochastic else None
        ),
        "stochastic_overbought": (
            stochastic.get("overbought", False)
            if stochastic else False
        ),
        "stochastic_oversold": (
            stochastic.get("oversold", False)
            if stochastic else False
        ),

        # Support / Resistance
        "support": (
            support_resistance.get("support")
            if support_resistance else None
        ),
        "resistance": (
            support_resistance.get("resistance")
            if support_resistance else None
        ),
        "support_resistance_position": (
            support_resistance.get("position")
            if support_resistance else None
        ),

        # Bollinger Bands
        "bb_middle": (
            bollinger.get("middle")
            if bollinger else None
        ),
        "bb_upper": (
            bollinger.get("upper")
            if bollinger else None
        ),
        "bb_lower": (
            bollinger.get("lower")
            if bollinger else None
        ),
        "bb_percent_b": (
            bollinger.get("percent_b")
            if bollinger else None
        ),
        "bb_bandwidth": (
            bollinger.get("bandwidth")
            if bollinger else None
        ),
        "bb_position": (
            bollinger.get("position")
            if bollinger else None
        ),

        # Ichimoku
        "ichimoku_tenkan": (
            ichimoku.get("tenkan")
            if ichimoku else None
        ),
        "ichimoku_kijun": (
            ichimoku.get("kijun")
            if ichimoku else None
        ),
        "ichimoku_span_a": (
            ichimoku.get("span_a")
            if ichimoku else None
        ),
        "ichimoku_span_b": (
            ichimoku.get("span_b")
            if ichimoku else None
        ),
        "ichimoku_cloud_top": (
            ichimoku.get("cloud_top")
            if ichimoku else None
        ),
        "ichimoku_cloud_bottom": (
            ichimoku.get("cloud_bottom")
            if ichimoku else None
        ),
        "ichimoku_price_position": (
            ichimoku.get("price_position")
            if ichimoku else None
        ),
        "ichimoku_tk_direction": (
            ichimoku.get("tk_direction")
            if ichimoku else None
        ),
        "ichimoku_cloud_direction": (
            ichimoku.get("cloud_direction")
            if ichimoku else None
        ),
    }
