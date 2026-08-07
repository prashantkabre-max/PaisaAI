"""
PaisaAI Professional Risk Management Engine
"""

from scanner.settings import *
from scanner.runtime import get_risk_mode
from scanner.stoploss_config import STOPLOSS_MODE




def get_stop_loss_mode():
    """
    Central dispatcher for stop-loss strategies.
    Behaviour is unchanged for now.
    """

    mode = STOPLOSS_MODE.upper()

    if mode == "ATR":
        return "ATR"

    if mode == "SESSION":
        return "SESSION"

    if mode == "SWING":
        return "SWING"

    if mode == "ORB":
        return "ORB"

    return "SMART"




def calculate_atr_stop(*args, **kwargs):
    return None


def calculate_session_stop(*args, **kwargs):
    return None


def calculate_swing_stop(*args, **kwargs):
    return None


def calculate_orb_stop(*args, **kwargs):
    return None


def calculate_smart_stop(*args, **kwargs):
    return None


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

    mode = get_risk_mode()

    if mode == "diagnostic":
        atr_mult = 0.25
        rr1, rr2, rr3 = 0.25, 0.50, 0.75
    elif mode == "aggressive":
        atr_mult = 0.75
        rr1, rr2, rr3 = 2.5, 4.0, 6.0
    else:
        atr_mult = 1.25
        rr1, rr2, rr3 = 1.0, 1.5, 2.0

    minimum_stop = max(
        atr * atr_mult,
        entry * 0.003,      # 0.30%
    )

    mode = get_stop_loss_mode()

    if mode == "ATR":
        print("🟢 STOPLOSS MODE : ATR")

    elif mode == "SESSION":
        print("🟢 STOPLOSS MODE : SESSION")

    elif mode == "SWING":
        print("🟢 STOPLOSS MODE : SWING")

    elif mode == "ORB":
        print("🟢 STOPLOSS MODE : ORB")

    else:
        print("🟢 STOPLOSS MODE : SMART")

    if signal == "BUY":

        candidates = [
            entry - minimum_stop,
        ]

        if day_low is not None:
            candidates.append(day_low)

        if swing_low is not None:
            candidates.append(swing_low)

        stop_loss = min(candidates)

        stop_loss = day_low if day_low is not None else stop_loss
        risk = entry - stop_loss

        target1 = entry + (risk * rr1)
        target2 = entry + (risk * rr2)
        target3 = entry + (risk * rr3)

    elif signal == "SELL":

        candidates = [
            entry + minimum_stop,
        ]

        if day_high is not None:
            candidates.append(day_high)

        if swing_high is not None:
            candidates.append(swing_high)

        stop_loss = max(candidates)

        stop_loss = day_high if day_high is not None else stop_loss
        risk = stop_loss - entry

        target1 = entry - (risk * rr1)
        target2 = entry - (risk * rr2)
        target3 = entry - (risk * rr3)

    else:
        return None

    reward = abs(target1 - entry)

    per_share_risk = abs(risk)

    recommended_qty = max(
        1,
        int(MAX_RISK_PER_TRADE / per_share_risk)
    ) if per_share_risk else 1

    capital_required = recommended_qty * entry

    print("\n================ STOP LOSS DEBUG ================")
    print(f"Entry Price     : {entry}")
    print(f"Chosen Stop     : {stop_loss}")
    print(f"Per Share Risk  : {per_share_risk}")
    print("=================================================\n")

    return {
        "entry": round(entry, 2),
        "stop_loss": round(stop_loss, 2),
        "target1": round(target1, 2),
        "target2": round(target2, 2),
        "target3": round(target3, 2),
        "risk": round(risk, 2),
        "per_share_risk": round(per_share_risk, 2),
        "recommended_qty": recommended_qty,
        "capital_required": round(capital_required, 2),
        "reward": round(reward, 2),
        "risk_reward": round(reward / risk, 2) if risk else 0,
    }
