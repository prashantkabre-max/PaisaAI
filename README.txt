PaisaAI Shadow Sentiment Stabilization
Source baseline: PaisaAI_GOLDEN1_2026-08-10_SHADOW_SENTIMENT.zip

Changes:
1. Shadow sentiment no longer prints as a standalone line.
2. Shadow sentiment is attached to an accepted trade and printed once inside its banner.
3. Raw score is smoothed over a 3-sample rolling window per symbol.
4. Shadow remains observation-only and cannot alter production decisions.
5. Shadow failures cannot interrupt production trade processing.
6. Shadow logs include raw_score and stabilized score.
7. Replay code is not changed by this patch.

Apply:
- scanner_live_sentiment_shadow.py -> scanner/live_sentiment_shadow.py
- scanner_stream.py -> scanner/stream.py
