from scanner.stream import LiveStreamer
from scanner.watchlist import get_watchlist
from data.preload import preload_history
from data.history import load_history
from scanner.replay import ReplayEngine

# -------------------------------------------------
# MODE SELECTION
# False = Live Market
# True  = Replay Mode
# -------------------------------------------------
REPLAY_MODE = True


def main():

    watchlist = get_watchlist()

    streamer = LiveStreamer()
    replay = ReplayEngine(streamer)

    if REPLAY_MODE:

        # Start with ONE symbol for validation.
        # After verification we'll expand to NIFTY200.
        symbol = watchlist[0]

        print(f"\n▶ Replay Mode : {symbol}")

        candles = load_history(symbol)

        replay.replay(symbol, candles)

    else:

        print("\n▶ Live Mode")

        preload_history(watchlist)

        streamer.start()


if __name__ == "__main__":
    main()
