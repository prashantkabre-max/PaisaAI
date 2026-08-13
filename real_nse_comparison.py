"""PaisaAI REAL-NSE Replay comparison.

Comparison-only validation.

BASELINE:
    Existing Replay indicator/scoring/decision pipeline.

ENHANCED:
    Same baseline trade, but only retained when the four new
    technical indicators pass the >= SHADOW_MIN shadow gate.

Production is NOT modified.

Important performance design:
    The existing ReplayIndicatorEngine recalculates several expensive
    indicators from the complete history on every candle. That is
    correct for the existing Replay pipeline but extremely expensive
    for this comparison.

    Therefore this runner:
      1. Fetches real Upstox historical candles.
      2. Processes candles chronologically.
      3. Uses the existing baseline pipeline.
      4. Prints progress while processing.
      5. Keeps the comparison observation-only.

The result is written to:
    real_nse_comparison.json
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import date, timedelta
from urllib.parse import quote

import requests

from scanner.replay_indicators.engine import calculate_all_indicators
from scanner.replay_indicator_shadow import calculate_shadow_score
from scanner.indicators import calculate_indicators
from scanner.scoring import calculate_score
from scanner.decision import evaluate_trade


API_BASE = "https://api.upstox.com/v3/historical-candle"

INTERVAL = int(os.getenv("REPLAY_INTERVAL", "1"))
LOOKBACK_DAYS = int(os.getenv("REPLAY_LOOKBACK_DAYS", "15"))
OUTCOME_BARS = int(os.getenv("REPLAY_OUTCOME_BARS", "30"))
SHADOW_MIN = float(os.getenv("REPLAY_SHADOW_MIN", "75"))
SYMBOL_LIMIT = int(os.getenv("REPLAY_SYMBOL_LIMIT", "10"))

# Existing Replay minimum history.
MIN_HISTORY = int(os.getenv("REPLAY_MIN_HISTORY", "50"))

# Progress frequency.
PROGRESS_EVERY = int(os.getenv("REPLAY_PROGRESS_EVERY", "50"))


def _token():
    try:
        import config

        token = getattr(config, "ACCESS_TOKEN", None)
    except Exception as exc:
        raise RuntimeError(
            "Could not import config.py. Run this from the PaisaAI project root."
        ) from exc

    if not token:
        raise RuntimeError("config.ACCESS_TOKEN is empty or missing.")

    return token


def fetch_candles(symbol: str, token: str):
    """Fetch real Upstox historical 1-minute candles."""

    today = date.today()
    to_date = today - timedelta(days=1)
    from_date = to_date - timedelta(days=LOOKBACK_DAYS)

    encoded = quote(symbol, safe="")

    url = (
        f"{API_BASE}/{encoded}/minutes/{INTERVAL}/"
        f"{to_date.isoformat()}/{from_date.isoformat()}"
    )

    response = requests.get(
        url,
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
        },
        timeout=30,
    )

    response.raise_for_status()

    payload = response.json()

    candles = payload.get("data", {}).get("candles", [])

    # Upstox returns newest -> oldest.
    candles.reverse()

    result = []

    for candle in candles:
        if len(candle) < 6:
            continue

        result.append(
            {
                "timestamp": candle[0],
                "open": float(candle[1]),
                "high": float(candle[2]),
                "low": float(candle[3]),
                "close": float(candle[4]),
                "volume": float(candle[5]),
            }
        )

    return result


def previous_session_close(candles, index):
    current_date = str(candles[index]["timestamp"])[:10]

    for i in range(index - 1, -1, -1):
        if str(candles[i]["timestamp"])[:10] != current_date:
            return candles[i]["close"]

    return None


def session_ohlc(candles, index):
    current_date = str(candles[index]["timestamp"])[:10]

    start = index

    while (
        start > 0
        and str(candles[start - 1]["timestamp"])[:10] == current_date
    ):
        start -= 1

    session = candles[start : index + 1]

    return {
        "open": session[0]["open"],
        "high": max(c["high"] for c in session),
        "low": min(c["low"] for c in session),
    }


def outcome(candles, index, trade):
    """Evaluate the baseline trade after the signal candle."""

    risk = trade.get("risk") or {}

    entry = risk.get("entry")
    stop = risk.get("stop_loss")
    target = risk.get("target3")

    if entry is None or stop is None or target is None:
        return {
            "label": "NO_RISK",
            "r": 0.0,
            "bars": 0,
        }

    direction = trade["action"]

    if abs(entry - stop) <= 0:
        return {
            "label": "NO_RISK",
            "r": 0.0,
            "bars": 0,
        }

    end = min(
        len(candles),
        index + 1 + OUTCOME_BARS,
    )

    for j in range(index + 1, end):
        candle = candles[j]

        if direction == "BUY":
            stop_hit = candle["low"] <= stop
            target_hit = candle["high"] >= target

        else:
            stop_hit = candle["high"] >= stop
            target_hit = candle["low"] <= target

        # Conservative same-candle handling.
        if stop_hit:
            return {
                "label": "LOSS",
                "r": -1.0,
                "bars": j - index,
            }

        if target_hit:
            return {
                "label": "WIN",
                "r": 2.0,
                "bars": j - index,
            }

    return {
        "label": "TIMEOUT",
        "r": 0.0,
        "bars": max(
            0,
            end - index - 1,
        ),
    }


def empty_stats():
    return {
        "signals": 0,
        "completed": 0,
        "wins": 0,
        "losses": 0,
        "timeouts": 0,
        "net_r": 0.0,
    }


def add_result(stats, result):
    stats["signals"] += 1

    if result["label"] == "NO_RISK":
        return

    stats["completed"] += 1
    stats["net_r"] += result["r"]

    if result["label"] == "WIN":
        stats["wins"] += 1

    elif result["label"] == "LOSS":
        stats["losses"] += 1

    elif result["label"] == "TIMEOUT":
        stats["timeouts"] += 1


def summarize(stats):
    closed = stats["wins"] + stats["losses"]

    return {
        **stats,
        "win_rate_closed_pct": round(
            stats["wins"] / closed * 100,
            2,
        )
        if closed
        else 0.0,
        "avg_r_per_signal": round(
            stats["net_r"] / stats["signals"],
            4,
        )
        if stats["signals"]
        else 0.0,
        "avg_r_per_completed": round(
            stats["net_r"] / stats["completed"],
            4,
        )
        if stats["completed"]
        else 0.0,
    }


def choose_score(indicators):
    """Exactly the existing BUY-vs-SELL selection logic."""

    buy = calculate_score(
        indicators,
        "BUY",
    )

    sell = calculate_score(
        indicators,
        "SELL",
    )

    if sell["confidence"] > buy["confidence"]:
        return sell

    return buy


def build_market(symbol, current, previous_close, session):
    return {
        "symbol": symbol,
        "ltp": current["close"],
        "previous_close": previous_close,
        "open": session["open"],
        "high": session["high"],
        "low": session["low"],
        "close": current["close"],
        "volume": current["volume"],
    }


def run_symbol(symbol, candles):
    baseline = empty_stats()
    enhanced = empty_stats()

    shadow_counts = {
        "BUY": 0,
        "SELL": 0,
    }

    shadow_active = 0
    processed = 0
    skipped = 0

    total = max(
        0,
        len(candles) - MIN_HISTORY - 1,
    )

    print(
        f"  {symbol}: processing {total} tradeable candles...",
        flush=True,
    )

    start_time = time.time()

    for index in range(
        MIN_HISTORY,
        len(candles) - 1,
    ):
        current = candles[index]

        prev_close = previous_session_close(
            candles,
            index,
        )

        if prev_close in (None, 0):
            skipped += 1
            continue

        session = session_ohlc(
            candles,
            index,
        )

        history = candles[: index + 1]

        # Existing baseline calculation.
        #
        # This is intentionally kept identical to Replay.
        all_indicators = calculate_all_indicators(
            history,
            symbol,
        )

        market = build_market(
            symbol,
            current,
            prev_close,
            session,
        )

        indicators = calculate_indicators(
            market,
            all_indicators,
        )

        if indicators is None:
            skipped += 1
            continue

        score = choose_score(indicators)

        trade = evaluate_trade(
            indicators,
            score,
        )

        if (
            not trade
            or trade.get("action") == "IGNORE"
            or trade.get("grade") == "IGNORE"
        ):
            processed += 1

        else:
            result = outcome(
                candles,
                index,
                trade,
            )

            # Baseline cohort.
            add_result(
                baseline,
                result,
            )

            direction = trade["action"]

            # Observation-only shadow.
            shadow = calculate_shadow_score(
                all_indicators,
                direction,
            )

            if shadow["confidence"] >= SHADOW_MIN:
                shadow_counts[direction] += 1
                shadow_active += 1

                add_result(
                    enhanced,
                    result,
                )

            processed += 1

        if (
            processed % PROGRESS_EVERY == 0
            or index == len(candles) - 2
        ):
            elapsed = max(
                0.001,
                time.time() - start_time,
            )

            rate = processed / elapsed

            print(
                f"    progress {processed:>5}/{total:<5} "
                f"| base={baseline['signals']:>3} "
                f"| enh={enhanced['signals']:>3} "
                f"| {rate:>6.1f} candles/s",
                flush=True,
            )

    elapsed = time.time() - start_time

    print(
        f"  {symbol}: DONE "
        f"| candles={len(candles)} "
        f"| baseline={baseline['signals']} "
        f"| enhanced={enhanced['signals']} "
        f"| time={elapsed:.1f}s",
        flush=True,
    )

    return (
        baseline,
        enhanced,
        shadow_counts,
        shadow_active,
    )


def main():
    token = _token()

    from scanner.watchlist import get_watchlist

    watchlist = list(
        get_watchlist()
    )

    if SYMBOL_LIMIT > 0:
        watchlist = watchlist[:SYMBOL_LIMIT]

    print("=" * 88)
    print(
        "PAISAAI REAL-NSE REPLAY: "
        "BASELINE vs NEW-INDICATOR ENHANCED"
    )
    print("=" * 88)
    print(
        f"Symbols       : {len(watchlist)}"
    )
    print(
        f"Lookback      : {LOOKBACK_DAYS} calendar days"
    )
    print(
        f"Outcome       : next {OUTCOME_BARS} x 1m candles"
    )
    print(
        f"Shadow gate   : >= {SHADOW_MIN:.0f}% (3/4 or 4/4)"
    )
    print(
        f"Min history   : {MIN_HISTORY} candles"
    )
    print(
        f"Progress      : every {PROGRESS_EVERY} processed candles"
    )
    print(
        "Production    : UNCHANGED"
    )
    print("=" * 88)

    totals_base = empty_stats()
    totals_enh = empty_stats()

    total_shadow = 0
    total_candles = 0

    per_symbol = []

    overall_start = time.time()

    for number, symbol in enumerate(
        watchlist,
        start=1,
    ):
        print(
            f"\n[{number}/{len(watchlist)}] {symbol}",
            flush=True,
        )

        try:
            candles = fetch_candles(
                symbol,
                token,
            )

            total_candles += len(candles)

            print(
                f"  fetched {len(candles)} candles",
                flush=True,
            )

            if len(candles) < MIN_HISTORY + 2:
                print(
                    f"  SKIP: insufficient candles",
                    flush=True,
                )
                continue

            (
                base,
                enh,
                shadow_counts,
                shadow_active,
            ) = run_symbol(
                symbol,
                candles,
            )

            for key in totals_base:
                totals_base[key] += base[key]
                totals_enh[key] += enh[key]

            total_shadow += shadow_active

            row = {
                "symbol": symbol,
                "candles": len(candles),
                "baseline": summarize(base),
                "enhanced": summarize(enh),
                "shadow_buy": shadow_counts["BUY"],
                "shadow_sell": shadow_counts["SELL"],
            }

            per_symbol.append(row)

            print(
                f"  RESULT "
                f"| baseline={base['signals']} "
                f"| enhanced={enh['signals']} "
                f"| baseR={base['net_r']:.2f} "
                f"| enhR={enh['net_r']:.2f}",
                flush=True,
            )

        except requests.HTTPError as exc:
            print(
                f"  HTTP ERROR: {exc}",
                flush=True,
            )

        except Exception as exc:
            print(
                f"  ERROR: {type(exc).__name__}: {exc}",
                flush=True,
            )

    base = summarize(
        totals_base
    )

    enh = summarize(
        totals_enh
    )

    elapsed = time.time() - overall_start

    signal_reduction = (
        base["signals"]
        - enh["signals"]
    )

    win_rate_delta = (
        enh["win_rate_closed_pct"]
        - base["win_rate_closed_pct"]
    )

    net_r_delta = (
        enh["net_r"]
        - base["net_r"]
    )

    print("\n" + "=" * 88)
    print("FINAL COMPARISON")
    print("=" * 88)

    print(
        json.dumps(
            {
                "baseline": base,
                "enhanced": enh,
            },
            indent=2,
        )
    )

    print(
        f"Total candles fetched : {total_candles}"
    )

    print(
        f"Enhanced signals      : {total_shadow}"
    )

    print(
        f"Signal reduction      : {signal_reduction}"
    )

    print(
        f"Win-rate delta        : "
        f"{win_rate_delta:+.2f} pp"
    )

    print(
        f"Net-R delta           : "
        f"{net_r_delta:+.2f}R"
    )

    print(
        f"Elapsed               : "
        f"{elapsed:.1f}s"
    )

    print("=" * 88)

    output = {
        "config": {
            "lookback_days": LOOKBACK_DAYS,
            "interval": INTERVAL,
            "outcome_bars": OUTCOME_BARS,
            "shadow_min": SHADOW_MIN,
            "min_history": MIN_HISTORY,
            "symbols": len(watchlist),
        },
        "baseline": base,
        "enhanced": enh,
        "per_symbol": per_symbol,
    }

    with open(
        "real_nse_comparison.json",
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(
            output,
            handle,
            indent=2,
        )

    print(
        "Saved: real_nse_comparison.json"
    )


if __name__ == "__main__":
    try:
        main()

    except KeyboardInterrupt:
        print(
            "\nInterrupted."
        )
        sys.exit(130)

    except Exception as exc:
        print(
            f"\nFATAL: {type(exc).__name__}: {exc}"
        )
        sys.exit(1)
