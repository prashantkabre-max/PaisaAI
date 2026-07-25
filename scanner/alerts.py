from datetime import datetime, timedelta

_last_alerts = {}

ALERT_COOLDOWN = timedelta(minutes=5)


def should_alert(symbol, action, grade, confidence):
    if action == "IGNORE":
        return False

    key = f"{symbol}:{action}"

    now = datetime.now()

    if key in _last_alerts:
        if now - _last_alerts[key] < ALERT_COOLDOWN:
            return False

    _last_alerts[key] = now
    return True


def build_alert(result):
    return {
        "symbol": result["symbol"],
        "action": result["action"],
        "grade": result["grade"],
        "confidence": result["confidence"],
        "risk": result["risk"],
        "market_sentiment": result["market_sentiment"],
        "stock_sentiment": result["stock_sentiment"],
        "trade_timing": result["trade_timing"],
        "reasons": result["reasons"],
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


def process_alert(result):
    if not should_alert(
        result["symbol"],
        result["action"],
        result["grade"],
        result["confidence"],
    ):
        return None

    return build_alert(result)
