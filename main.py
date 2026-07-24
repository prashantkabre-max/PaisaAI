from scanner.stream import LiveStreamer
from scanner.watchlist import get_watchlist
from data.preload import preload_history


def main():
    watchlist = get_watchlist()

    preload_history(watchlist)

    streamer = LiveStreamer()
    streamer.start()


if __name__ == "__main__":
    main()
