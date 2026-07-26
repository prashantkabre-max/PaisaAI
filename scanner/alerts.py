"""
PaisaAI Alert Engine
"""

from datetime import datetime, timedelta

_last_alerts = {}

ALERT_COOLDOWN = timedelta(minutes=5)


def should_alert(trade):
    """
    Prevent duplicate alerts within cooldown.
    """

    if trade is None:
        return False

    if trade["action"] == "IGNORE":
        return False

    key = f'{trade["symbol"]}:{trade["action"]}'

    now = datetime.now()

    if key in _last_alerts:
        if now - _last_alerts[key] < ALERT_COOLDOWN:
            return False

    _last_alerts[key] = now
    return True


def build_alert(trade):
    """
    Build a standard alert object.
    """

    return {
        "symbol": trade["symbol"],
        "action": trade["action"],
        "grade": trade["grade"],
        "confidence": trade["confidence"],
        "risk": trade["risk"],
        "market_sentiment": trade["market_sentiment"],
        "stock_sentiment": trade["stock_sentiment"],
        "trade_timing": trade["trade_timing"],
        "passed": trade["passed"],
        "failed": trade["failed"],
        "generated_at": datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        ),
    }


def process_alert(trade):
    """
    Returns an alert object if alert criteria are met.
    """

    if not should_alert(trade):
        return None

    return build_alert(trade)
