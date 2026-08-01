from scanner.replay_indicators.engine import calculate_all_indicators


class IndicatorState:
    """
    V2-B indicator state manager.

    For now this is a compatibility layer that preserves the current
    behaviour. Future versions will replace the full-history calculation
    with incremental indicator updates.
    """

    def __init__(self):
        self._cache = {}

    def clear(self):
        self._cache.clear()

    def calculate(self, symbol, history):
        key = (symbol, len(history))

        if key not in self._cache:
            self._cache[key] = calculate_all_indicators(
                history,
                symbol,
            )

        return self._cache[key]
