"""
PaisaAI Runtime State
"""

MARKET_STATE = {
    "NIFTY": None,
    "BANKNIFTY": None,

    # Institutional daily context.
    "INSTITUTIONAL_FLOW": None,

    # Optional real sector feed.
    # Keyed by stock symbol or sector identifier.
    "SECTOR_CHANGES": {},
}

# ==========================================================
# Runtime Risk Mode
# ==========================================================

RISK_MODE = "production"

def set_risk_mode(mode):
    global RISK_MODE
    RISK_MODE = mode.lower()

def get_risk_mode():
    return RISK_MODE
