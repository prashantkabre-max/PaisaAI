import config
import upstox_client

from datetime import date

configuration = upstox_client.Configuration()
configuration.access_token = config.ACCESS_TOKEN

api_client = upstox_client.ApiClient(configuration)
history_api = upstox_client.HistoryApi(api_client)


def load_history(
    symbol,
    interval="1minute",
    from_date=None,
    to_date=None,
):
    """
    Load historical candles from Upstox.

    Returns a list of dictionaries compatible with ReplayEngine.
    """

    if to_date is None:
        to_date = date.today().strftime("%Y-%m-%d")

    if from_date is None:
        from_date = to_date

    response = history_api.get_historical_candle_data(
        symbol,
        interval,
        to_date,
        "2.0",
    )

    candles = []

    for c in reversed(response.data.candles):

        candles.append(
            {
                "timestamp": c[0],
                "open": c[1],
                "high": c[2],
                "low": c[3],
                "close": c[4],
                "volume": c[5],
            }
        )

    return candles
