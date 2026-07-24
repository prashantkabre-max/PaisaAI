"""
NIFTY 200 Universe

Initially we'll test with a few highly liquid stocks.
Once the engine is stable, we'll replace this list with the complete
NIFTY 200 instrument universe.
"""

SYMBOL_MAP = {
    "NSE_INDEX|Nifty 50": "NIFTY50",
    "NSE_INDEX|Nifty Bank": "BANKNIFTY",

    "NSE_EQ|INE467B01029": "TCS",
    "NSE_EQ|INE009A01021": "INFY",
    "NSE_EQ|INE040A01034": "HDFCBANK",
    "NSE_EQ|INE002A01018": "RELIANCE",
   # "NSE_EQ|INE237A01028": "KOTAKBANK",
}

NIFTY200 = list(SYMBOL_MAP.keys())
