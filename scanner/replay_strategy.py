"""
Replay-only strategy configuration.

Changing these values affects ONLY Replay V2.
Production remains untouched.
"""

STOPLOSS_MODE = "SMART"

AVAILABLE_STOPLOSS = [
    "ATR",
    "SESSION",
    "SWING",
    "ORB",
    "SMART",
]

PRINT_STRATEGY = True

