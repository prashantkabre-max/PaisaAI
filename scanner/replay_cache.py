class ReplayCache:
    """
    Replay history/session helper.

    This module contains all reusable logic for
    working with historical candle data during replay.

    No trading logic belongs here.
    """

    @staticmethod
    def date_of(candle):
        timestamp = candle.get("timestamp")

        if timestamp is None:
            return None

        return str(timestamp)[:10]

    def previous_session_close(
        self,
        candles,
        index,
    ):
        if index <= 0:
            return None

        current_date = self.date_of(candles[index])

        if current_date is None:
            return candles[index - 1].get("close")

        for i in range(index - 1, -1, -1):
            candle = candles[i]

            if self.date_of(candle) != current_date:
                return candle.get("close")

        return None

    def session_ohlc(
        self,
        candles,
        index,
    ):
        current_date = self.date_of(candles[index])

        if current_date is None:
            candle = candles[index]

            return {
                "open": candle.get("open"),
                "high": candle.get("high"),
                "low": candle.get("low"),
            }

        session = []

        for i in range(index, -1, -1):
            candle = candles[i]

            if self.date_of(candle) != current_date:
                break

            session.append(candle)

        session.reverse()

        if not session:
            return {
                "open": None,
                "high": None,
                "low": None,
            }

        highs = [
            c.get("high")
            for c in session
            if c.get("high") is not None
        ]

        lows = [
            c.get("low")
            for c in session
            if c.get("low") is not None
        ]

        return {
            "open": session[0].get("open"),
            "high": max(highs) if highs else None,
            "low": min(lows) if lows else None,
        }
