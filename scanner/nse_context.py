"""PaisaAI NSE-first live context provider.

NSE is the preferred source for:
- Nifty 50 benchmark change
- NSE sector-index change
- equity market depth (best 5 bid/ask levels when available)
- FII/FPI + DII daily cash-market flow

The provider is deliberately observation-only. It does not touch trade
accounting, entries, exits, targets or stop-loss logic.
"""

from datetime import date, datetime, timedelta
import threading

import requests


BASE = "https://www.nseindia.com"
HOME = BASE + "/"
ALL_INDICES = BASE + "/api/allIndices"
QUOTE_EQUITY = BASE + "/api/quote-equity"
FII_DII = BASE + "/api/fiidiiTradeReact"

TIMEOUT = 8
CACHE_SECONDS = 20
DEPTH_CACHE_SECONDS = 60

_session = None
_lock = threading.Lock()
_indices_cache = {"at": None, "data": None}
_depth_cache = {}
_fii_cache = {"at": None, "data": None}


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 "
        "Chrome/120.0.0.0 Mobile Safari/537.36"
    ),
    "Accept": "application/json,text/plain,*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": BASE + "/",
    "Connection": "keep-alive",
}


# NSE sector index names -> PaisaAI sector keys.
_INDEX_SECTOR_ALIASES = {
    "NIFTY AUTO": "AUTO",
    "NIFTY BANK": "BANK",
    "NIFTY FINANCIAL SERVICES": "FINANCIAL_SERVICES",
    "NIFTY FMCG": "FMCG",
    "NIFTY HEALTHCARE INDEX": "HEALTHCARE",
    "NIFTY IT": "IT",
    "NIFTY METAL": "METAL",
    "NIFTY OIL & GAS": "OIL_GAS",
    "NIFTY OIL AND GAS": "OIL_GAS",
    "NIFTY PHARMA": "PHARMA",
    "NIFTY ENERGY": "POWER",
    "NIFTY POWER": "POWER",
    "NIFTY REALTY": "REALTY",
    "NIFTY CONSUMER DURABLES": "CONSUMER_DURABLES",
    "NIFTY INFRASTRUCTURE": "INFRASTRUCTURE",
    "NIFTY INDIA CONSUMPTION": "CONSUMPTION",
}


def _normalise_name(value):
    return " ".join(str(value or "").upper().replace("-", " ").split())


def _session_get():
    global _session
    with _lock:
        if _session is None:
            _session = requests.Session()
            _session.headers.update(HEADERS)
        return _session


def _get_json(url, params=None):
    s = _session_get()
    # Establish NSE cookies before API calls. NSE's public endpoints may
    # reject a cold API request without the website session.
    try:
        s.get(HOME, timeout=TIMEOUT)
    except Exception:
        pass
    response = s.get(url, params=params, timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()


def _float(value):
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def _index_rows(payload):
    if isinstance(payload, dict):
        rows = payload.get("data")
        if isinstance(rows, list):
            return rows
    if isinstance(payload, list):
        return payload
    return []


def refresh_indices(force=False):
    now = datetime.now()
    if (
        not force
        and _indices_cache["at"]
        and (now - _indices_cache["at"]).total_seconds() < CACHE_SECONDS
    ):
        return _indices_cache["data"] or []

    try:
        rows = _index_rows(_get_json(ALL_INDICES))
        _indices_cache["at"] = now
        _indices_cache["data"] = rows
        return rows
    except Exception:
        return _indices_cache["data"] or []


def _row_name(row):
    return _normalise_name(
        row.get("index")
        or row.get("indexSymbol")
        or row.get("name")
    )


def _row_change(row):
    for key in ("percentChange", "perChange", "pChange", "%Chng"):
        value = _float(row.get(key))
        if value is not None:
            return value
    return None


def get_nifty_change():
    for row in refresh_indices():
        if _row_name(row) in ("NIFTY 50", "NIFTY50"):
            value = _row_change(row)
            if value is not None:
                return round(value, 4)
    return None


def get_sector_changes():
    result = {}
    for row in refresh_indices():
        sector = _INDEX_SECTOR_ALIASES.get(_row_name(row))
        value = _row_change(row)
        if sector and value is not None:
            result[sector] = round(value, 4)
    return result


def _extract_levels(book, side):
    if not isinstance(book, list):
        return []
    levels = []
    for item in book[:5]:
        if isinstance(item, dict):
            price = (
                item.get("price")
                or item.get("bidPrice")
                or item.get("askPrice")
            )
            qty = (
                item.get("quantity")
                or item.get("qty")
                or item.get("buyQuantity" if side == "bid" else "sellQuantity")
            )
            if price is not None and qty is not None:
                levels.append({"price": price, "quantity": qty})
    return levels


def get_market_depth(symbol, force=False):
    """Return NSE best-five depth in the shape expected by market_depth.py."""
    symbol = str(symbol or "").split("|", 1)[-1].upper()
    if not symbol or symbol in ("NIFTY 50", "NIFTY BANK"):
        return None

    now = datetime.now()
    cached = _depth_cache.get(symbol)
    if (
        not force
        and cached
        and (now - cached["at"]).total_seconds() < DEPTH_CACHE_SECONDS
    ):
        return cached.get("depth")

    try:
        payload = _get_json(
            QUOTE_EQUITY,
            params={"symbol": symbol, "section": "trade_info"},
        )
        book = payload.get("marketDeptOrderBook") or payload.get("marketDeptOrderBook")
        if not isinstance(book, dict):
            book = payload.get("marketDeptOrderBook", {})

        bids = (
            book.get("bid")
            or book.get("bids")
            or payload.get("bid")
            or payload.get("bids")
            or []
        )
        asks = (
            book.get("ask")
            or book.get("asks")
            or payload.get("ask")
            or payload.get("asks")
            or []
        )

        bids = _extract_levels(bids, "bid")
        asks = _extract_levels(asks, "ask")

        if not bids or not asks:
            return None

        depth = {"bids": bids, "asks": asks, "source": "NSE"}
        _depth_cache[symbol] = {"at": now, "depth": depth}
        return depth
    except Exception:
        return None


def _parse_flow_rows(payload):
    rows = _index_rows(payload)
    result = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        day = row.get("date") or row.get("Date")
        if not day:
            continue
        text = str(day).strip()
        parsed = None
        for fmt in ("%d-%b-%Y", "%d-%b-%y", "%d/%m/%Y", "%Y-%m-%d"):
            try:
                parsed = datetime.strptime(text, fmt).date()
                break
            except ValueError:
                pass
        if parsed is None:
            continue

        category = str(
            row.get("category") or row.get("Category") or ""
        ).upper()
        buy = _float(row.get("buyValue") or row.get("buy_value") or row.get("buyAmount"))
        sell = _float(row.get("sellValue") or row.get("sell_value") or row.get("sellAmount"))
        net = _float(row.get("netValue") or row.get("net_value") or row.get("netAmount"))

        if net is None and buy is not None and sell is not None:
            net = buy - sell

        result.append({
            "date": parsed.isoformat(),
            "category": category,
            "buy": buy,
            "sell": sell,
            "net": net,
        })
    return result


def refresh_fii_dii(force=False):
    now = datetime.now()
    if (
        not force
        and _fii_cache["at"]
        and (now - _fii_cache["at"]).total_seconds() < 300
    ):
        return _fii_cache["data"]

    try:
        payload = _get_json(FII_DII)
        rows = _parse_flow_rows(payload)
        if not rows:
            return _fii_cache["data"]

        today = date.today()
        grouped = {}
        for row in rows:
            d = date.fromisoformat(row["date"])
            if d > today:
                continue
            grouped.setdefault(row["date"], {})
            cat = row["category"]
            if "FII" in cat or "FPI" in cat:
                grouped[row["date"]]["fii"] = row
            elif "DII" in cat:
                grouped[row["date"]]["dii"] = row

        valid_dates = sorted(
            d for d in grouped
            if grouped[d].get("fii") or grouped[d].get("dii")
        )
        if not valid_dates:
            return _fii_cache["data"]

        latest = valid_dates[-1]
        g = grouped[latest]
        snapshot = {
            "date": latest,
            "fii": g.get("fii"),
            "dii": g.get("dii"),
            "source": "NSE",
            "available": bool(g.get("fii") or g.get("dii")),
        }
        _fii_cache["at"] = now
        _fii_cache["data"] = snapshot
        return snapshot
    except Exception:
        return _fii_cache["data"]


def flow_for_date(requested_date):
    snapshot = refresh_fii_dii()
    if not snapshot:
        return None

    # NSE FII/DII is daily and normally unavailable for the current session
    # until after the day's reporting. Never invent a current-day zero.
    req = requested_date
    if hasattr(req, "date"):
        req = req.date()
    if isinstance(req, str):
        try:
            req = date.fromisoformat(req[:10])
        except ValueError:
            req = date.today()
    if not isinstance(req, date):
        req = date.today()

    snap_day = date.fromisoformat(snapshot["date"])
    if snap_day > req:
        return None
    return snapshot
