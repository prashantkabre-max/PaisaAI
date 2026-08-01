from scanner.indicator_state import IndicatorState
from scanner.indicator_state import IndicatorState
from scanner.scoring import calculate_score
from scanner.decision import evaluate_trade


class ReplayRunner:
    """
    Replay execution engine.

    This class becomes the single entry point for replay evaluation.
    Future V2-B incremental indicator updates will be added here without
    changing ReplayEngine.
    """

    def __init__(self):
        self.state = indicatorstate()

    def _calculate_indicators(self, symbol, history):
        return self.state.calculate(
            symbol,
            history,
        )

    def evaluate(self, symbol, history, market):

        all_indicators = self._calculate_indicators(
            symbol,
            history,
        )

        indicators = calculate_indicators(
            market,
            all_indicators,
        )

        if indicators is None:
            return None

        buy = calculate_score(
            indicators,
            "BUY",
        )

        sell = calculate_score(
            indicators,
            "SELL",
        )

        score = (
            sell
            if sell["confidence"] > buy["confidence"]
            else buy
        )

        return evaluate_trade(
            indicators,
            score,
        )

    def clear_cache(self):
        self._indicator_cache.clear()
