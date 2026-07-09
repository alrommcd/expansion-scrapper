"""
Chennai city config. Corridor names are Claude's proposal (well-known
IT-corridor localities), approved by the user 2026-07-05 since the pivot
message didn't specify Chennai explicitly (DECISIONS.md). All
corridor_candidates metrics and canonical_societies below are SEED /
PLACEHOLDER values - this city has not been scraped at all yet.
"""

from config.city_config import (
    CityConfig,
    CorridorCandidate,
    DemandAnchor,
    ListingSourceConfig,
    RERASource,
)

CHENNAI = CityConfig(
    city_id="chennai",
    city_name="Chennai",
    state="Tamil Nadu",
    rera_source=RERASource(
        name="TN-RERA",
        url="https://rera.tn.gov.in/",
        note="Verified reachable 2026-07-05 (200, real content, title ':: TNRERA ::'). "
        "Note: tnrera.in is a parked domain, NOT the real site - do not use it.",
    ),
    product_price_band_min_inr=7_500_000,   # Rs 75L
    product_price_band_max_inr=15_000_000,  # Rs 1.5Cr
    demand_anchors=[
        DemandAnchor(name="OMR / Sholinganallur IT Corridor", lat=12.9010, lon=80.2279),
        DemandAnchor(name="Siruseri (SIPCOT IT Park)", lat=12.8232, lon=80.2242),
    ],
    listing_sources=[
        ListingSourceConfig(
            source="99acres",
            active=False,
            note="Blocked by Akamai bot protection account/deployment-wide (recon 2026-07-03, Pune). Not re-tested per-city, assumed to carry over.",
        ),
        ListingSourceConfig(
            source="magicbricks",
            active=True,
            note="Server-rendered, not blocked for Pune. Not yet scraped for Chennai.",
        ),
        ListingSourceConfig(
            source="nobroker",
            active=False,
            note="Listings client-rendered via internal JSON APIs. Deferred, same as Pune.",
        ),
    ],
    corridor_candidates=[
        CorridorCandidate(
            name="OMR",
            pct_units_in_band=0.50,
            min_distance_to_demand_anchor_km=1.0,
            rera_clean_pct=0.80,
            comp_count_90d=44,
            avg_dom_days=40,
            resale_txn_count_90d=28,
            canonical_societies=["OMR Society Seed 01"],
        ),
        CorridorCandidate(
            name="Sholinganallur",
            pct_units_in_band=0.52,
            min_distance_to_demand_anchor_km=1.5,
            rera_clean_pct=0.79,
            comp_count_90d=40,
            avg_dom_days=42,
            resale_txn_count_90d=26,
            canonical_societies=["Sholinganallur Society Seed 01"],
        ),
        CorridorCandidate(
            name="Perungudi",
            pct_units_in_band=0.45,
            min_distance_to_demand_anchor_km=3.0,
            rera_clean_pct=0.81,
            comp_count_90d=36,
            avg_dom_days=44,
            resale_txn_count_90d=24,
            canonical_societies=["Perungudi Society Seed 01"],
        ),
        CorridorCandidate(
            name="Siruseri",
            pct_units_in_band=0.60,
            min_distance_to_demand_anchor_km=6.0,
            rera_clean_pct=0.76,
            comp_count_90d=28,
            avg_dom_days=52,
            resale_txn_count_90d=18,
            canonical_societies=["Siruseri Society Seed 01"],
        ),
    ],
)
