"""
Mumbai city config. Corridor names are the user-specified list (2026-07-05,
DECISIONS.md), with one correction (2026-07-06): Thane and Navi Mumbai
404'd against the "mumbai" MagicBricks city slug - they're independent
municipalities with their own separate city slugs in MagicBricks' own
taxonomy (e.g. "thane", "navi-mumbai"), not localities within Mumbai
proper. Rather than extend the scraper to support a per-corridor city-slug
override for this one case, substituted two verified Mumbai-proper
localities instead: Mulund (replacing Thane) and Borivali (replacing Navi
Mumbai). See DECISIONS.md 2026-07-06.

All corridor_candidates metrics and canonical_societies below are SEED /
PLACEHOLDER values, not yet computed from live data or scraped - this city
has not been scraped at all yet. Same honesty convention as Pune's original
placeholder corridors: clearly labeled, never presented as verified.
"""

from config.city_config import (
    CityConfig,
    CorridorCandidate,
    DemandAnchor,
    ListingSourceConfig,
    RERASource,
)

MUMBAI = CityConfig(
    city_id="mumbai",
    city_name="Mumbai",
    state="Maharashtra",
    rera_source=RERASource(
        name="MahaRERA",
        url="https://maharera.mahaonline.gov.in/",
        note="Same state authority as Pune (Maharashtra).",
    ),
    product_price_band_min_inr=7_500_000,   # Rs 75L
    product_price_band_max_inr=15_000_000,  # Rs 1.5Cr
    demand_anchors=[
        DemandAnchor(name="Bandra Kurla Complex (BKC)", lat=19.0662, lon=72.8686),
        DemandAnchor(name="Powai (Hiranandani business hub)", lat=19.1176, lon=72.9060),
        DemandAnchor(name="Andheri East / SEEPZ", lat=19.1197, lon=72.8464),
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
            note="Server-rendered, not blocked for Pune. Not yet scraped for Mumbai.",
        ),
        ListingSourceConfig(
            source="nobroker",
            active=False,
            note="Listings client-rendered via internal JSON APIs. Deferred, same as Pune.",
        ),
    ],
    corridor_candidates=[
        CorridorCandidate(
            name="Powai",
            pct_units_in_band=0.45,
            min_distance_to_demand_anchor_km=0.5,
            rera_clean_pct=0.80,
            comp_count_90d=45,
            avg_dom_days=40,
            resale_txn_count_90d=30,
            canonical_societies=["Powai Society Seed 01", "Powai Society Seed 02"],
        ),
        CorridorCandidate(
            name="Andheri East",
            pct_units_in_band=0.40,
            min_distance_to_demand_anchor_km=0.8,
            rera_clean_pct=0.78,
            comp_count_90d=50,
            avg_dom_days=38,
            resale_txn_count_90d=32,
            canonical_societies=["Andheri East Society Seed 01", "Andheri East Society Seed 02"],
        ),
        CorridorCandidate(
            name="Mulund",
            pct_units_in_band=0.65,
            min_distance_to_demand_anchor_km=9.0,
            rera_clean_pct=0.75,
            comp_count_90d=30,
            avg_dom_days=55,
            resale_txn_count_90d=22,
            canonical_societies=["Mulund Society Seed 01"],
        ),
        CorridorCandidate(
            name="Borivali",
            pct_units_in_band=0.60,
            min_distance_to_demand_anchor_km=10.0,
            rera_clean_pct=0.78,
            comp_count_90d=32,
            avg_dom_days=50,
            resale_txn_count_90d=20,
            canonical_societies=["Borivali Society Seed 01"],
        ),
        CorridorCandidate(
            name="Kandivali",
            pct_units_in_band=0.55,
            min_distance_to_demand_anchor_km=12.0,
            rera_clean_pct=0.70,
            comp_count_90d=22,
            avg_dom_days=65,
            resale_txn_count_90d=15,
            canonical_societies=["Kandivali Society Seed 01"],
        ),
        CorridorCandidate(
            name="Goregaon",
            pct_units_in_band=0.50,
            min_distance_to_demand_anchor_km=8.5,
            rera_clean_pct=0.76,
            comp_count_90d=28,
            avg_dom_days=55,
            resale_txn_count_90d=18,
            canonical_societies=["Goregaon Society Seed 01"],
        ),
        CorridorCandidate(
            name="Malad",
            pct_units_in_band=0.52,
            min_distance_to_demand_anchor_km=11.0,
            rera_clean_pct=0.68,
            comp_count_90d=20,
            avg_dom_days=68,
            resale_txn_count_90d=14,
            canonical_societies=["Malad Society Seed 01"],
        ),
        CorridorCandidate(
            name="Bandra",
            pct_units_in_band=0.25,
            min_distance_to_demand_anchor_km=2.0,
            rera_clean_pct=0.85,
            comp_count_90d=42,
            avg_dom_days=35,
            resale_txn_count_90d=28,
            canonical_societies=["Bandra Society Seed 01"],
        ),
        CorridorCandidate(
            name="Worli",
            pct_units_in_band=0.20,
            min_distance_to_demand_anchor_km=3.0,
            rera_clean_pct=0.88,
            comp_count_90d=35,
            avg_dom_days=40,
            resale_txn_count_90d=20,
            canonical_societies=["Worli Society Seed 01"],
        ),
        CorridorCandidate(
            name="Chembur",
            pct_units_in_band=0.48,
            min_distance_to_demand_anchor_km=6.0,
            rera_clean_pct=0.77,
            comp_count_90d=33,
            avg_dom_days=48,
            resale_txn_count_90d=24,
            canonical_societies=["Chembur Society Seed 01"],
        ),
    ],
)
