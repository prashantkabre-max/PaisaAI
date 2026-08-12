PaisaAI Replay Engine Consolidated Update — 2026-08-11

Based on the uploaded Golden Checkpoint #3, Replay Golden3 implementation,
and the latest available stabilized sentiment patch/reference.

This bundle changes Replay only:
- Dynamic SL lifecycle mirrors Production.
- Replay event banners show T1/T2/T3/SL dynamic transitions.
- Replay summary banner emits every 10 replay candles (1-minute candles = 10 minutes).
- Replay final summary includes Dynamic SL, Sentiment, and Depth counters.
- Market Depth uses the shared V1 engine with deterministic OHLCV proxy when historical order-book data is unavailable.
- Replay converts historical timestamp strings to datetime before calling the shared depth engine.
- Optional REPLAY_SYMBOL_LIMIT supports short validation; default remains full watchlist.
- No production stream.py or production trade manager is included/changed.
- Existing indicators/scoring are untouched.
