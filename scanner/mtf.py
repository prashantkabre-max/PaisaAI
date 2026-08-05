from scanner.scoring import calculate_score
from scanner.settings import (
    MTF_WEIGHTS,
    MTF_ALIGNMENT_MIN_SCORE,
    MTF_MIN_SCORE_DIFFERENCE,
)


def calculate_mtf_score(timeframe_indicators, direction="BUY"):
    """
    Calculate Multi-Timeframe (MTF) score.

    timeframe_indicators format:

    {
        "1m": indicators,
        "3m": indicators,
        "5m": indicators,
        "15m": indicators,
        "30m": indicators,
        "60m": indicators,
    }

    Returns a structure compatible with calculate_score().
    """

    weighted_score = 0
    max_score = 0

    passed = []
    failed = []
    timeframe_scores = {}

    base_result = None

    for tf, indicators in timeframe_indicators.items():

        result = calculate_score(indicators, direction)

        if tf == "1m":
            base_result = result

        timeframe_scores[tf] = result

        weight = MTF_WEIGHTS.get(tf, 0)

        weighted_score += result["confidence"] * weight
        max_score += 100 * weight

        if result["confidence"] >= MTF_ALIGNMENT_MIN_SCORE:
            passed.append(tf)
        else:
            failed.append(tf)

    if max_score == 0:
        confidence = 0
    else:
        confidence = round((weighted_score / max_score) * 100)

    if confidence >= 90:
        grade = "A+"
    elif confidence >= 75:
        grade = "A"
    else:
        grade = "IGNORE"

    return {
        "grade": grade,
        "confidence": confidence,
        "passed": base_result["passed"] if base_result else [],
        "failed": base_result["failed"] if base_result else [],
        "aligned_timeframes": passed,
        "failed_timeframes": failed,
        "timeframes": timeframe_scores,
    }
