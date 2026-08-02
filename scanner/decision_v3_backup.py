"""
PaisaAI Unified Decision Engine
"""

from scanner.risk import calculate_risk
from scanner.trade_timing import evaluate_trade_timing


def evaluate_trade(
    indicators,
    score_result,
):
    """
    Builds the unified trade object for PaisaAI.

    This is the single object that flows through:

    Decision -> Alerts -> Learning -> Ranking
    """

    if indicators is None:
        return None

    if score_result is None:
        return None

    grade = score_result.get("grade", "IGNORE")

    signal = "IGNORE"

    ema9 = indicators.get("ema9")
    ema20 = indicators.get("ema20")

    if (
        grade != "IGNORE"
        and ema9 is not None
        and ema20 is not None
    ):
        if ema9 > ema20:
            signal = "BUY"
        else:
            signal = "SELL"

    risk = None

    if signal != "IGNORE":
        risk = calculate_risk(
            indicators,
            signal,
        )

    trade = {
        "symbol": indicators.get("symbol"),
        "display_symbol": indicators.get("display_symbol"),
        "action": signal,
        "grade": grade,
        "confidence": score_result.get("confidence", 0),

        "passed": score_result.get("passed", []),
        "failed": score_result.get("failed", []),

        "risk": risk,

        # Context
        "ema9": indicators.get("ema9"),
        "ema20": indicators.get("ema20"),
        "adx": indicators.get("adx"),
        "rsi": indicators.get("rsi"),
        "rvol": indicators.get("rvol"),
        "atr": indicators.get("atr"),
        "vwap": indicators.get("vwap"),
        "ltp": indicators.get("ltp"),
        "change_percent": indicators.get("change_percent"),

        # Future engines
        "market_sentiment": None,
        "stock_sentiment": None,
        "trade_timing": evaluate_trade_timing(
            indicators,
            risk,
            signal,
        ),
    }

    return trade
