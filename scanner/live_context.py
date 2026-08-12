"""
PaisaAI Live Context Market State

Provides the live inputs required by the shared context scorer:
- Nifty benchmark change for Relative Strength
- Sector change for Sector Strength

The sector value prefers a genuine NSE sector-index snapshot when one is
available. Until such a feed is subscribed, it falls back to the average
performance of the mapped live Nifty constituents in that sector. This keeps
the engine data-driven and avoids a permanent 0/N/A state.
"""

from scanner.runtime import MARKET_STATE


# Live benchmark/context subscriptions.
# Nifty 50 is required for order-independent Relative Strength.
NIFTY_BENCHMARK_INSTRUMENT = "NSE_INDEX|Nifty 50"


# Broad NSE sector buckets for the current Nifty-50 universe.
# The mapping is deliberately explicit so a stock cannot silently become
# its own sector benchmark.
STOCK_SECTOR = {
    "ADANIENT": "INFRASTRUCTURE",
    "ADANIPORTS": "INFRASTRUCTURE",
    "APOLLOHOSP": "HEALTHCARE",
    "ASIANPAINT": "CONSUMER_DURABLES",
    "AXISBANK": "BANK",
    "BAJAJ-AUTO": "AUTO",
    "BAJAJFINSV": "FINANCIAL_SERVICES",
    "BAJFINANCE": "FINANCIAL_SERVICES",
    "BEL": "INFRASTRUCTURE",
    "BHARTIARTL": "TELECOM",
    "CIPLA": "PHARMA",
    "COALINDIA": "METAL",
    "DRREDDY": "PHARMA",
    "EICHERMOT": "AUTO",
    "ETERNAL": "CONSUMPTION",
    "GRASIM": "INFRASTRUCTURE",
    "HCLTECH": "IT",
    "HDFCBANK": "BANK",
    "HDFCLIFE": "FINANCIAL_SERVICES",
    "HEROMOTOCO": "AUTO",
    "HINDALCO": "METAL",
    "HINDUNILVR": "FMCG",
    "ICICIBANK": "BANK",
    "INDUSINDBK": "BANK",
    "INFY": "IT",
    "ITC": "FMCG",
    "JIOFIN": "FINANCIAL_SERVICES",
    "JSWSTEEL": "METAL",
    "KOTAKBANK": "BANK",
    "LT": "INFRASTRUCTURE",
    "M&M": "AUTO",
    "MARUTI": "AUTO",
    "MAXHEALTH": "HEALTHCARE",
    "NESTLEIND": "FMCG",
    "NTPC": "POWER",
    "ONGC": "OIL_GAS",
    "POWERGRID": "POWER",
    "RELIANCE": "OIL_GAS",
    "SBILIFE": "FINANCIAL_SERVICES",
    "SBIN": "BANK",
    "SHRIRAMFIN": "FINANCIAL_SERVICES",
    "SUNPHARMA": "PHARMA",
    "TATACONSUM": "FMCG",
    "TATAMOTORS": "AUTO",
    "TMPV": "AUTO",
    "TATASTEEL": "METAL",
    "TCS": "IT",
    "TECHM": "IT",
    "TITAN": "CONSUMER_DURABLES",
    "TRENT": "CONSUMPTION",
    "ULTRACEMCO": "INFRASTRUCTURE",
    "WIPRO": "IT",
}


# Optional real sector-index keys. If the live feed is expanded later, these
# values automatically take priority over the peer-basket fallback.
SECTOR_INDEX_BY_SECTOR = {
    "AUTO": "NSE_INDEX|Nifty Auto",
    "BANK": "NSE_INDEX|Nifty Bank",
    "FINANCIAL_SERVICES": "NSE_INDEX|Nifty Financial Services",
    "FMCG": "NSE_INDEX|Nifty FMCG",
    "HEALTHCARE": "NSE_INDEX|Nifty Healthcare Index",
    "IT": "NSE_INDEX|Nifty IT",
    "METAL": "NSE_INDEX|Nifty Metal",
    "OIL_GAS": "NSE_INDEX|Nifty Oil & Gas",
    "PHARMA": "NSE_INDEX|Nifty Pharma",
    "POWER": "NSE_INDEX|Nifty Energy",
    "REALTY": "NSE_INDEX|Nifty Realty",
    "CONSUMER_DURABLES": "NSE_INDEX|Nifty Consumer Durables",
    "INFRASTRUCTURE": "NSE_INDEX|Nifty Infrastructure",
    "CONSUMPTION": "NSE_INDEX|Nifty India Consumption",
    # TELECOM has no validated Upstox index key in this live feed.
    # BHARTIARTL therefore uses the peer-basket fallback when peers exist.
}

INDEX_TO_SECTOR = {
    instrument: sector
    for sector, instrument in SECTOR_INDEX_BY_SECTOR.items()
}


def _symbol(instrument_key):
    return str(instrument_key or "").split("|", 1)[-1].upper()


def _change_percent(market):
    ltp = market.get("ltp")
    previous_close = market.get("previous_close")
    if ltp is None or previous_close in (None, 0):
        return None
    try:
        return round(((float(ltp) - float(previous_close)) / float(previous_close)) * 100, 4)
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def update_live_context(market):
    """Update benchmark, sector-index and stock peer snapshots from a feed tick."""
    if not isinstance(market, dict):
        return

    instrument = market.get("symbol")
    if not instrument:
        return

    change = _change_percent(market)
    if change is None:
        return

    if instrument == NIFTY_BENCHMARK_INSTRUMENT:
        MARKET_STATE["NIFTY_CONTEXT"] = {
            "change_percent": change,
            "source": "UPSTOX_LIVE",
        }
        return

    sector = INDEX_TO_SECTOR.get(instrument)
    if sector:
        MARKET_STATE.setdefault("SECTOR_CHANGES", {})[sector] = change
        return

    symbol = _symbol(instrument)
    sector = STOCK_SECTOR.get(symbol)
    if sector:
        MARKET_STATE.setdefault("STOCK_CHANGES", {})[symbol] = change


def get_nifty_context(fallback=None):
    """Return the latest order-independent Nifty benchmark snapshot."""
    context = MARKET_STATE.get("NIFTY_CONTEXT")
    if context and context.get("change_percent") is not None:
        return {"change_percent": context["change_percent"]}

    return fallback or {}


def get_sector_for_stock(instrument_key):
    return STOCK_SECTOR.get(_symbol(instrument_key))


def get_sector_change(instrument_key, explicit_change=None, explicit_sector=None):
    """
    Resolve sector change in priority order:
    1. Explicit value already attached to the stock snapshot.
    2. Real sector-index snapshot.
    3. Live peer-basket average from the mapped Nifty universe.
    """
    if explicit_change is not None:
        return explicit_change

    sector = explicit_sector or get_sector_for_stock(instrument_key)
    if not sector:
        return None

    index_change = MARKET_STATE.get("SECTOR_CHANGES", {}).get(sector)
    if index_change is not None:
        return round(float(index_change), 4)

    changes = MARKET_STATE.get("STOCK_CHANGES", {})
    peers = [
        value
        for symbol, value in changes.items()
        if STOCK_SECTOR.get(symbol) == sector
        and symbol != _symbol(instrument_key)
        and value is not None
    ]

    if not peers:
        return None

    return round(sum(peers) / len(peers), 4)
