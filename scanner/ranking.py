"""
PaisaAI Trade Ranking Engine
"""


def rank_trades(trades):
    """
    Sort trades by confidence (highest first).
    """

    if not trades:
        return []

    return sorted(
        trades,
        key=lambda trade: (
            trade.get("confidence", 0),
            trade.get("grade", ""),
        ),
        reverse=True,
    )


def top_trades(trades, limit=10):
    """
    Return top N ranked trades.
    """

    return rank_trades(trades)[:limit]


def print_ranking(trades):
    """
    Display ranked trades.
    """

    ranked = top_trades(trades)

    if not ranked:
        print("\nNo qualifying trades found.\n")
        return

    print("\n" + "=" * 70)
    print("                PAISAAI TOP TRADE RANKINGS")
    print("=" * 70)

    for index, trade in enumerate(ranked, start=1):

        print(
            f"{index:2}. "
            f"{trade.get('symbol', '-'):<15} "
            f"{trade.get('signal', '-'):>6}   "
            f"{trade.get('grade', '-'):>2}   "
            f"{trade.get('confidence', 0):>3}%"
        )

    print("=" * 70)
