"""
PaisaAI Live Shadow Sentiment Engine
====================================

Observation-only sentiment engine.

IMPORTANT:
- Never modifies production trade decisions.
- Never changes entry, exit, SL, targets, grade or confidence.
- Live mode records observations.
- Replay mode can call run_shadow(..., record=False).
"""

import json
from datetime import datetime
from pathlib import Path


LOG_FILE = Path("logs/shadow_sentiment.jsonl")

ENGINE_NAME = "Shadow Sentiment"
ENGINE_VERSION = "2.0"

# Component weights used only when the component has valid data.
WEIGHTS = {
    "nifty_trend": 30,
    "nifty_strength": 10,
    "stock_ema": 20,
    "vwap": 15,
    "supertrend": 10,
    "rsi": 10,
    "price_action": 5,
}


def _direction(score):
    if score >= 20:
        return "BULLISH"

    if score <= -20:
        return "BEARISH"

    return "NEUTRAL"


def _confidence(score):
    return min(100, max(0, int(abs(score))))


def _add(score, reasons, points, reason):
    score += points
    reasons.append(reason)
    return score


def analyze_shadow_sentiment(stock, nifty=None):
    """
    Calculate observation-only sentiment.

    Score:
        -100 to +100

    No production trade object is modified.
    Missing data contributes ZERO rather than being guessed.
    """

    stock = stock or {}
    nifty = nifty or {}

    score = 0
    reasons = []

    # ============================================================
    # NIFTY MARKET CONTEXT
    # ============================================================

    n_ema9 = nifty.get("ema9")
    n_ema20 = nifty.get("ema20")
    n_vwap = nifty.get("vwap")
    n_ltp = nifty.get("ltp")
    n_adx = nifty.get("adx")
    n_supertrend = nifty.get("supertrend_trend")

    # Nifty EMA structure
    if n_ema9 is not None and n_ema20 is not None:
        if n_ema9 > n_ema20:
            score = _add(
                score,
                reasons,
                WEIGHTS["nifty_trend"],
                "NIFTY bullish EMA",
            )
        elif n_ema9 < n_ema20:
            score = _add(
                score,
                reasons,
                -WEIGHTS["nifty_trend"],
                "NIFTY bearish EMA",
            )

    # Nifty trend strength
    if n_adx is not None:
        if n_adx >= 25:
            if n_ema9 is not None and n_ema20 is not None:
                if n_ema9 > n_ema20:
                    score = _add(
                        score,
                        reasons,
                        WEIGHTS["nifty_strength"],
                        "NIFTY strong bullish trend",
                    )
                elif n_ema9 < n_ema20:
                    score = _add(
                        score,
                        reasons,
                        -WEIGHTS["nifty_strength"],
                        "NIFTY strong bearish trend",
                    )
        elif n_adx < 20:
            reasons.append("NIFTY trend weak")

    # Nifty VWAP
    if n_ltp is not None and n_vwap is not None:
        if n_ltp > n_vwap:
            score = _add(
                score,
                reasons,
                5,
                "NIFTY above VWAP",
            )
        elif n_ltp < n_vwap:
            score = _add(
                score,
                reasons,
                -5,
                "NIFTY below VWAP",
            )

    # Nifty Supertrend
    if n_supertrend is not None:
        trend = str(n_supertrend).upper()

        if any(x in trend for x in ("BUY", "BULL", "UP")):
            score = _add(
                score,
                reasons,
                5,
                "NIFTY Supertrend bullish",
            )
        elif any(x in trend for x in ("SELL", "BEAR", "DOWN")):
            score = _add(
                score,
                reasons,
                -5,
                "NIFTY Supertrend bearish",
            )

    # ============================================================
    # STOCK CONTEXT
    # ============================================================

    ema9 = stock.get("ema9")
    ema20 = stock.get("ema20")
    vwap = stock.get("vwap")
    ltp = stock.get("ltp")
    rsi = stock.get("rsi")
    supertrend = stock.get("supertrend_trend")

    # Stock EMA
    if ema9 is not None and ema20 is not None:
        if ema9 > ema20:
            score = _add(
                score,
                reasons,
                WEIGHTS["stock_ema"],
                "stock EMA bullish",
            )
        elif ema9 < ema20:
            score = _add(
                score,
                reasons,
                -WEIGHTS["stock_ema"],
                "stock EMA bearish",
            )

    # Stock VWAP
    if ltp is not None and vwap is not None:
        if ltp > vwap:
            score = _add(
                score,
                reasons,
                WEIGHTS["vwap"],
                "stock above VWAP",
            )
        elif ltp < vwap:
            score = _add(
                score,
                reasons,
                -WEIGHTS["vwap"],
                "stock below VWAP",
            )

    # Stock Supertrend
    if supertrend is not None:
        trend = str(supertrend).upper()

        if any(x in trend for x in ("BUY", "BULL", "UP")):
            score = _add(
                score,
                reasons,
                WEIGHTS["supertrend"],
                "stock Supertrend bullish",
            )
        elif any(x in trend for x in ("SELL", "BEAR", "DOWN")):
            score = _add(
                score,
                reasons,
                -WEIGHTS["supertrend"],
                "stock Supertrend bearish",
            )

    # RSI
    if rsi is not None:
        if 55 <= rsi <= 70:
            score = _add(
                score,
                reasons,
                WEIGHTS["rsi"],
                "RSI bullish zone",
            )
        elif 30 <= rsi <= 45:
            score = _add(
                score,
                reasons,
                -WEIGHTS["rsi"],
                "RSI bearish zone",
            )
        elif rsi > 70:
            reasons.append("RSI overbought")
        elif rsi < 30:
            reasons.append("RSI oversold")

    # Price action relative to VWAP already captures intraday
    # directional pressure. Add a small confirmation from EMA.
    if ltp is not None and ema9 is not None:
        if ltp > ema9:
            score = _add(
                score,
                reasons,
                WEIGHTS["price_action"],
                "price above EMA9",
            )
        elif ltp < ema9:
            score = _add(
                score,
                reasons,
                -WEIGHTS["price_action"],
                "price below EMA9",
            )

    score = max(-100, min(100, int(score)))

    return {
        "timestamp": datetime.now().isoformat(),
        "engine": ENGINE_NAME,
        "version": ENGINE_VERSION,
        "score": score,
        "confidence": _confidence(score),
        "sentiment": _direction(score),
        "reasons": reasons,
    }


def record_shadow(symbol, production_trade, sentiment):
    """
    Append-only live observation.
    """

    LOG_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    record = {
        "timestamp": datetime.now().isoformat(),
        "symbol": symbol,
        "production_action": production_trade.get("action"),
        "production_grade": production_trade.get("grade"),
        "production_confidence": production_trade.get("confidence"),
        "shadow_score": sentiment["score"],
        "shadow_confidence": sentiment["confidence"],
        "shadow_sentiment": sentiment["sentiment"],
        "shadow_reasons": sentiment["reasons"],
    }

    with LOG_FILE.open("a") as f:
        f.write(
            json.dumps(
                record,
                separators=(",", ":"),
            )
            + "\n"
        )


def run_shadow(
    symbol,
    production_trade,
    stock_indicators,
    nifty_indicators,
    record=True,
):
    """
    Run sentiment observation.

    record=True:
        Live production.

    record=False:
        Replay / testing.

    Production trade is NEVER modified.
    """

    sentiment = analyze_shadow_sentiment(
        stock_indicators,
        nifty_indicators,
    )

    if record:
        record_shadow(
            symbol,
            production_trade,
            sentiment,
        )

    return sentiment


if __name__ == "__main__":

    result = analyze_shadow_sentiment(
        {
            "ema9": 101,
            "ema20": 99,
            "vwap": 100,
            "ltp": 102,
            "rsi": 62,
            "supertrend_trend": "BUY",
        },
        {
            "ema9": 200,
            "ema20": 195,
            "vwap": 198,
            "ltp": 202,
            "adx": 28,
            "supertrend_trend": "BUY",
        },
    )

    print("=" * 60)
    print("🧠 PAISAAI SHADOW SENTIMENT")
    print("=" * 60)
    print("Engine      :", result["engine"])
    print("Version     :", result["version"])
    print("Sentiment   :", result["sentiment"])
    print("Score       :", result["score"])
    print("Confidence  :", result["confidence"], "%")
    print("Reasons     :")

    for reason in result["reasons"]:
        print(" •", reason)

    print("=" * 60)
