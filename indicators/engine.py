from indicators.ema import calculate_ema
from indicators.vwap import calculate_vwap
from indicators.volume import calculate_volume_metrics
from indicators.rsi import calculate_rsi
from indicators.macd import calculate_macd
from indicators.atr import calculate_atr
from indicators.adx import calculate_adx
from indicators.supertrend import calculate_supertrend
from indicators.orb import calculate_orb


def calculate_all_indicators(candles, symbol=None):
    """
    Calculate all indicators used by PaisaAI.
    """

    if not candles:
        return {}

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

    return {

        "ema9": ema9,
        "ema20": ema20,

        "vwap": vwap,

        "current_volume": volume.get("current_volume"),
        "average_volume": volume.get("average_volume"),
        "rvol": volume.get("rvol"),

        "rsi": rsi,

        "macd": macd.get("macd") if macd else None,
        "macd_signal": macd.get("signal") if macd else None,
        "macd_histogram": macd.get("histogram") if macd else None,

        "atr": atr,

        "adx": adx.get("adx") if adx else None,
        "plus_di": adx.get("plus_di") if adx else None,
        "minus_di": adx.get("minus_di") if adx else None,
        "adx_trend": adx.get("trend") if adx else None,

        "supertrend": supertrend.get("supertrend") if supertrend else None,
        "supertrend_trend": supertrend.get("trend") if supertrend else None,

        "orb_high": orb.get("orb_high") if orb else None,
        "orb_low": orb.get("orb_low") if orb else None,
        "orb_breakout": orb.get("orb_breakout") if orb else False,
        "orb_breakdown": orb.get("orb_breakdown") if orb else False,
    }
