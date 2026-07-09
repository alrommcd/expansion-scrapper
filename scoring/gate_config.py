"""
Corridor gate thresholds and normalization caps. Single source of truth for
corridor-level scoring, backend-only (CLAUDE.md hard constraint: metric
definitions and weights never reach the frontend).

The 5 corridor metrics themselves are LOCKED per the kickoff brief and must
not be re-derived. The specific threshold values and the "pass all 5 gates,
then rank survivors by an equal-weighted composite" combination rule below
are this implementation's assumption (flagged in DECISIONS.md 2026-07-03),
since the brief specified the metrics but not exact cutoffs or weights.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class GateThresholds:
    min_pct_units_in_band: float = 0.35
    max_distance_to_demand_anchor_km: float = 8.0
    min_rera_clean_pct: float = 0.75
    min_comp_count_90d: int = 25
    max_avg_dom_days: float = 60.0
    min_resale_txn_count_90d: int = 20


@dataclass(frozen=True)
class NormalizationCaps:
    """Fixed scales used to convert each raw metric into a 0-1 sub-score for
    ranking survivors. Fixed (not min-max over the candidate batch) so a
    corridor's score doesn't shift depending on what else is in the batch."""

    demand_anchor_distance_cap_km: float = 8.0  # matches the gate cutoff
    comp_density_cap: float = 60.0
    dom_days_cap: float = 60.0  # matches the gate cutoff
    resale_txn_cap: float = 50.0


GATES = GateThresholds()
CAPS = NormalizationCaps()
