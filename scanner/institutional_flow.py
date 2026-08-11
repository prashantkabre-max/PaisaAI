"""
PaisaAI Institutional Flow Engine

FII/DII data source:
    Upstox Market Information APIs.

Important:
    - Daily data only.
    - Replay uses the candle/replay date.
    - Live uses the latest available daily snapshot.
    - No current-day lookahead is injected into historical Replay.

FII:
    /v2/market/fii
    NSE_EQ|CASH

DII:
    /v2/market/dii
    NSE_EQ|CASH
"""

from datetime import datetime, timezone
from pathlib import Path

import requests

import config
from scanner.runtime import MARKET_STATE


BASE_URL = "https://api.upstox.com/v2"

FII_ENDPOINT = f"{BASE_URL}/market/fii"
DII_ENDPOINT = f"{BASE_URL}/market/dii"

TIMEOUT = 10

# Cache in memory for the current process.
_FLOW_CACHE = {}


def _headers():
    return {
        "Accept": "application/json",
        "Authorization": f"Bearer {config.ACCESS_TOKEN}",
    }


def _date_from_timestamp(timestamp):
    if timestamp is None:
        return None

    try:
        if isinstance(timestamp, (int, float)):
            dt = datetime.fromtimestamp(
                timestamp / 1000.0,
                tz=timezone.utc,
            )
        else:
            value = str(timestamp).replace("Z", "+00:00")
            dt = datetime.fromisoformat(value)

        return dt.date().isoformat()

    except Exception:
        return None


def _fetch_fii(date_from=None):

    params = [
        ("data_type", "NSE_EQ|CASH"),
        ("interval", "1D"),
    ]

    if date_from:
        params.append(("from", date_from))

    response = requests.get(
        FII_ENDPOINT,
        params=params,
        headers=_headers(),
        timeout=TIMEOUT,
    )

    response.raise_for_status()

    payload = response.json()

    rows = (
        payload.get("data", {})
        .get("NSE_EQ|CASH", [])
    )

    return rows


def _fetch_dii(date_from=None):

    params = {
        "data_type": "NSE_EQ|CASH",
        "interval": "1D",
    }

    if date_from:
        params["from"] = date_from

    response = requests.get(
        DII_ENDPOINT,
        params=params,
        headers=_headers(),
        timeout=TIMEOUT,
    )

    response.raise_for_status()

    payload = response.json()

    rows = (
        payload.get("data", {})
        .get("NSE_EQ|CASH", [])
    )

    return rows


def _row_date(row):

    timestamp = row.get("time_stamp")

    if timestamp is None:
        timestamp = row.get("timestamp")

    return _date_from_timestamp(timestamp)


def _normalise(rows):

    result = {}

    for row in rows:

        day = _row_date(row)

        if not day:
            continue

        buy = float(row.get("buy_amount", 0) or 0)
        sell = float(row.get("sell_amount", 0) or 0)

        # Upstox documentation reports INR amounts.
        # Convert to crore for readable scanner context.
        buy_cr = buy / 10_000_000
        sell_cr = sell / 10_000_000
        net_cr = buy_cr - sell_cr

        result[day] = {
            "date": day,
            "buy": round(buy_cr, 2),
            "sell": round(sell_cr, 2),
            "net": round(net_cr, 2),
        }

    return result


def get_flow_for_date(date_value):

    if hasattr(date_value, "isoformat"):
        day = date_value.isoformat()
    else:
        day = str(date_value)

    if day in _FLOW_CACHE:
        return _FLOW_CACHE[day]

    try:

        fii_rows = _fetch_fii(day)
        dii_rows = _fetch_dii(day)

        fii = _normalise(fii_rows)
        dii = _normalise(dii_rows)

        snapshot = {
            "date": day,
            "fii": fii.get(day),
            "dii": dii.get(day),
            "source": "UPSTOX",
        }

        if snapshot["fii"] is None and snapshot["dii"] is None:
            snapshot["available"] = False
        else:
            snapshot["available"] = True

        _FLOW_CACHE[day] = snapshot

        return snapshot

    except Exception as exc:

        snapshot = {
            "date": day,
            "fii": None,
            "dii": None,
            "source": "UPSTOX",
            "available": False,
            "error": str(exc),
        }

        _FLOW_CACHE[day] = snapshot

        return snapshot


def get_flow_for_timestamp(timestamp):

    day = _date_from_timestamp(timestamp)

    if day is None:
        return None

    return get_flow_for_date(day)


def refresh_live():

    try:

        # Fetch a small recent range.
        fii_rows = _fetch_fii()
        dii_rows = _fetch_dii()

        fii = _normalise(fii_rows)
        dii = _normalise(dii_rows)

        dates = sorted(
            set(fii.keys()) | set(dii.keys())
        )

        if not dates:
            return None

        latest = dates[-1]

        snapshot = {
            "date": latest,
            "fii": fii.get(latest),
            "dii": dii.get(latest),
            "source": "UPSTOX",
            "available": True,
        }

        _FLOW_CACHE[latest] = snapshot
        MARKET_STATE["INSTITUTIONAL_FLOW"] = snapshot

        return snapshot

    except Exception as exc:

        print(
            f"⚠️ FII/DII refresh unavailable: {exc}"
        )

        return None


def calculate_institutional_score(
    snapshot,
    direction,
):
    """
    Convert institutional cash flow into a small directional
    confidence contribution.

    Maximum:
        +/-5

    This is intentionally an additive engine contribution.
    It does not reject a trade.
    """

    if not snapshot:
        return {
            "adjustment": 0,
            "fii_net": None,
            "dii_net": None,
            "combined_net": None,
            "available": False,
        }

    fii = snapshot.get("fii") or {}
    dii = snapshot.get("dii") or {}

    fii_net = float(fii.get("net", 0) or 0)
    dii_net = float(dii.get("net", 0) or 0)

    combined = fii_net + dii_net

    direction = str(
        direction or ""
    ).upper()

    if direction == "SELL":
        combined = -combined

    # Scale in ₹ crore.
    # 5,000 Cr of combined directional flow ≈ full contribution.
    raw = combined / 5000.0

    raw = max(
        -1.0,
        min(1.0, raw),
    )

    adjustment = round(
        raw * 5
    )

    return {
        "adjustment": adjustment,
        "fii_net": round(fii_net, 2),
        "dii_net": round(dii_net, 2),
        "combined_net": round(
            fii_net + dii_net,
            2,
        ),
        "available": True,
        "date": snapshot.get("date"),
        "source": snapshot.get("source"),
    }
