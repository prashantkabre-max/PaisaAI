import config
import upstox_client

from datetime import date
from data.candles import update_tick

configuration = upstox_client.Configuration()
configuration.access_token = config.ACCESS_TOKEN

api_client = upstox_client.ApiClient(configuration)
history_api = upstox_client.HistoryApi(api_client)


def preload_history(symbols):

    print("Preloading historical candles...")

    for symbol in symbols:

        try:

            response = history_api.get_historical_candle_data(
                symbol,
                "1minute",
                date.today().strftime("%Y-%m-%d"),
                "2.0",
            )

            candles = response.data.candles

            candles.reverse()

            for c in candles:

                timestamp = c[0]
                high = c[2]
                low = c[3]
                close = c[4]
                volume = c[5]

                update_tick(
                    symbol,
                    close,
                    volume,
                    timestamp,
                )

            print(f"{symbol}: {len(candles)} candles loaded")

        except Exception as e:

            print(symbol, e)

    print("History preload completed.")
