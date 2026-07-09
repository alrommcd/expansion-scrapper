"""
Bangalore city config. Corridor names are the user-specified list
(2026-07-05, DECISIONS.md). All corridor_candidates metrics and
canonical_societies below are SEED / PLACEHOLDER values - this city has
not been scraped at all yet. See config/cities/pune.py for the placeholder
convention this follows.
"""

from config.city_config import (
    CityConfig,
    CorridorCandidate,
    DemandAnchor,
    ListingSourceConfig,
    RERASource,
)

BANGALORE = CityConfig(
    city_id="bangalore",
    city_name="Bangalore",
    state="Karnataka",
    rera_source=RERASource(
        name="K-RERA",
        url="https://rera.karnataka.gov.in/",
        note="Verified reachable 2026-07-05 (200, real content, title 'Karnataka RERA').",
    ),
    product_price_band_min_inr=7_500_000,   # Rs 75L
    product_price_band_max_inr=15_000_000,  # Rs 1.5Cr
    demand_anchors=[
        DemandAnchor(name="Whitefield (ITPL)", lat=12.9698, lon=77.7500),
        DemandAnchor(name="Electronic City", lat=12.8452, lon=77.6602),
        DemandAnchor(name="Outer Ring Road / Marathahalli", lat=12.9569, lon=77.7011),
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
            note="Server-rendered, not blocked for Pune. Not yet scraped for Bangalore.",
        ),
        ListingSourceConfig(
            source="nobroker",
            active=False,
            note="Listings client-rendered via internal JSON APIs. Deferred, same as Pune.",
        ),
    ],
    corridor_candidates=[
        CorridorCandidate(
            name="Whitefield",
            pct_units_in_band=0.50,
            min_distance_to_demand_anchor_km=1.0,
            rera_clean_pct=0.82,
            comp_count_90d=48,
            avg_dom_days=40,
            resale_txn_count_90d=30,
            canonical_societies=["Whitefield Society Seed 01", "Whitefield Society Seed 02"],
        ),
        CorridorCandidate(
            name="Electronic City",
            pct_units_in_band=0.55,
            min_distance_to_demand_anchor_km=1.2,
            rera_clean_pct=0.80,
            comp_count_90d=45,
            avg_dom_days=42,
            resale_txn_count_90d=28,
            canonical_societies=["Electronic City Society Seed 01"],
        ),
        CorridorCandidate(
            name="Marathahalli",
            pct_units_in_band=0.48,
            min_distance_to_demand_anchor_km=2.0,
            rera_clean_pct=0.79,
            comp_count_90d=40,
            avg_dom_days=44,
            resale_txn_count_90d=26,
            canonical_societies=["Marathahalli Society Seed 01"],
        ),
        CorridorCandidate(
            name="Sarjapur",
            pct_units_in_band=0.58,
            min_distance_to_demand_anchor_km=4.5,
            rera_clean_pct=0.76,
            comp_count_90d=35,
            avg_dom_days=48,
            resale_txn_count_90d=22,
            canonical_societies=["Sarjapur Society Seed 01"],
        ),
        CorridorCandidate(
            name="HSR Layout",
            pct_units_in_band=0.35,
            min_distance_to_demand_anchor_km=3.5,
            rera_clean_pct=0.83,
            comp_count_90d=38,
            avg_dom_days=42,
            resale_txn_count_90d=24,
            canonical_societies=["HSR Layout Society Seed 01"],
        ),
        CorridorCandidate(
            name="Koramangala",
            pct_units_in_band=0.22,
            min_distance_to_demand_anchor_km=5.0,
            rera_clean_pct=0.85,
            comp_count_90d=36,
            avg_dom_days=38,
            resale_txn_count_90d=20,
            canonical_societies=["Koramangala Society Seed 01"],
        ),
        CorridorCandidate(
            name="Hebbal",
            pct_units_in_band=0.52,
            min_distance_to_demand_anchor_km=9.0,
            rera_clean_pct=0.74,
            comp_count_90d=28,
            avg_dom_days=58,
            resale_txn_count_90d=16,
            canonical_societies=["Hebbal Society Seed 01"],
        ),
        CorridorCandidate(
            name="Yelahanka",
            pct_units_in_band=0.60,
            min_distance_to_demand_anchor_km=14.0,
            rera_clean_pct=0.68,
            comp_count_90d=20,
            avg_dom_days=70,
            resale_txn_count_90d=12,
            canonical_societies=["Yelahanka Society Seed 01"],
        ),
    ],
)
