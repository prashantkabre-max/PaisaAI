"""
PaisaAI Professional Risk Management Engine
"""

from scanner.settings import *


def calculate_risk(indicators, signal):

    ltp = indicators.get("ltp")
    atr = indicators.get("atr")

    day_high = indicators.get("high")
    day_low = indicators.get("low")

    swing_high = indicators.get("swing_high")
    swing_low = indicators.get("swing_low")

    if ltp is None or atr is None or atr <= 0:
        return None

    entry = round(ltp, 2)

    minimum_stop = max(
        atr * 1.25,
        entry * 0.003,      # 0.30%
    )

    if signal == "BUY":

        candidates = [
            entry - minimum_stop,
        ]

        if day_low is not None:
            candidates.append(day_low)

        if swing_low is not None:
            candidates.append(swing_low)

        stop_loss = min(candidates)

        risk = entry - stop_loss

        target1 = entry + (risk * 2.0)
        target2 = entry + (risk * 3.0)
        target3 = entry + (risk * 4.0)

    elif signal == "SELL":

        candidates = [
            entry + minimum_stop,
        ]

        if day_high is not None:
            candidates.append(day_high)

        if swing_high is not None:
            candidates.append(swing_high)

        stop_loss = max(candidates)

        risk = stop_loss - entry

        target1 = entry - (risk * 2.0)
        target2 = entry - (risk * 3.0)
        target3 = entry - (risk * 4.0)

    else:
        return None

    reward = abs(target1 - entry)

    return {
        "entry": round(entry, 2),
        "stop_loss": round(stop_loss, 2),
        "target1": round(target1, 2),
        "target2": round(target2, 2),
        "target3": round(target3, 2),
        "risk": round(risk, 2),
        "reward": round(reward, 2),
        "risk_reward": round(reward / risk, 2) if risk else 0,
    }
