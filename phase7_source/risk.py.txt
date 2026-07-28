"""
PaisaAI Risk Management Engine
"""

from scanner.settings import *


def calculate_risk(indicators, signal):
    """
    Returns entry, stop-loss, targets and risk-reward.
    """

    ltp = indicators.get("ltp")
    atr = indicators.get("atr")

    if ltp is None or atr is None or atr <= 0:
        return None

    entry = round(ltp, 2)

    if signal == "BUY":

        stop_loss = round(entry - atr, 2)

        target1 = round(entry + (atr * 2), 2)
        target2 = round(entry + (atr * 3), 2)
        target3 = round(entry + (atr * 4), 2)

    elif signal == "SELL":

        stop_loss = round(entry + atr, 2)

        target1 = round(entry - (atr * 2), 2)
        target2 = round(entry - (atr * 3), 2)
        target3 = round(entry - (atr * 4), 2)

    else:
        return None

    risk = abs(entry - stop_loss)
    reward = abs(target1 - entry)

    rr = round(reward / risk, 2) if risk else 0

    return {
        "entry": entry,
        "stop_loss": stop_loss,
        "target1": target1,
        "target2": target2,
        "target3": target3,
        "risk": round(risk, 2),
        "reward": round(reward, 2),
        "risk_reward": rr,
    }
