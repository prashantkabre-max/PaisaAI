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
    Display ranked trades with risk levels.
    """

    ranked = top_trades(trades)

    if not ranked:
        print("\nNo qualifying trades found.\n")
        return

    print("\n" + "=" * 100)
    print("                        PAISAAI TOP TRADE RANKINGS")
    print("=" * 100)

    for index, trade in enumerate(ranked, start=1):

        risk = trade.get("risk") or {}

        print(
            f"{index:2}. "
            f"{trade.get('symbol','-'):<15} "
            f"{trade.get('action','-'):>5} "
            f"{trade.get('grade','-'):>2} "
            f"{trade.get('confidence',0):>3}%"
        )

        if risk:
            print(
                f"    Entry: {risk.get('entry','-')} | "
                f"SL: {risk.get('stop_loss','-')} | "
                f"T1: {risk.get('target1','-')} | "
                f"R:R {risk.get('risk_reward','-')}:1"
            )

    print("=" * 100)
