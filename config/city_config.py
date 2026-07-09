"""
City-agnostic data contracts. Every city plugs into the scoring engine by
producing one CityConfig instance (see config/cities/pune.py for the reference
implementation). The scorer in scoring/corridor.py never imports a city
module directly, it only consumes these dataclasses.
"""

from dataclasses import dataclass, field


@dataclass
class DemandAnchor:
    """A hub where the ICP works (IT park, business district, etc)."""

    name: str
    lat: float
    lon: float


@dataclass
class ListingSourceConfig:
    """Coverage note for one listing source in this city. `active` is False
    when a source is known to have weak or no coverage for this city, so the
    scraper layer can skip it without special-casing the city by name."""

    source: str  # e.g. "99acres", "magicbricks", "nobroker"
    active: bool
    note: str = ""


@dataclass
class RERASource:
    name: str  # e.g. "MahaRERA", "TS-RERA", "K-RERA"
    url: str
    note: str = ""


@dataclass
class CorridorCandidate:
    """Aggregated metrics for one candidate corridor, one row per corridor.

    In v1 these numbers are seeded by hand per city (see cities/pune.py) to
    prove the scoring engine and city-agnostic architecture. From Milestone 2
    onward this same shape is populated by the scraper + RERA + comp
    pipeline instead of being hand-entered. See DECISIONS.md 2026-07-03.
    """

    name: str
    pct_units_in_band: float  # share of stock priced Rs 75L-1.55Cr, 0-1
    min_distance_to_demand_anchor_km: float
    rera_clean_pct: float  # share of projects RERA-clean / clear title, 0-1
    comp_count_90d: int  # recent comps available for day-one pricing
    avg_dom_days: float  # average days-on-market
    resale_txn_count_90d: int  # resale transaction volume, last 90 days
    canonical_societies: list[str] = field(default_factory=list)
    # Explicit, user-curated list of societies known to have high NRI/absentee
    # ownership (from local market knowledge, not an inferred heuristic - see
    # DECISIONS.md 2026-07-04). Empty until the user supplies names; the
    # Tier 3 "NRI-heavy society" absentee signal is false for everyone until
    # then, it is never silently guessed.
    nri_heavy_societies: list[str] = field(default_factory=list)


@dataclass
class CityConfig:
    city_id: str
    city_name: str
    state: str
    rera_source: RERASource
    demand_anchors: list[DemandAnchor]
    listing_sources: list[ListingSourceConfig]
    corridor_candidates: list[CorridorCandidate]
    # HouseEazy's target buy price band for this city, INR. None means no
    # business-confirmed band exists yet for this city - code that depends
    # on it (scoring/society_fit.py) must skip the city and report why, not
    # fall back to another city's numbers (2026-07-06 hard constraint).
    product_price_band_min_inr: int | None = None
    product_price_band_max_inr: int | None = None
