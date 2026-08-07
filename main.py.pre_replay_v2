import sys

from scanner.stream import LiveStreamer
from scanner.watchlist import get_watchlist
from scanner.replay_feed import start_replay_feed
from scanner.runtime import set_risk_mode

from data.preload import preload_history


def run_live(watchlist):
    """
    Start normal PaisaAI live-market mode.
    """

    print("\n==============================================================")
    print("🚀 PAISAAI LIVE SCANNER")
    from scanner.runtime import get_risk_mode
    print(f"🟢 MODE : {get_risk_mode().upper()}")
    print("==============================================================\n")

    streamer = LiveStreamer()
    streamer.start()



def run_replay(watchlist):
    """
    PaisaAI Replay V2
    """

    print("\n==============================================================")
    print("🎬 PAISAAI REPLAY ENGINE V2")
    print("==============================================================\\n")

    start_replay_feed()

def main():

    watchlist = get_watchlist()
    mode = sys.argv[1].strip().lower() if len(sys.argv) > 1 else "production"

    if len(sys.argv) > 1:
        mode = sys.argv[1].strip().lower()

    if mode not in ("production", "replay"):
        print("Usage:")
        print("  python main.py production")
        print("  python main.py replay")
        return

    preload_history(watchlist)

    if mode == "replay":
        run_replay(watchlist)
        return

    risk_mode = "production"

    if mode == "diagnostic":
        risk_mode = "diagnostic"
    elif mode == "aggressive":
        risk_mode = "aggressive"

    run_live(watchlist)


if __name__ == "__main__":
    main()

