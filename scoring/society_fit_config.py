"""
Config for the society-level product-fit layer (rung 3: city -> corridor ->
society -> people, 2026-07-06). This is a NEW, independent score - separate
from scoring/society_config.py (the older society scorer, unused since it
reads classified_listings which has stayed empty since the pipeline moved
to the deterministic raw_listings path) and from corridor fit_score /
absentee_score. Never merged with either.

Weights were specified directly by the user, not derived: supply 0.30,
velocity 0.30, consistency 0.20, rating 0.20. When rating is unavailable for
a society, the remaining three are re-normalized to sum to 1 rather than
just dropping the rating term unweighted (see scoring/society_fit.py).
"""

from dataclasses import dataclass

MIN_LISTINGS = 3  # societies with fewer in-band canonical listings are dropped - too small a sample to rank on

WEIGHT_SUPPLY = 0.30
WEIGHT_VELOCITY = 0.30
WEIGHT_CONSISTENCY = 0.20
WEIGHT_RATING = 0.20


@dataclass(frozen=True)
class MapsConfig:
    api_key_env: str = "GOOGLE_MAPS_API_KEY"
    rate_limit_seconds: float = 1.0  # politeness delay between live Maps lookups (cache hits skip this)
    request_timeout_seconds: float = 10.0


MAPS = MapsConfig()
