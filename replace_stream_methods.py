from pathlib import Path

stream_path = Path("scanner/stream.py")
text = stream_path.read_text(encoding="utf-8")


def replace_between(source, start_marker, end_marker, replacement):
    start = source.index(start_marker)
    end = source.index(end_marker, start)
    return source[:start] + replacement + "\n\n" + source[end:]


new_calculate_indicators = '''    def calculate_indicators(self, market):

        from scanner.indicators import calculate_indicators

        history = {}

        for timeframe in (
            "1m",
            "3m",
            "5m",
            "15m",
            "30m",
            "60m",
        ):
            history[timeframe] = get_history(
                market["symbol"],
                timeframe,
            )

        all_indicators = calculate_all_indicators(
            history,
            market["symbol"],
        )

        timeframe_indicators = {}

        for timeframe, indicator_values in all_indicators.items():

            timeframe_indicators[timeframe] = calculate_indicators(
                market,
                indicator_values,
            )

        return timeframe_indicators
'''

new_calculate_trade = '''    def calculate_trade(self, timeframe_indicators):

        if timeframe_indicators is None:
            return None

        buy_score = calculate_mtf_score(
            timeframe_indicators,
            "BUY",
        )

        sell_score = calculate_mtf_score(
            timeframe_indicators,
            "SELL",
        )

        if buy_score is None and sell_score is None:
            return None

        if sell_score["confidence"] > buy_score["confidence"]:
            score_result = sell_score
        else:
            score_result = buy_score

        indicators = timeframe_indicators.get("1m")

        if indicators is None:
            return None

        return evaluate_trade(
            indicators,
            score_result,
        )
'''

text = replace_between(
    text,
    "    def calculate_indicators",
    "    def calculate_trade",
    new_calculate_indicators,
)

text = replace_between(
    text,
    "    def calculate_trade",
    "    def print_trade",
    new_calculate_trade,
)

stream_path.write_text(text, encoding="utf-8")

print("✅ scanner/stream.py updated successfully")