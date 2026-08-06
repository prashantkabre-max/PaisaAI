"""
PaisaAI Nifty Engine Configuration
Version 1.0
"""

# ---------- Indicator Thresholds ----------

RSI_BULLISH = 60
RSI_BEARISH = 40

ADX_TRENDING = 25

# ---------- Component Weights ----------

TREND_WEIGHT = 30
EMA_WEIGHT = 20
VWAP_WEIGHT = 20
RSI_WEIGHT = 15
ADX_WEIGHT = 15

TOTAL_SCORE = (
    TREND_WEIGHT
    + EMA_WEIGHT
    + VWAP_WEIGHT
    + RSI_WEIGHT
    + ADX_WEIGHT
)

assert TOTAL_SCORE == 100

