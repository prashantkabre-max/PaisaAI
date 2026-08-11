"""
PaisaAI Context Score Engine

Technical MTF confidence remains the foundation.

Sentiment:
    aligned   -> positive
    opposing  -> negative

Market Depth:
    confirmed in trade direction -> positive
    confirmed opposite direction -> negative
    unconfirmed -> neutral

Maximum contribution:
    Sentiment : +/-10
    Depth     : +/-10
"""

from scanner.sentiment import calculate_sentiment


SENTIMENT_MAX_ADJUSTMENT = 10
DEPTH_MAX_ADJUSTMENT = 10


def calculate_context_score(
    technical_confidence,
    direction,
    stock_indicators=None,
    nifty_indicators=None,
    market_depth=None,
):
    technical = max(
        0,
        min(100, int(technical_confidence or 0)),
    )

    direction = str(direction or "").upper()

    sentiment = calculate_sentiment(
        stock_indicators or {},
        nifty_indicators or {},
    )

    raw_sentiment = float(
        sentiment.get("score", 0) or 0
    )

    directional_sentiment = raw_sentiment

    if direction == "SELL":
        directional_sentiment = -directional_sentiment

    directional_sentiment = max(
        -100,
        min(100, directional_sentiment),
    )

    sentiment_adjustment = round(
        (directional_sentiment / 100)
        * SENTIMENT_MAX_ADJUSTMENT
    )

    confirmed = str(
        (market_depth or {}).get("confirmed") or ""
    ).upper()

    if confirmed == direction and direction in ("BUY", "SELL"):
        depth_adjustment = DEPTH_MAX_ADJUSTMENT

    elif (
        confirmed in ("BUY", "SELL")
        and confirmed != direction
    ):
        depth_adjustment = -DEPTH_MAX_ADJUSTMENT

    else:
        depth_adjustment = 0

    final_confidence = max(
        0,
        min(
            100,
            technical
            + sentiment_adjustment
            + depth_adjustment,
        ),
    )

    if final_confidence >= 90:
        grade = "A+"
    elif final_confidence >= 75:
        grade = "A"
    else:
        grade = "IGNORE"

    return {
        "technical_confidence": technical,
        "sentiment_score": round(directional_sentiment),
        "sentiment_raw_score": round(raw_sentiment),
        "sentiment_adjustment": sentiment_adjustment,
        "depth_adjustment": depth_adjustment,
        "depth_confirmed": confirmed or None,
        "confidence": final_confidence,
        "grade": grade,
        "sentiment": sentiment,
    }
