from data.nifty50 import NIFTY50

# Nifty 50 itself is subscribed as the live RS benchmark.
NIFTY_BENCHMARK_INSTRUMENT = "NSE_INDEX|Nifty 50"

# Validated sector indices for the current Upstox live feed.
# Nifty India Telecom is intentionally excluded because Upstox returns
# UDAPI100011 (Invalid Instrument key) for that key. Telecom therefore uses
# the existing peer-basket fallback instead of a fabricated benchmark.
SECTOR_INDEX_INSTRUMENTS = [
    "NSE_INDEX|Nifty Auto",
    "NSE_INDEX|Nifty Bank",
    "NSE_INDEX|Nifty Financial Services",
    "NSE_INDEX|Nifty FMCG",
    "NSE_INDEX|Nifty Healthcare Index",
    "NSE_INDEX|Nifty IT",
    "NSE_INDEX|Nifty Metal",
    "NSE_INDEX|Nifty Oil & Gas",
    "NSE_INDEX|Nifty Pharma",
    "NSE_INDEX|Nifty Energy",
    "NSE_INDEX|Nifty Realty",
    "NSE_INDEX|Nifty Consumer Durables",
    "NSE_INDEX|Nifty Infrastructure",
    "NSE_INDEX|Nifty India Consumption",
]

UNSUPPORTED_SECTOR_INDEX_INSTRUMENTS = [
    "NSE_INDEX|Nifty India Telecom",
]


def get_watchlist():
    """Return Nifty-50 stocks plus the live benchmark and sector feeds."""
    result = []
    seen = set()

    for instrument in [NIFTY_BENCHMARK_INSTRUMENT] + list(NIFTY50) + SECTOR_INDEX_INSTRUMENTS:
        if instrument not in seen:
            seen.add(instrument)
            result.append(instrument)

    return result
