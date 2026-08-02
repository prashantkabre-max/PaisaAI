from scanner.replay_indicators.engine import calculate_all_indicators


class IndicatorState:

    def __init__(self):
        self._symbol_cache = {}

    def clear(self):
        self._symbol_cache.clear()

    def calculate(self, symbol, history):

        count = len(history)

        state = self._symbol_cache.get(symbol)

        if (
            state is not None
            and state["count"] == count
        ):
            return state["result"]

        result = calculate_all_indicators(
            history,
            symbol,
        )

        self._symbol_cache[symbol] = {
            "count": count,
            "result": result,
        }

        return result
