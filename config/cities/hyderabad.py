"""
Hyderabad city config. Corridor names are Claude's proposal (well-known
IT-hub-adjacent localities), approved by the user 2026-07-05 since the
pivot message didn't specify Hyderabad explicitly (DECISIONS.md). All
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

HYDERABAD = CityConfig(
    city_id="hyderabad",
    city_name="Hyderabad",
    state="Telangana",
    rera_source=RERASource(
        name="TS-RERA",
        url="https://rera.telangana.gov.in/",
        note="Verified reachable 2026-07-05 (200, real content, title 'Welcome to TGRERA').",
    ),
    product_price_band_min_inr=7_500_000,   # Rs 75L
    product_price_band_max_inr=15_000_000,  # Rs 1.5Cr
    demand_anchors=[
        DemandAnchor(name="Hitech City / Madhapur", lat=17.4435, lon=78.3772),
        DemandAnchor(name="Gachibowli", lat=17.4401, lon=78.3489),
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
            note="Server-rendered, not blocked for Pune. Not yet scraped for Hyderabad.",
        ),
        ListingSourceConfig(
            source="nobroker",
            active=False,
            note="Listings client-rendered via internal JSON APIs. Deferred, same as Pune.",
        ),
    ],
    corridor_candidates=[
        CorridorCandidate(
            name="Hitech City",
            pct_units_in_band=0.42,
            min_distance_to_demand_anchor_km=0.5,
            rera_clean_pct=0.83,
            comp_count_90d=46,
            avg_dom_days=38,
            resale_txn_count_90d=30,
            canonical_societies=["Hitech City Society Seed 01"],
        ),
        CorridorCandidate(
            name="Madhapur",
            pct_units_in_band=0.40,
            min_distance_to_demand_anchor_km=0.8,
            rera_clean_pct=0.82,
            comp_count_90d=44,
            avg_dom_days=40,
            resale_txn_count_90d=28,
            canonical_societies=["Madhapur Society Seed 01"],
        ),
        CorridorCandidate(
            name="Gachibowli",
            pct_units_in_band=0.48,
            min_distance_to_demand_anchor_km=1.0,
            rera_clean_pct=0.81,
            comp_count_90d=42,
            avg_dom_days=42,
            resale_txn_count_90d=26,
            canonical_societies=["Gachibowli Society Seed 01"],
        ),
        CorridorCandidate(
            name="Kondapur",
            pct_units_in_band=0.55,
            min_distance_to_demand_anchor_km=2.5,
            rera_clean_pct=0.79,
            comp_count_90d=36,
            avg_dom_days=46,
            resale_txn_count_90d=22,
            canonical_societies=["Kondapur Society Seed 01"],
        ),
        CorridorCandidate(
            name="Kukatpally",
            pct_units_in_band=0.58,
            min_distance_to_demand_anchor_km=7.5,
            rera_clean_pct=0.73,
            comp_count_90d=26,
            avg_dom_days=56,
            resale_txn_count_90d=16,
            canonical_societies=["Kukatpally Society Seed 01"],
        ),
    ],
)
