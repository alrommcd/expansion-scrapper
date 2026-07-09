"""
Absentee/NRI lead-scoring config. Single source of truth, backend-only
(CLAUDE.md hard constraint). Point values and thresholds are exactly as
specified by the user 2026-07-04 (DECISIONS.md); the flag-to-tier mapping
below is this implementation's structuring of that spec.

Tier 3 has 2 signals here, not 3: a surname-based signal was requested and
explicitly declined (bias-prone, excluded in the original kickoff brief).
"""

TIER1_POINTS = 40
TIER2_POINTS = 20
TIER3_POINTS = 10

HOT_THRESHOLD = 60
WARM_THRESHOLD = 30

# A listing's price-per-sqft below this fraction of the corridor's median
# price-per-sqft counts as the Tier 3 "below-market price" signal. User
# override of the classifier's "never infer NRI from price" rule - real
# false-positive risk, see DECISIONS.md 2026-07-04.
BELOW_MARKET_RATIO = 0.7

TIER1_FLAGS = (
    "flag_nri_mention",
    "flag_poa_mention",
    "flag_owner_abroad",
    "flag_international_contact_hint",
)

TIER2_FLAGS = (
    "flag_owner_not_local",
    "flag_visit_by_appointment_only",
    "flag_calling_hours_hint",
    "flag_long_vacant_or_tenanted",
    "flag_investment_property_mention",
)

MAX_POSSIBLE_SCORE = len(TIER1_FLAGS) * TIER1_POINTS + len(TIER2_FLAGS) * TIER2_POINTS + 2 * TIER3_POINTS


def lead_tier(score: int) -> tuple[str, str]:
    if score >= HOT_THRESHOLD:
        return "hot", "Hot NRI lead \U0001F525"  # fire emoji
    if score >= WARM_THRESHOLD:
        return "warm", "Warm lead ⚡"  # high-voltage emoji
    return "cold", "Cold, skip"
