"""
PaisaAI Replay Trade Manager V2

REPLAY ONLY.

Every generated signal is evaluated independently through:

    ATR
    SESSION
    SWING
    ORB
    SMART

Production trade_manager.py is NOT used or modified.
"""

from datetime import datetime
from math import floor

from scanner import settings


# ============================================================
# CONFIGURATION
# ============================================================

STRATEGIES = [
    "ATR",
    "SESSION",
    "SWING",
    "ORB",
    "SMART",
]

MAX_RISK_PER_TRADE = getattr(
    settings,
    "MAX_RISK_PER_TRADE",
    2000,
)

ATR_MULTIPLIER = 1.25
MIN_STOP_PERCENT = 0.003

RR1 = 1.0
RR2 = 1.5
RR3 = 2.0

SWING_LOOKBACK = 10
ORB_CANDLES = 5


# ============================================================
# REPLAY STATE
# ============================================================

_active_trades = {
    strategy: {}
    for strategy in STRATEGIES
}

_stats = {
    strategy: {
        "signals": 0,
        "trades": 0,
        "wins": 0,
        "losses": 0,
        "eod": 0,
        "target1": 0,
        "target2": 0,
        "target3": 0,
        "stoploss": 0,
        "gross_profit": 0.0,
        "gross_loss": 0.0,
    }
    for strategy in STRATEGIES
}


# ============================================================
# RESET
# ============================================================

def reset():
    """
    Completely reset replay state.

    Called before every replay run.
    """

    for strategy in STRATEGIES:

        _active_trades[strategy].clear()

        for key in _stats[strategy]:

            if key in (
                "gross_profit",
                "gross_loss",
            ):
                _stats[strategy][key] = 0.0

            else:
                _stats[strategy][key] = 0


# ============================================================
# BASIC HELPERS
# ============================================================

def _safe_float(value):

    if value is None:
        return None

    try:
        return float(value)

    except (
        TypeError,
        ValueError,
    ):
        return None


def _valid_buy_stop(
    entry,
    stop,
):
    stop = _safe_float(stop)

    return (
        stop is not None
        and stop < entry
    )


def _valid_sell_stop(
    entry,
    stop,
):
    stop = _safe_float(stop)

    return (
        stop is not None
        and stop > entry
    )


def _atr_distance(
    entry,
    atr,
):
    return max(
        atr * ATR_MULTIPLIER,
        entry * MIN_STOP_PERCENT,
    )


# ============================================================
# SESSION / SWING / ORB LEVELS
# ============================================================

def _date_of(candle):

    timestamp = candle.get(
        "timestamp"
    )

    if timestamp is None:
        return None

    return str(timestamp)[:10]


def _levels(history):
    """
    Calculate structural levels using only information
    available at the moment the signal is generated.

    SESSION:
        Includes the current completed entry candle.

    SWING:
        Previous completed candles only.

    ORB:
        First five candles of the current session.
    """

    candles = list(
        history or []
    )

    if not candles:
        return {
            "session_high": None,
            "session_low": None,
            "swing_high": None,
            "swing_low": None,
            "orb_high": None,
            "orb_low": None,
        }

    current_date = _date_of(
        candles[-1]
    )

    # --------------------------------------------------------
    # Current session
    # --------------------------------------------------------

    session = []

    for candle in reversed(candles):

        if (
            _date_of(candle)
            != current_date
        ):
            break

        session.append(candle)

    session.reverse()

    session_highs = [
        _safe_float(c.get("high"))
        for c in session
        if _safe_float(c.get("high"))
        is not None
    ]

    session_lows = [
        _safe_float(c.get("low"))
        for c in session
        if _safe_float(c.get("low"))
        is not None
    ]

    session_high = (
        max(session_highs)
        if session_highs
        else None
    )

    session_low = (
        min(session_lows)
        if session_lows
        else None
    )

    # --------------------------------------------------------
    # Swing
    #
    # Current candle is excluded.
    # --------------------------------------------------------

    completed = candles[:-1]

    previous_session = []

    for candle in reversed(
        completed
    ):

        if (
            _date_of(candle)
            == current_date
        ):
            previous_session.append(
                candle
            )

        else:
            break

    previous_session.reverse()

    swing_window = previous_session[
        -SWING_LOOKBACK:
    ]

    swing_highs = [
        _safe_float(c.get("high"))
        for c in swing_window
        if _safe_float(c.get("high"))
        is not None
    ]

    swing_lows = [
        _safe_float(c.get("low"))
        for c in swing_window
        if _safe_float(c.get("low"))
        is not None
    ]

    swing_high = (
        max(swing_highs)
        if len(swing_window)
        >= SWING_LOOKBACK
        and swing_highs
        else None
    )

    swing_low = (
        min(swing_lows)
        if len(swing_window)
        >= SWING_LOOKBACK
        and swing_lows
        else None
    )

    # --------------------------------------------------------
    # ORB
    # --------------------------------------------------------

    opening = session[
        :ORB_CANDLES
    ]

    if len(opening) >= ORB_CANDLES:

        orb_highs = [
            _safe_float(
                c.get("high")
            )
            for c in opening
            if _safe_float(
                c.get("high")
            ) is not None
        ]

        orb_lows = [
            _safe_float(
                c.get("low")
            )
            for c in opening
            if _safe_float(
                c.get("low")
            ) is not None
        ]

        orb_high = (
            max(orb_highs)
            if orb_highs
            else None
        )

        orb_low = (
            min(orb_lows)
            if orb_lows
            else None
        )

    else:

        orb_high = None
        orb_low = None

    return {
        "session_high": session_high,
        "session_low": session_low,
        "swing_high": swing_high,
        "swing_low": swing_low,
        "orb_high": orb_high,
        "orb_low": orb_low,
    }


# ============================================================
# STOP LOSS SELECTION
# ============================================================

def _select_buy_stop(
    strategy,
    entry,
    minimum_distance,
    levels,
):

    atr_stop = (
        entry
        - minimum_distance
    )

    if strategy == "ATR":
        return atr_stop

    candidates = []

    if strategy in (
        "SESSION",
        "SMART",
    ):
        if _valid_buy_stop(
            entry,
            levels["session_low"],
        ):
            candidates.append(
                levels["session_low"]
            )

    if strategy in (
        "SWING",
        "SMART",
    ):
        if _valid_buy_stop(
            entry,
            levels["swing_low"],
        ):
            candidates.append(
                levels["swing_low"]
            )

    if strategy in (
        "ORB",
        "SMART",
    ):
        if _valid_buy_stop(
            entry,
            levels["orb_low"],
        ):
            candidates.append(
                levels["orb_low"]
            )

    if strategy == "SESSION":

        return (
            candidates[0]
            if candidates
            else atr_stop
        )

    if strategy == "SWING":

        return (
            candidates[0]
            if candidates
            else atr_stop
        )

    if strategy == "ORB":

        return (
            candidates[0]
            if candidates
            else atr_stop
        )

    # --------------------------------------------------------
    # SMART
    #
    # Choose the nearest valid structural stop that still
    # provides at least the ATR/minimum protective distance.
    #
    # If no structural stop satisfies that requirement,
    # fall back to ATR.
    # --------------------------------------------------------

    smart_candidates = []

    for stop in candidates:

        distance = entry - stop

        if distance >= minimum_distance:
            smart_candidates.append(
                (
                    distance,
                    stop,
                )
            )

    if smart_candidates:

        smart_candidates.sort(
            key=lambda item: item[0]
        )

        return smart_candidates[0][1]

    return atr_stop


def _select_sell_stop(
    strategy,
    entry,
    minimum_distance,
    levels,
):

    atr_stop = (
        entry
        + minimum_distance
    )

    if strategy == "ATR":
        return atr_stop

    candidates = []

    if strategy in (
        "SESSION",
        "SMART",
    ):
        if _valid_sell_stop(
            entry,
            levels["session_high"],
        ):
            candidates.append(
                levels["session_high"]
            )

    if strategy in (
        "SWING",
        "SMART",
    ):
        if _valid_sell_stop(
            entry,
            levels["swing_high"],
        ):
            candidates.append(
                levels["swing_high"]
            )

    if strategy in (
        "ORB",
        "SMART",
    ):
        if _valid_sell_stop(
            entry,
            levels["orb_high"],
        ):
            candidates.append(
                levels["orb_high"]
            )

    if strategy == "SESSION":

        return (
            candidates[0]
            if candidates
            else atr_stop
        )

    if strategy == "SWING":

        return (
            candidates[0]
            if candidates
            else atr_stop
        )

    if strategy == "ORB":

        return (
            candidates[0]
            if candidates
            else atr_stop
        )

    # SMART

    smart_candidates = []

    for stop in candidates:

        distance = stop - entry

        if distance >= minimum_distance:
            smart_candidates.append(
                (
                    distance,
                    stop,
                )
            )

    if smart_candidates:

        smart_candidates.sort(
            key=lambda item: item[0]
        )

        return smart_candidates[0][1]

    return atr_stop


# ============================================================
# BUILD RISK
# ============================================================

def build_risk(
    strategy,
    trade,
    history,
):
    """
    Build completely independent risk for one strategy.
    """

    if strategy not in STRATEGIES:
        return None

    if not trade:
        return None

    indicators = trade.get(
        "indicators",
        {},
    )

    entry = _safe_float(
        trade.get("ltp")
        or trade.get(
            "risk",
            {},
        ).get("entry")
    )

    atr = _safe_float(
        indicators.get("atr")
    )

    if entry is None:
        return None

    if atr is None or atr <= 0:
        return None

    levels = _levels(
        history
    )

    minimum_distance = _atr_distance(
        entry,
        atr,
    )

    if trade["action"] == "BUY":

        stop = _select_buy_stop(
            strategy,
            entry,
            minimum_distance,
            levels,
        )

        stop = round(
            float(stop),
            2,
        )

        risk = round(
            entry - stop,
            2,
        )

        if risk <= 0:
            return None

        target1 = round(
            entry + risk * RR1,
            2,
        )

        target2 = round(
            entry + risk * RR2,
            2,
        )

        target3 = round(
            entry + risk * RR3,
            2,
        )

    elif trade["action"] == "SELL":

        stop = _select_sell_stop(
            strategy,
            entry,
            minimum_distance,
            levels,
        )

        stop = round(
            float(stop),
            2,
        )

        risk = round(
            stop - entry,
            2,
        )

        if risk <= 0:
            return None

        target1 = round(
            entry - risk * RR1,
            2,
        )

        target2 = round(
            entry - risk * RR2,
            2,
        )

        target3 = round(
            entry - risk * RR3,
            2,
        )

    else:

        return None

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # Calculate quantity AFTER rounding the actual stop.
    # This guarantees actual risk cannot exceed ₹2,000
    # because of rounding.
    # --------------------------------------------------------

    quantity = floor(
        MAX_RISK_PER_TRADE
        / risk
    )

    if quantity < 1:
        quantity = 1

    actual_risk = round(
        quantity * risk,
        2,
    )

    return {
        "entry": round(
            entry,
            2,
        ),
        "stop_loss": stop,
        "target1": target1,
        "target2": target2,
        "target3": target3,
        "risk": risk,
        "per_share_risk": risk,
        "recommended_qty": quantity,
        "capital_required": round(
            quantity * entry,
            2,
        ),
        "actual_max_risk": actual_risk,
        "reward": round(
            abs(target1 - entry),
            2,
        ),
        "risk_reward": round(
            abs(target1 - entry)
            / risk,
            2,
        ),
        "strategy": strategy,
        "session_high": levels[
            "session_high"
        ],
        "session_low": levels[
            "session_low"
        ],
        "swing_high": levels[
            "swing_high"
        ],
        "swing_low": levels[
            "swing_low"
        ],
        "orb_high": levels[
            "orb_high"
        ],
        "orb_low": levels[
            "orb_low"
        ],
    }


# ============================================================
# REGISTER
# ============================================================

def register_trade(
    strategy,
    trade,
    history=None,
):
    """
    Register EVERY signal independently.

    IMPORTANT:
    The key is NOT symbol.

    Multiple signals on the same symbol are therefore allowed
    in replay so every generated signal can be compared fairly.
    """

    if strategy not in STRATEGIES:
        return False

    if not trade:
        return False

    symbol = trade.get(
        "symbol"
    )

    if not symbol:
        return False

    risk = build_risk(
        strategy,
        trade,
        history or [],
    )

    if risk is None:
        return False

    trade_number = trade.get(
        "trade_number"
    )

    if trade_number is None:
        return False

    trade_id = (
        f"{strategy}:"
        f"{symbol}:"
        f"{trade_number}"
    )

    timestamp = trade.get(
        "timestamp",
        datetime.now(),
    )

    _active_trades[
        strategy
    ][trade_id] = {
        "trade_id": trade_id,
        "strategy": strategy,
        "symbol": symbol,
        "display_symbol": trade.get(
            "display_symbol",
            symbol,
        ),
        "trade_number": trade_number,
        "action": trade["action"],
        "entry": risk["entry"],
        "stop_loss": risk["stop_loss"],
        "target1": risk["target1"],
        "target2": risk["target2"],
        "target3": risk["target3"],
        "risk": risk,
        "target1_hit": False,
        "target2_hit": False,
        "target3_hit": False,
        "opened_at": timestamp,
    }

    _stats[
        strategy
    ]["signals"] += 1

    _stats[
        strategy
    ]["trades"] += 1

    return True


# ============================================================
# UPDATE
# ============================================================

def _terminal_event(
    strategy,
    trade,
    event,
    price,
    timestamp,
):
    """
    Record ONLY terminal trade outcome.

    T1/T2 are milestones.
    T3 is a win.
    SL is a loss.
    """

    quantity = trade[
        "risk"
    ]["recommended_qty"]

    entry = trade["entry"]

    if event == "TARGET_3_HIT":

        if trade["action"] == "BUY":

            pnl = (
                trade["target3"]
                - entry
            ) * quantity

        else:

            pnl = (
                entry
                - trade["target3"]
            ) * quantity

        pnl = round(
            pnl,
            2,
        )

        _stats[
            strategy
        ]["wins"] += 1

        _stats[
            strategy
        ]["target3"] += 1

        _stats[
            strategy
        ]["gross_profit"] += max(
            pnl,
            0,
        )

    elif event == "STOP_LOSS_HIT":

        if trade["action"] == "BUY":

            pnl = (
                trade["stop_loss"]
                - entry
            ) * quantity

        else:

            pnl = (
                entry
                - trade["stop_loss"]
            ) * quantity

        pnl = round(
            pnl,
            2,
        )

        _stats[
            strategy
        ]["losses"] += 1

        _stats[
            strategy
        ]["stoploss"] += 1

        _stats[
            strategy
        ]["gross_loss"] += abs(
            pnl
        )

    else:

        return None

    try:

        duration = int(
            (
                timestamp
                - trade["opened_at"]
            ).total_seconds()
        )

    except (
        TypeError,
        AttributeError,
    ):

        duration = 0

    return {
        "trade_id": trade[
            "trade_id"
        ],
        "strategy": strategy,
        "symbol": trade[
            "symbol"
        ],
        "display_symbol": trade[
            "display_symbol"
        ],
        "trade_number": trade[
            "trade_number"
        ],
        "event": event,
        "exit_reason": (
            "TARGET 3"
            if event
            == "TARGET_3_HIT"
            else "STOP LOSS"
        ),
        "entry": trade[
            "entry"
        ],
        "exit_price": round(
            price,
            2,
        ),
        "stop_loss": trade[
            "stop_loss"
        ],
        "quantity": quantity,
        "pnl": pnl,
        "duration": (
            f"{duration // 60:02d}m "
            f"{duration % 60:02d}s"
        ),
        "opened_at": trade[
            "opened_at"
        ],
        "closed_at": timestamp,
    }


def update_trade(
    strategy,
    symbol,
    price,
    timestamp=None,
    trade_id=None,
):
    """
    Update ALL active replay trades for this symbol
    under the selected strategy.

    This is critical because several signals may be active
    simultaneously in replay.
    """

    if strategy not in STRATEGIES:
        return []

    if timestamp is None:
        timestamp = datetime.now()

    price = _safe_float(
        price
    )

    if price is None:
        return []

    events = []

    matching_ids = [
        active_trade_id
        for active_trade_id, trade
        in _active_trades[
            strategy
        ].items()
        if (
            trade["symbol"] == symbol
            and (
                trade_id is None
                or active_trade_id == trade_id
            )
        )
    ]

    for trade_id in matching_ids:

        trade = _active_trades[
            strategy
        ].get(
            trade_id
        )

        if trade is None:
            continue

        # ----------------------------------------------------
        # BUY
        # ----------------------------------------------------

        if trade["action"] == "BUY":

            if (
                not trade["target1_hit"]
                and price
                >= trade["target1"]
            ):

                trade[
                    "target1_hit"
                ] = True

                _stats[
                    strategy
                ]["target1"] += 1

                events.append({
                    "trade_id": trade_id,
                    "strategy": strategy,
                    "symbol": symbol,
                    "display_symbol": trade[
                        "display_symbol"
                    ],
                    "trade_number": trade[
                        "trade_number"
                    ],
                    "event": "TARGET_1_HIT",
                    "entry": trade[
                        "entry"
                    ],
                    "exit_price": trade[
                        "target1"
                    ],
                    "quantity": trade[
                        "risk"
                    ]["recommended_qty"],
                    "pnl": round(
                        (
                            trade[
                                "target1"
                            ]
                            - trade[
                                "entry"
                            ]
                        )
                        * trade[
                            "risk"
                        ]["recommended_qty"],
                        2,
                    ),
                })

            if (
                not trade["target2_hit"]
                and price
                >= trade["target2"]
            ):

                trade[
                    "target2_hit"
                ] = True

                _stats[
                    strategy
                ]["target2"] += 1

                events.append({
                    "trade_id": trade_id,
                    "strategy": strategy,
                    "symbol": symbol,
                    "display_symbol": trade[
                        "display_symbol"
                    ],
                    "trade_number": trade[
                        "trade_number"
                    ],
                    "event": "TARGET_2_HIT",
                    "entry": trade[
                        "entry"
                    ],
                    "exit_price": trade[
                        "target2"
                    ],
                    "quantity": trade[
                        "risk"
                    ]["recommended_qty"],
                    "pnl": round(
                        (
                            trade[
                                "target2"
                            ]
                            - trade[
                                "entry"
                            ]
                        )
                        * trade[
                            "risk"
                        ]["recommended_qty"],
                        2,
                    ),
                })

            if (
                not trade["target3_hit"]
                and price
                >= trade["target3"]
            ):

                trade[
                    "target3_hit"
                ] = True

                event = _terminal_event(
                    strategy,
                    trade,
                    "TARGET_3_HIT",
                    trade["target3"],
                    timestamp,
                )

                del _active_trades[
                    strategy
                ][trade_id]

                if event:
                    events.append(
                        event
                    )

                continue

            if price <= trade[
                "stop_loss"
            ]:

                event = _terminal_event(
                    strategy,
                    trade,
                    "STOP_LOSS_HIT",
                    trade["stop_loss"],
                    timestamp,
                )

                del _active_trades[
                    strategy
                ][trade_id]

                if event:
                    events.append(
                        event
                    )

        # ----------------------------------------------------
        # SELL
        # ----------------------------------------------------

        else:

            if (
                not trade["target1_hit"]
                and price
                <= trade["target1"]
            ):

                trade[
                    "target1_hit"
                ] = True

                _stats[
                    strategy
                ]["target1"] += 1

                events.append({
                    "trade_id": trade_id,
                    "strategy": strategy,
                    "symbol": symbol,
                    "display_symbol": trade[
                        "display_symbol"
                    ],
                    "trade_number": trade[
                        "trade_number"
                    ],
                    "event": "TARGET_1_HIT",
                    "entry": trade[
                        "entry"
                    ],
                    "exit_price": trade[
                        "target1"
                    ],
                    "quantity": trade[
                        "risk"
                    ]["recommended_qty"],
                    "pnl": round(
                        (
                            trade[
                                "entry"
                            ]
                            - trade[
                                "target1"
                            ]
                        )
                        * trade[
                            "risk"
                        ]["recommended_qty"],
                        2,
                    ),
                })

            if (
                not trade["target2_hit"]
                and price
                <= trade["target2"]
            ):

                trade[
                    "target2_hit"
                ] = True

                _stats[
                    strategy
                ]["target2"] += 1

                events.append({
                    "trade_id": trade_id,
                    "strategy": strategy,
                    "symbol": symbol,
                    "display_symbol": trade[
                        "display_symbol"
                    ],
                    "trade_number": trade[
                        "trade_number"
                    ],
                    "event": "TARGET_2_HIT",
                    "entry": trade[
                        "entry"
                    ],
                    "exit_price": trade[
                        "target2"
                    ],
                    "quantity": trade[
                        "risk"
                    ]["recommended_qty"],
                    "pnl": round(
                        (
                            trade[
                                "entry"
                            ]
                            - trade[
                                "target2"
                            ]
                        )
                        * trade[
                            "risk"
                        ]["recommended_qty"],
                        2,
                    ),
                })

            if (
                not trade["target3_hit"]
                and price
                <= trade["target3"]
            ):

                trade[
                    "target3_hit"
                ] = True

                event = _terminal_event(
                    strategy,
                    trade,
                    "TARGET_3_HIT",
                    trade["target3"],
                    timestamp,
                )

                del _active_trades[
                    strategy
                ][trade_id]

                if event:
                    events.append(
                        event
                    )

                continue

            if price >= trade[
                "stop_loss"
            ]:

                event = _terminal_event(
                    strategy,
                    trade,
                    "STOP_LOSS_HIT",
                    trade["stop_loss"],
                    timestamp,
                )

                del _active_trades[
                    strategy
                ][trade_id]

                if event:
                    events.append(
                        event
                    )

    return events


# ============================================================
# ACTIVE TRADES
# ============================================================

def get_active_trades(
    strategy=None,
):

    if strategy is None:

        return {
            name: dict(
                _active_trades[name]
            )
            for name in STRATEGIES
        }

    if strategy not in STRATEGIES:
        return {}

    return dict(
        _active_trades[strategy]
    )


def get_strategies():

    return list(
        STRATEGIES
    )


# ============================================================
# END OF DAY
# ============================================================

def finalize_replay(
    timestamp=None,
):

    if timestamp is None:
        timestamp = datetime.now()

    results = []

    for strategy in STRATEGIES:

        trade_ids = list(
            _active_trades[
                strategy
            ].keys()
        )

        for trade_id in trade_ids:

            trade = _active_trades[
                strategy
            ].pop(
                trade_id,
                None,
            )

            if trade is None:
                continue

            _stats[
                strategy
            ]["eod"] += 1

            results.append({
                "trade_id": trade_id,
                "strategy": strategy,
                "symbol": trade[
                    "symbol"
                ],
                "display_symbol": trade[
                    "display_symbol"
                ],
                "trade_number": trade[
                    "trade_number"
                ],
                "event": "EOD_EXIT",
                "exit_reason": "END OF REPLAY",
                "entry": trade[
                    "entry"
                ],
                "exit_price": trade[
                    "entry"
                ],
                "quantity": trade[
                    "risk"
                ]["recommended_qty"],
                "pnl": 0.0,
            })

    return results


# ============================================================
# REPORT
# ============================================================

def get_stats(
    strategy=None,
):

    if strategy is None:

        return {
            name: dict(
                _stats[name]
            )
            for name in STRATEGIES
        }

    if strategy not in STRATEGIES:
        return {}

    return dict(
        _stats[strategy]
    )


def get_report():

    report = {}

    for strategy in STRATEGIES:

        stats = _stats[
            strategy
        ]

        completed = (
            stats["wins"]
            + stats["losses"]
        )

        if completed:

            win_rate = (
                stats["wins"]
                / completed
            ) * 100

        else:

            win_rate = 0.0

        net_pnl = (
            stats["gross_profit"]
            - stats["gross_loss"]
        )

        report[strategy] = {
            "signals": stats[
                "signals"
            ],
            "trades": stats[
                "trades"
            ],
            "completed": completed,
            "wins": stats[
                "wins"
            ],
            "losses": stats[
                "losses"
            ],
            "eod": stats[
                "eod"
            ],
            "target1": stats[
                "target1"
            ],
            "target2": stats[
                "target2"
            ],
            "target3": stats[
                "target3"
            ],
            "stoploss": stats[
                "stoploss"
            ],
            "win_rate": round(
                win_rate,
                2,
            ),
            "gross_profit": round(
                stats[
                    "gross_profit"
                ],
                2,
            ),
            "gross_loss": round(
                stats[
                    "gross_loss"
                ],
                2,
            ),
            "net_pnl": round(
                net_pnl,
                2,
            ),
        }

    return report


def print_report():

    report = get_report()

    print()
    print("=" * 96)
    print(
        "🏆 PAISAAI FAIR REPLAY "
        "STOP-LOSS COMPARISON"
    )
    print("=" * 96)

    print(
        f"{'STRATEGY':<12}"
        f"{'SIGNALS':>9}"
        f"{'DONE':>8}"
        f"{'WINS':>8}"
        f"{'LOSS':>8}"
        f"{'WIN %':>10}"
        f"{'GROSS +':>14}"
        f"{'GROSS -':>14}"
        f"{'NET P&L':>14}"
    )

    print("-" * 96)

    for strategy in STRATEGIES:

        row = report[
            strategy
        ]

        print(
            f"{strategy:<12}"
            f"{row['signals']:>9}"
            f"{row['completed']:>8}"
            f"{row['wins']:>8}"
            f"{row['losses']:>8}"
            f"{row['win_rate']:>9.2f}%"
            f"{row['gross_profit']:>14.2f}"
            f"{row['gross_loss']:>14.2f}"
            f"{row['net_pnl']:>14.2f}"
        )

    print("-" * 96)

    ranked = sorted(
        report.items(),
        key=lambda item: (
            item[1]["net_pnl"],
            item[1]["win_rate"],
        ),
        reverse=True,
    )

    if ranked:

        winner = ranked[0][0]
        data = ranked[0][1]

        print()
        print(
            f"🏆 BEST NET P&L : "
            f"{winner}"
        )

        print(
            f"📈 Net P&L      : "
            f"₹{data['net_pnl']:.2f}"
        )

        print(
            f"🎯 Win Rate     : "
            f"{data['win_rate']:.2f}%"
        )

    print()
    print(
        "ℹ️ T1/T2 are milestones only."
    )

    print(
        "ℹ️ Win = T3 terminal exit."
    )

    print(
        "ℹ️ Loss = Stop Loss terminal exit."
    )

    print(
        "ℹ️ EOD trades are excluded from "
        "win-rate calculation."
    )

    print("=" * 96)
    print()

    return report


# ============================================================
# OHLC CANDLE UPDATE
# ============================================================

def update_candle(
    strategy,
    symbol,
    high,
    low,
    timestamp=None,
):
    """
    Evaluate one OHLC candle against each active virtual
    trade independently.

    Conservative intrabar assumption:

        BUY  -> LOW first, HIGH second
        SELL -> HIGH first, LOW second

    This prevents a BUY trade from using the SELL sequence,
    and vice versa.
    """

    if strategy not in STRATEGIES:
        return []

    if timestamp is None:
        timestamp = datetime.now()

    high = _safe_float(high)
    low = _safe_float(low)

    if high is None or low is None:
        return []

    snapshot = [
        (
            trade_id,
            trade["action"],
        )
        for trade_id, trade
        in list(
            _active_trades[strategy].items()
        )
        if trade["symbol"] == symbol
    ]

    events = []

    for trade_id, action in snapshot:

        # Trade may already have been closed by an earlier
        # event on this same candle.
        if trade_id not in _active_trades[strategy]:
            continue

        if action == "BUY":

            result = update_trade(
                strategy,
                symbol,
                low,
                timestamp,
                trade_id,
            )

            if result:
                events.extend(
                    result
                    if isinstance(result, list)
                    else [result]
                )

            if trade_id not in _active_trades[strategy]:
                continue

            result = update_trade(
                strategy,
                symbol,
                high,
                timestamp,
                trade_id,
            )

            if result:
                events.extend(
                    result
                    if isinstance(result, list)
                    else [result]
                )

        else:

            result = update_trade(
                strategy,
                symbol,
                high,
                timestamp,
                trade_id,
            )

            if result:
                events.extend(
                    result
                    if isinstance(result, list)
                    else [result]
                )

            if trade_id not in _active_trades[strategy]:
                continue

            result = update_trade(
                strategy,
                symbol,
                low,
                timestamp,
                trade_id,
            )

            if result:
                events.extend(
                    result
                    if isinstance(result, list)
                    else [result]
                )

    return events
