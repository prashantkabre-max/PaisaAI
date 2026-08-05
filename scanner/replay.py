from datetime import datetime

from scanner.replay_indicators.engine import calculate_all_indicators
from scanner.indicators import calculate_indicators
from scanner.replay_runner import ReplayRunner
from scanner.scoring import calculate_score
from scanner.decision import evaluate_trade


class ReplayEngine:
    """
    PaisaAI Replay Engine.

    Replays historical candles through the same indicator
    and scoring pipeline used by the scanner.
    """

    def __init__(self, min_history=50):
        self.min_history = min_history
        self.runner = ReplayRunner()

        from scanner.stream import LiveStreamer

        self.viewer = LiveStreamer.__new__(LiveStreamer)
        self.viewer.trade_number = 0
        self.viewer.live_trades = []
        self.viewer.session_start = datetime.now()
        self.viewer.last_summary = datetime.now()
        self.viewer.session_stats = {
            "total": 0,
            "buy": 0,
            "sell": 0,
            "a_plus": 0,
            "a": 0,
            "active": 0,
            "target1": 0,
            "target2": 0,
            "target3": 0,
            "stoploss": 0,
            "wins": 0,
            "losses": 0,
        }

    @staticmethod
    def _date_of(candle):
        timestamp = candle.get("timestamp")

        if timestamp is None:
            return None

        return str(timestamp)[:10]

    def _previous_session_close(self, candles, index):
        if index <= 0:
            return None

        current_date = self._date_of(candles[index])

        if current_date is None:
            return candles[index - 1].get("close")

        for i in range(index - 1, -1, -1):
            candle = candles[i]

            if self._date_of(candle) != current_date:
                return candle.get("close")

        return None

    def _session_ohlc(self, candles, index):
        current_date = self._date_of(candles[index])

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

            if self._date_of(candle) != current_date:
                break

            session.append(candle)

        session.reverse()

        if not session:
            return {
                "open": None,
                "high": None,
                "low": None,
            }

        day_open = session[0].get("open")

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
            "open": day_open,
            "high": max(highs) if highs else None,
            "low": min(lows) if lows else None,
        }

    def replay_symbol(self, symbol, candles):
        results = []

        if not candles:
            return results

        if len(candles) <= self.min_history:
            return results

        for index in range(
            self.min_history,
            len(candles),
        ):
            history = candles[: index + 1]
            current = candles[index]

            ltp = current.get("close")

            if ltp is None:
                continue

            previous_close = self._previous_session_close(
                candles,
                index,
            )

            if previous_close in (None, 0):
                continue

            session_ohlc = self._session_ohlc(
                candles,
                index,
            )

            all_indicators = calculate_all_indicators(
                history,
                symbol,
            )

            market = {
                "symbol": symbol,
                "ltp": ltp,
                "previous_close": previous_close,
                "open": session_ohlc["open"],
                "high": session_ohlc["high"],
                "low": session_ohlc["low"],
                "close": current.get("close"),
                "volume": current.get("volume", 0),
            }

            indicators = calculate_indicators(
                market,
                all_indicators,
            )

            if indicators is None:
                continue

            buy_score = calculate_score(indicators, "BUY")
            sell_score = calculate_score(indicators, "SELL")

            score = sell_score if sell_score["confidence"] > buy_score["confidence"] else buy_score

            trade = evaluate_trade(
                indicators,
                score,
            )

            if trade is None:
                continue

            results.append({
                "symbol": symbol,
                "display_symbol": indicators["display_symbol"],
                "timestamp": current.get("timestamp"),
                "direction": trade["action"],
                "grade": trade["grade"],
                "confidence": trade["confidence"],
                "passed": trade["passed"],
                "failed": trade["failed"],
                "risk": trade["risk"],
                "trade_timing": trade["trade_timing"],
                "rvol": indicators.get("rvol"),
                "rsi": indicators.get("rsi"),
                "change_percent": indicators.get("change_percent"),
                "ltp": indicators.get("ltp"),
                "session_open": session_ohlc["open"],
                "session_high": session_ohlc["high"],
                "session_low": session_ohlc["low"],
            })

        return results

    def replay_latest(self, symbol, candles):
        results = self.replay_symbol(symbol, candles)

        if not results:
            return None

        result = results[-1]

        if result["grade"] != "IGNORE":
            trade = {
                "symbol": result["symbol"],
                "display_symbol": result["display_symbol"],
                "action": result["direction"],
                "grade": result["grade"],
                "confidence": result["confidence"],
                "passed": result["passed"],
                "failed": result["failed"],
                "risk": result["risk"],
                "rvol": result["rvol"],
                "rsi": result["rsi"],
            }

            self.viewer.print_trade(
                trade,
                replay_mode=True,
                replay_timestamp=result["timestamp"],
            )

        return result
