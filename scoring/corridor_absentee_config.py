"""
Corridor-level Absentee Score config (Phase B). Deterministic only, no
Gemini. 3-signal formula (2026-07-05, DECISIONS.md): avg_age_days was
dropped entirely - it was both redundant with stale_90d_pct (both derived
from the same days_since_posted per-listing data) and structurally unable
to affect the score (max contribution 0.2 vs stale's 35, a 175x scale
mismatch that no amount of real-world data could overcome). Removing it
lost no real information; avg_age_days is still computed and stored for
information, it just doesn't feed the score anymore.

Note on the curve: 1 - exp(-raw/5) is strictly increasing for all raw > 0,
so no two different raw values produce the same score mathematically.
But at 1-decimal rounding, raw values above ~26.5 all round to 10.0 (the
curve's derivative gets very small out there) - this is an inherent
property of any curve bounded on [0, 10] with finite display precision,
not a flaw specific to this implementation.
"""

import math

STALE_90D_THRESHOLD_DAYS = 90

# A listing counts as "distressed" only if BOTH conditions hold - cheap
# alone isn't distress, it might just be priced right and sell fast.
DISTRESSED_BELOW_MARKET_RATIO = 0.85  # price/sqft below 85% of corridor median (15%+ below)
DISTRESSED_MIN_AGE_DAYS = 60

WEIGHT_STALE_90D = 0.45
WEIGHT_VACANCY = 0.35
WEIGHT_DISTRESSED = 0.20

EXP_DECAY = 5


def compute_raw(stale_90d_pct: float, vacancy_pct: float, distressed_pct: float) -> float:
    return (
        stale_90d_pct * WEIGHT_STALE_90D
        + vacancy_pct * WEIGHT_VACANCY
        + distressed_pct * WEIGHT_DISTRESSED
    )


def absentee_score_from_raw(raw: float) -> float:
    return round(10 * (1 - math.exp(-raw / EXP_DECAY)), 1)
