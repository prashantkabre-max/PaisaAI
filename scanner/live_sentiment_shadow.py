"""
PaisaAI Live / Replay Shadow Sentiment Adapter

The actual calculation lives in scanner.sentiment.

This module preserves the existing Live/Replay API while ensuring
both modes use exactly the same engine.
"""

import json
from datetime import datetime
from pathlib import Path

from scanner.sentiment import (
    ENGINE_NAME,
    ENGINE_VERSION,
    calculate_sentiment,
)

LOG_FILE = Path("logs/shadow_sentiment.jsonl")


def analyze_shadow_sentiment(stock, nifty=None):
    result = calculate_sentiment(
        stock,
        nifty,
    )

    result = dict(result)
    result["timestamp"] = datetime.now().isoformat()

    return result


def record_shadow(symbol, production_trade, sentiment):

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
        "engine": ENGINE_NAME,
        "engine_version": ENGINE_VERSION,
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
    record=True  -> Live observation/logging
    record=False -> Replay/test observation only

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
