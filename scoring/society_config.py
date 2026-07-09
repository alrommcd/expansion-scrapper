"""
Society scoring config. Single source of truth, backend-only (CLAUDE.md
hard constraint). The 5 signals themselves were confirmed with the user in
Plan Mode (DECISIONS.md 2026-07-03): price-band fit, resale liquidity,
listing density, RERA/title cleanliness, possession status. Weights were
not specified, so equal weighting is used, same assumption as the corridor
gates (scoring/gate_config.py).

Two of the five signals are PROXIES forced by what a single listings scrape
can actually see, not the literal locked definition, documented here so
they don't get mistaken for verified data:

- resale_liquidity: the locked definition is "recent transaction count +
  days-on-market". We only see active listings, not historical sales, so
  it's approximated as listing freshness (days_since_posted, from the
  source's "posted/updated X ago" text) averaged across the society. A
  true version needs historical transaction data (comps / IGR, v2 scope).
- title_cleanliness: the locked definition is RERA-clean / clear title. We
  approximate it as the share of listings whose free-text description
  mentions "RERA" at all, not a verified MahaRERA registry lookup. A real
  version queries the city's RERA source (see config/city_config.py
  RERASource) per project, v2 scope.
"""

from dataclasses import dataclass

PRICE_BAND_MIN_INR = 7_500_000  # Rs 75L
PRICE_BAND_MAX_INR = 15_500_000  # Rs 1.55Cr


@dataclass(frozen=True)
class SocietyNormalizationCaps:
    listing_density_cap: int = 10  # listings for a society at/above this count -> density score of 1.0
    recency_cap_days: int = 30  # a listing this stale or older -> recency contribution of 0.0


CAPS = SocietyNormalizationCaps()
