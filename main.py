import sys

from scanner.stream import LiveStreamer
from scanner.watchlist import get_watchlist
from scanner.replay import ReplayEngine

from data.preload import preload_history
from data.candles import get_history


def run_live(watchlist):
    """
    Start normal PaisaAI live-market mode.
    """

    print("\n===================================")
    print("PaisaAI MODE : LIVE")
    print("===================================\n")

    streamer = LiveStreamer()
    streamer.start()


def run_replay(watchlist):
    """
    Run PaisaAI against preloaded historical 1-minute candles.

    Replay uses the same:
        indicators
        scoring
        decision engine
        risk engine
        professional trade banner

    as Live mode.
    """

    print("\n===================================")
    print("PaisaAI MODE : REPLAY")
    print("Symbols       :", len(watchlist))
    print("===================================\n")

    engine = ReplayEngine()

    replayed = 0
    signals = 0

    for symbol in watchlist:
        candles = get_history(
            symbol,
            "1m",
        )

        if not candles:
            continue

        replayed += 1

        result = engine.replay_latest(
            symbol,
            candles,
        )

        if result is None:
            continue

        if result["grade"] != "IGNORE":
            signals += 1

    print("\n===================================")
    print("PaisaAI REPLAY COMPLETED")
    print("Symbols replayed :", replayed)
    print("Trade signals    :", signals)
    print("===================================\n")


def main():
    watchlist = get_watchlist()

    mode = "live"

    if len(sys.argv) > 1:
        mode = sys.argv[1].strip().lower()

    if mode not in ("live", "replay"):
        print("Usage:")
        print("  python main.py")
        print("  python main.py live")
        print("  python main.py replay")
        return

    preload_history(watchlist)

    if mode == "replay":
        run_replay(watchlist)
        return

    run_live(watchlist)


if __name__ == "__main__":
    main()
