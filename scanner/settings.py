"""
PaisaAI Scanner Settings
Edit these values to tune the scanner.
"""

# ==========================
# EMA
# ==========================

EMA_FAST = 9
EMA_SLOW = 20

# ==========================
# Relative Volume
# ==========================

RVOL_HIGH = 2.0
RVOL_MEDIUM = 1.5
RVOL_LOW = 1.0

# ==========================
# Score Thresholds
# ==========================

A_PLUS_SCORE = 80
A_SCORE = 60
A_MINUS_SCORE = 40

# ==========================
# Price Change %
# ==========================

PRICE_CHANGE_HIGH = 2.0
PRICE_CHANGE_MEDIUM = 1.0

# ==========================
# Scanner
# ==========================

MAX_HISTORY = 500

# ==========================
# Indicator Settings
# ==========================

RSI_PERIOD = 14

MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9

ATR_PERIOD = 14
ADX_PERIOD = 14

SUPERTREND_PERIOD = 10
SUPERTREND_MULTIPLIER = 3
# ==========================
# Rule Thresholds
# ==========================
EMA_MIN_GAP_PERCENT = 0.10
ADX_MIN = 20
RSI_BUY_MIN = 20
RSI_BUY_MAX = 80
RSI_SELL_MIN = 20
RSI_SELL_MAX = 80
RVOL_MIN = 1.20

# ==========================
# Scoring Weights
# ==========================

EMA_WEIGHT = 20
VWAP_WEIGHT = 15
SUPERTREND_WEIGHT = 15
RVOL_WEIGHT = 15
ADX_WEIGHT = 10
MACD_WEIGHT = 10
RSI_WEIGHT = 5
PRICE_CHANGE_WEIGHT = 5
OPEN_WEIGHT = 3
HIGH_LOW_WEIGHT = 2

# ==========================
# Risk Management
# ==========================
ATR_STOP_MULTIPLIER = 2.0
ATR_TARGET1_MULTIPLIER = 4.0
ATR_TARGET2_MULTIPLIER = 6.0
ATR_TARGET3_MULTIPLIER = 8.0

# ==========================
# Multi Time Frame (MTF)
# ==========================

MTF_WEIGHTS = {
    "1m": 25,
    "3m": 20,
    "5m": 20,
    "15m": 15,
    "30m": 10,
    "60m": 10,
}

# Minimum confidence required
# for a timeframe to be considered aligned
MTF_ALIGNMENT_MIN_SCORE = 75

# Reserved for future divergence filter
MTF_MIN_SCORE_DIFFERENCE = 10



# ==========================================================
# PAISAAI RISK MANAGER
# ==========================================================

MAX_RISK_PER_TRADE = 2000

