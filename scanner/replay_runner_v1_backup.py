from indicators.engine import calculate_all_indicators
from scanner.indicators import calculate_indicators
from scanner.scoring import calculate_score
from scanner.decision import evaluate_trade


class ReplayRunner:

    def evaluate(self, symbol, history, market):

        all_indicators = calculate_all_indicators(
            history,
            symbol,
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
