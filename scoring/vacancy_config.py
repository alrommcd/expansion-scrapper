"""
Layer 2B vacancy/staleness config. Single source of truth, backend-only
(CLAUDE.md hard constraint). This is a proxy signal, not direct detection
(user's own framing, 2026-07-04/05, DECISIONS.md): high vacancy + long
average listing age suggests an absentee-heavy society, it does not prove
it. Thresholds are this implementation's structuring of the user's spec,
not independently re-derived.

Deliberately 100% deterministic, no Gemini call anywhere in this layer -
listing age, price, and society name are all near-structured MagicBricks
fields (see classify/parsing.py), so there is nothing here that benefits
from an LLM read, and it keeps this layer fast/free/fully auditable.
"""

STALE_THRESHOLD_60D = 60
STALE_THRESHOLD_90D = 90

# Normalization cap for average listing age -> 0-1 score. A society whose
# listings average this age or older gets the max staleness contribution.
AVG_AGE_CAP_DAYS = 180
