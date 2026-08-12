"""PaisaAI FII/DII Institutional Flow Engine.

NSE is the primary source. For live/intraday use, the latest published
trading-day snapshot is used; current-day zeros are never fabricated.
"""

from datetime import datetime, timezone

from scanner.runtime import MARKET_STATE
from scanner.nse_context import refresh_fii_dii, flow_for_date


def _date_from_timestamp(timestamp):
    if timestamp is None:
        return None
    try:
        if isinstance(timestamp, (int, float)):
            return datetime.fromtimestamp(timestamp / 1000.0, tz=timezone.utc).date().isoformat()
        return datetime.fromisoformat(str(timestamp).replace("Z", "+00:00")).date().isoformat()
    except Exception:
        return None


def _snapshot_to_engine(snapshot):
    if not snapshot:
        return None
    fii = snapshot.get("fii") or {}
    dii = snapshot.get("dii") or {}
    return {
        "date": snapshot.get("date"),
        "fii": {
            "buy": round(float(fii.get("buy") or 0), 2),
            "sell": round(float(fii.get("sell") or 0), 2),
            "net": round(float(fii.get("net") or 0), 2),
        } if fii else None,
        "dii": {
            "buy": round(float(dii.get("buy") or 0), 2),
            "sell": round(float(dii.get("sell") or 0), 2),
            "net": round(float(dii.get("net") or 0), 2),
        } if dii else None,
        "source": snapshot.get("source", "NSE"),
        "available": bool(snapshot.get("available")),
    }


def get_flow_for_date(date_value):
    try:
        snapshot = flow_for_date(date_value)
        result = _snapshot_to_engine(snapshot)
        if result:
            return result
    except Exception:
        pass
    return None


def get_flow_for_timestamp(timestamp):
    day = _date_from_timestamp(timestamp)
    if day is None:
        return None
    return get_flow_for_date(day)


def refresh_live():
    snapshot = refresh_fii_dii(force=True)
    result = _snapshot_to_engine(snapshot)
    if result:
        MARKET_STATE["INSTITUTIONAL_FLOW"] = result
    return result


def calculate_institutional_score(snapshot, direction):
    if not snapshot or not snapshot.get("available"):
        return {
            "adjustment": 0,
            "fii_net": None,
            "dii_net": None,
            "combined_net": None,
            "available": False,
            "date": snapshot.get("date") if snapshot else None,
            "source": snapshot.get("source") if snapshot else None,
        }

    fii = snapshot.get("fii") or {}
    dii = snapshot.get("dii") or {}
    fii_net = float(fii.get("net", 0) or 0)
    dii_net = float(dii.get("net", 0) or 0)
    combined_net = fii_net + dii_net

    if str(direction or "").upper() == "SELL":
        combined_net = -combined_net

    raw = max(-1.0, min(1.0, combined_net / 5000.0))
    adjustment = round(raw * 5)

    return {
        "adjustment": adjustment,
        "fii_net": round(fii_net, 2),
        "dii_net": round(dii_net, 2),
        "combined_net": round(fii_net + dii_net, 2),
        "available": True,
        "date": snapshot.get("date"),
        "source": snapshot.get("source", "NSE"),
    }
