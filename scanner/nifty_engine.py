"""
PaisaAI Nifty Engine v1
Independent module.
"""

ENGINE_NAME = "Nifty Engine"
ENGINE_VERSION = "1.0"

from scanner.nifty_config import *


def score_trend(nifty):
    """
    Trend scoring based on EMA alignment.
    """

    ema20 = nifty.get("ema20")
    ema50 = nifty.get("ema50")
    ltp = nifty.get("ltp")

    if None in (ema20, ema50, ltp):
        return {
            "score": 0,
            "confidence": 0,
            "trend": "UNKNOWN",
            "reason": "Missing EMA data",
        }

    if ltp > ema20 > ema50:
        return {
            "score": TREND_WEIGHT,
            "confidence": 100,
            "trend": "UPTREND",
            "reason": "Price above EMA20 above EMA50",
        }

    if ltp < ema20 < ema50:
        return {
            "score": 0,
            "confidence": 100,
            "trend": "DOWNTREND",
            "reason": "Price below EMA20 below EMA50",
        }

    return {
        "score": TREND_WEIGHT // 2,
        "confidence": 50,
        "trend": "SIDEWAYS",
        "reason": "Mixed EMA structure",
    }




def analyze_nifty(nifty):
    """
    Analyze Nifty and return its contribution
    to Market Sentiment.
    """

    trend = score_trend(nifty)

    return {
        "score": trend["score"],
        "confidence": trend["confidence"],
        "trend": trend["trend"],
        "status": "PASS",
        "reasons": [trend["reason"]],
    }


if __name__ == "__main__":
    print(analyze_nifty({}))
