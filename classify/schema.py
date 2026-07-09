"""
Structured output contracts.

`GeminiFlags` is what Gemini fills in: it only ever reads free text and
classifies/normalizes it (CLAUDE.md hard rule: the LLM never invents
numbers and never scores). Price, area, BHK, and listing_type are NOT
asked of Gemini, they are parsed deterministically in classify/parsing.py
because MagicBricks already presents them as near-structured labeled
fields, and a regex parse carries zero hallucination risk on a number that
a LLM call would.

Absentee/NRI flags are tiered per the user's 2026-07-04 expansion of the
original 4-signal design (DECISIONS.md). Tier 1 and Tier 2 flags below are
all explicit-text judgment calls (Gemini's job). Two Tier 3 signals
(below-market price, NRI-heavy society) are comparative/config-driven, not
intrinsic to one listing in isolation, so they are computed in
scoring/absentee.py instead of here. A surname-based Tier 3 signal was
requested and explicitly declined (bias-prone, excluded in the original
kickoff brief).

`ListingClassification` is the full row shape written to
classified_listings (parsing.py output merged with GeminiFlags output).
"""

from pydantic import BaseModel


class GeminiFlags(BaseModel):
    listing_index: int  # position in the batch, so responses can be matched back to inputs
    society_name_normalized: str | None

    # Tier 1 (explicit, high confidence)
    flag_nri_mention: bool
    flag_poa_mention: bool  # includes "power of attorney" and "attorney holder"
    flag_owner_abroad: bool  # explicit "owner abroad" / "owner overseas"

    # Tier 2 (explicit, medium confidence)
    flag_owner_not_local: bool  # generic "not local" / "out of station" / other city
    flag_visit_by_appointment_only: bool
    flag_calling_hours_hint: bool  # e.g. "call after 7pm IST"
    flag_long_vacant_or_tenanted: bool  # long-tenanted, vacant 6+ months, or repeatedly re-listed
    flag_investment_property_mention: bool  # "rental income" / "investment property"


class GeminiFlagsBatch(BaseModel):
    items: list[GeminiFlags]


class ListingClassification(BaseModel):
    society_name_as_written: str | None
    price_inr: int | None
    area_sqft: int | None
    bhk: int | None
    listing_type: str  # 'owner' | 'agent' | 'unknown'
    possession_status: str  # 'ready_to_move' | 'under_construction' | 'unknown'
    days_since_posted: int | None
    mentions_rera: bool

    flag_nri_mention: bool
    flag_poa_mention: bool
    flag_owner_abroad: bool
    flag_owner_not_local: bool
    flag_visit_by_appointment_only: bool
    flag_calling_hours_hint: bool
    flag_long_vacant_or_tenanted: bool
    flag_investment_property_mention: bool
    flag_international_contact_hint: bool  # deterministic regex on already-scraped text, not a fetched phone number
