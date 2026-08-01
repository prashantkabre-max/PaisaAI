from scanner.replay_indicators.ema import calculate_ema
from scanner.replay_indicators.vwap import calculate_vwap
from scanner.replay_indicators.volume import calculate_volume_metrics
from scanner.replay_indicators.rsi import calculate_rsi
from scanner.replay_indicators.macd import calculate_macd
from scanner.replay_indicators.atr import calculate_atr
from scanner.replay_indicators.adx import calculate_adx
from scanner.replay_indicators.supertrend import calculate_supertrend


def calculate_all_indicators(candles, symbol=None):
    """
    Replay-only indicator engine.

    This is intentionally independent from the live engine so Replay
    optimizations never affect production trading.
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

        "supertrend": supertrend.get("supertrend") if supertrend else None,
        "supertrend_trend": supertrend.get("trend") if supertrend else None,
    }
