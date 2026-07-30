from datetime import datetime

from data.candles import preload_candle


class ReplayEngine:

    def __init__(self, streamer):
        self.streamer = streamer

    def replay(self, symbol, candles):

        print(f"\n▶️ Starting replay for {symbol} ({len(candles)} candles)\n")

        for candle in candles:

            preload_candle(symbol, candle)

            market = {
                "symbol": symbol,

                "ltp": candle["close"],

                "open": candle["open"],
                "high": candle["high"],
                "low": candle["low"],
                "close": candle["close"],

                "volume": candle.get("volume", 0),

                "timestamp": candle.get(
                    "timestamp",
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                ),
            }

            self.streamer.process_completed_candle(market)

        print("\n✅ Replay completed.\n")
