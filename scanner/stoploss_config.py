"""
PaisaAI Stop Loss Configuration
"""

# Available Modes:
#
# ATR
# SESSION
# SWING
# ORB
# SMART
#
# Change this single line to test different strategies.

STOPLOSS_MODE = "ATR"


# Runtime override.
# Production uses STOPLOSS_MODE.
# Replay may temporarily change CURRENT_STOPLOSS_MODE.
CURRENT_STOPLOSS_MODE = STOPLOSS_MODE
