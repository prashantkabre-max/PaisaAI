"""
PaisaAI Live Shadow Sentiment
Observation-only engine.

IMPORTANT:
This module must never modify production trade decisions,
entries, exits, stop-losses, targets, or grades.
"""

import json
from datetime import datetime
from pathlib import Path


LOG_FILE = Path("logs/shadow_sentiment.jsonl")


def _direction(score):
    if score >= 20:
        return "BULLISH"
    if score <= -20:
        return "BEARISH"
    return "NEUTRAL"


def _confidence(score):
    return min(100, max(0, int(abs(score))))


def analyze_shadow_sentiment(stock, nifty=None):
    """
    Observation-only sentiment assessment.

    Score range: -100 to +100.
    """

    stock = stock or {}
    nifty = nifty or {}

    score = 0
    reasons = []

    # -------------------------
    # MARKET / NIFTY
    # -------------------------
    n_ema9 = nifty.get("ema9")
    n_ema20 = nifty.get("ema20")
    n_adx = nifty.get("adx")

    if n_ema9 is not None and n_ema20 is not None:
        if n_ema9 > n_ema20:
            score += 30
            reasons.append("NIFTY bullish EMA")
        elif n_ema9 < n_ema20:
            score -= 30
            reasons.append("NIFTY bearish EMA")

    if n_adx is not None:
        if n_adx >= 25:
            reasons.append("NIFTY trend strong")
        elif n_adx < 20:
            score = int(score * 0.75)
            reasons.append("NIFTY trend weak")

    # -------------------------
    # STOCK
    # -------------------------
    ema9 = stock.get("ema9")
    ema20 = stock.get("ema20")
    vwap = stock.get("vwap")
    ltp = stock.get("ltp")
    rsi = stock.get("rsi")
    supertrend = stock.get("supertrend_trend")

    if ema9 is not None and ema20 is not None:
        if ema9 > ema20:
            score += 25
            reasons.append("stock EMA bullish")
        elif ema9 < ema20:
            score -= 25
            reasons.append("stock EMA bearish")

    if ltp is not None and vwap is not None:
        if ltp > vwap:
            score += 20
            reasons.append("above VWAP")
        elif ltp < vwap:
            score -= 20
            reasons.append("below VWAP")

    if supertrend is not None:
        trend = str(supertrend).upper()
        if "BUY" in trend or "BULL" in trend or "UP" in trend:
            score += 15
            reasons.append("supertrend bullish")
        elif "SELL" in trend or "BEAR" in trend or "DOWN" in trend:
            score -= 15
            reasons.append("supertrend bearish")

    if rsi is not None:
        if 55 <= rsi <= 70:
            score += 10
            reasons.append("RSI bullish zone")
        elif 30 <= rsi <= 45:
            score -= 10
            reasons.append("RSI bearish zone")

    score = max(-100, min(100, score))

    result = {
        "timestamp": datetime.now().isoformat(),
        "score": score,
        "confidence": _confidence(score),
        "sentiment": _direction(score),
        "reasons": reasons,
    }

    return result


def record_shadow(symbol, production_trade, sentiment):
    """
    Append-only shadow record.
    Never changes production_trade.
    """

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

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
        f.write(json.dumps(record, separators=(",", ":")) + "\n")


def run_shadow(symbol, production_trade, stock_indicators, nifty_indicators):
    """
    Run shadow analysis and return the observation.

    Production trade object is NEVER modified.
    """

    sentiment = analyze_shadow_sentiment(
        stock_indicators,
        nifty_indicators,
    )

    record_shadow(
        symbol,
        production_trade,
        sentiment,
    )

    return sentiment
