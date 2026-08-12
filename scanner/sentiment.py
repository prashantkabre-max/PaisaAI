"""
PaisaAI Sentiment Engine V2

Single calculation source shared by Live and Replay.

Observation-only until explicitly promoted into production
decision scoring.
"""

ENGINE_NAME = "Sentiment Engine"
ENGINE_VERSION = "2.0"

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


def calculate_sentiment(stock=None, nifty=None):
    """
    Calculate the unified V2 sentiment.

    The exact same calculation is used by:
    - Live shadow mode
    - Replay shadow mode

    Missing data contributes zero.
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
        "engine": ENGINE_NAME,
        "version": ENGINE_VERSION,
        "score": score,
        "confidence": _confidence(score),
        "sentiment": _direction(score),
        "reasons": reasons,
    }


def score_nifty(nifty):
    return calculate_sentiment({}, nifty)


if __name__ == "__main__":

    result = calculate_sentiment(
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
    print("🧠 PAISAAI SENTIMENT ENGINE")
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
