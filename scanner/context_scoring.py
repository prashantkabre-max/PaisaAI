"""
PaisaAI Unified Context Score Engine

Technical MTF remains the foundation.

Additional engines:
    Sentiment
    Market Depth
    Relative Strength
    Sector Strength
    FII/DII Institutional Flow

These engines contribute directionally.

They do NOT introduce new rejection gates.

Maximum contributions:
    Sentiment        +/-10
    Market Depth     +/-10
    Relative Strength +/-5
    Sector Strength  +/-5
    FII/DII           +/-5
"""

from scanner.sentiment import calculate_sentiment

from scanner.relative_strength import (
    calculate_relative_strength,
)

from scanner.sector_strength import (
    calculate_sector_strength,
)

from scanner.institutional_flow import (
    calculate_institutional_score,
)


SENTIMENT_MAX_ADJUSTMENT = 10
DEPTH_MAX_ADJUSTMENT = 10
RS_MAX_ADJUSTMENT = 5
SECTOR_MAX_ADJUSTMENT = 5


def _directional_percent_score(
    value,
    direction,
    maximum,
    scale,
):
    if value is None:
        return 0

    try:
        value = float(value)
    except (TypeError, ValueError):
        return 0

    direction = str(
        direction or ""
    ).upper()

    if direction == "SELL":
        value = -value

    value = max(
        -scale,
        min(scale, value),
    )

    return round(
        (value / scale) * maximum
    )


def calculate_context_score(
    technical_confidence,
    direction,
    stock_indicators=None,
    nifty_indicators=None,
    market_depth=None,
    sector_change=None,
    institutional_flow=None,
):
    technical = max(
        0,
        min(
            100,
            int(
                technical_confidence or 0
            ),
        ),
    )

    direction = str(
        direction or ""
    ).upper()

    stock_indicators = (
        stock_indicators or {}
    )

    nifty_indicators = (
        nifty_indicators or {}
    )

    # ============================================================
    # SENTIMENT
    # ============================================================

    sentiment = calculate_sentiment(
        stock_indicators,
        nifty_indicators,
    )

    raw_sentiment = float(
        sentiment.get("score", 0) or 0
    )

    directional_sentiment = raw_sentiment

    if direction == "SELL":
        directional_sentiment = (
            -directional_sentiment
        )

    directional_sentiment = max(
        -100,
        min(100, directional_sentiment),
    )

    sentiment_adjustment = round(
        (
            directional_sentiment
            / 100
        )
        * SENTIMENT_MAX_ADJUSTMENT
    )

    # ============================================================
    # MARKET DEPTH
    # ============================================================

    confirmed = str(
        (market_depth or {}).get(
            "confirmed"
        )
        or ""
    ).upper()

    if (
        confirmed == direction
        and direction in ("BUY", "SELL")
    ):
        depth_adjustment = (
            DEPTH_MAX_ADJUSTMENT
        )

    elif (
        confirmed in ("BUY", "SELL")
        and confirmed != direction
    ):
        depth_adjustment = (
            -DEPTH_MAX_ADJUSTMENT
        )

    else:
        depth_adjustment = 0

    # ============================================================
    # RELATIVE STRENGTH
    # ============================================================

    stock_change = (
        stock_indicators.get(
            "change_percent"
        )
    )

    nifty_change = (
        nifty_indicators.get(
            "change_percent"
        )
    )

    relative_strength = (
        calculate_relative_strength(
            stock_change,
            nifty_change,
        )
    )

    rs_value = None

    if relative_strength:
        rs_value = relative_strength.get(
            "relative_strength"
        )

    relative_strength_adjustment = (
        _directional_percent_score(
            rs_value,
            direction,
            RS_MAX_ADJUSTMENT,
            2.0,
        )
    )

    # ============================================================
    # SECTOR STRENGTH
    # ============================================================

    sector_strength = (
        calculate_sector_strength(
            sector_change
        )
    )

    sector_value = None

    if sector_strength:
        sector_value = (
            sector_strength.get(
                "sector_strength"
            )
        )

    sector_adjustment = (
        _directional_percent_score(
            sector_value,
            direction,
            SECTOR_MAX_ADJUSTMENT,
            2.0,
        )
    )

    # ============================================================
    # FII / DII
    # ============================================================

    institutional = (
        calculate_institutional_score(
            institutional_flow,
            direction,
        )
    )

    institutional_adjustment = (
        institutional["adjustment"]
    )

    # ============================================================
    # FINAL
    # ============================================================

    final_confidence = max(
        0,
        min(
            100,
            technical
            + sentiment_adjustment
            + depth_adjustment
            + relative_strength_adjustment
            + sector_adjustment
            + institutional_adjustment,
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

        "sentiment_score": round(
            directional_sentiment
        ),
        "sentiment_raw_score": round(
            raw_sentiment
        ),
        "sentiment_adjustment": (
            sentiment_adjustment
        ),

        "depth_adjustment": (
            depth_adjustment
        ),
        "depth_confirmed": (
            confirmed or None
        ),

        "relative_strength": (
            relative_strength
        ),
        "relative_strength_adjustment": (
            relative_strength_adjustment
        ),

        "sector_strength": (
            sector_strength
        ),
        "sector_adjustment": (
            sector_adjustment
        ),

        "institutional": institutional,
        "institutional_adjustment": (
            institutional_adjustment
        ),

        "confidence": final_confidence,
        "grade": grade,
        "sentiment": sentiment,
    }
