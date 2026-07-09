"""
City-agnostic corridor ranking engine. Contains zero city-specific logic:
it only ever reads CorridorCandidate objects handed to it by a CityConfig
(see config/cities/pune.py). Adding a new city means adding a new city
config module, never touching this file.

Pipeline: for each candidate, evaluate the 5 locked gates -> corridors that
fail any gate are marked ineligible (with the failed gate names, for
auditability) -> corridors that pass all 5 are ranked by an equal-weighted
composite of the 5 normalized sub-scores.
"""

from dataclasses import dataclass

from config.city_config import CorridorCandidate
from scoring.gate_config import CAPS, GATES

GATE_NAMES = (
    "product_in_band",
    "demand_adjacent",
    "clean_title",
    "comp_density",
    "resale_velocity",
)


@dataclass
class CorridorResult:
    name: str
    eligible: bool
    failed_gates: list[str]
    sub_scores: dict[str, float]
    composite_score: float | None  # None when ineligible


def _evaluate_gates(c: CorridorCandidate) -> list[str]:
    failed = []
    if c.pct_units_in_band < GATES.min_pct_units_in_band:
        failed.append("product_in_band")
    if c.min_distance_to_demand_anchor_km > GATES.max_distance_to_demand_anchor_km:
        failed.append("demand_adjacent")
    if c.rera_clean_pct < GATES.min_rera_clean_pct:
        failed.append("clean_title")
    if c.comp_count_90d < GATES.min_comp_count_90d:
        failed.append("comp_density")
    if (
        c.avg_dom_days > GATES.max_avg_dom_days
        or c.resale_txn_count_90d < GATES.min_resale_txn_count_90d
    ):
        failed.append("resale_velocity")
    return failed


def _sub_scores(c: CorridorCandidate) -> dict[str, float]:
    demand_adjacent = max(
        0.0, 1 - c.min_distance_to_demand_anchor_km / CAPS.demand_anchor_distance_cap_km
    )
    comp_density = min(c.comp_count_90d / CAPS.comp_density_cap, 1.0)
    dom_score = max(0.0, 1 - c.avg_dom_days / CAPS.dom_days_cap)
    txn_score = min(c.resale_txn_count_90d / CAPS.resale_txn_cap, 1.0)
    resale_velocity = (dom_score + txn_score) / 2

    return {
        "product_in_band": round(c.pct_units_in_band, 4),
        "demand_adjacent": round(demand_adjacent, 4),
        "clean_title": round(c.rera_clean_pct, 4),
        "comp_density": round(comp_density, 4),
        "resale_velocity": round(resale_velocity, 4),
    }


def rank_corridors(candidates: list[CorridorCandidate]) -> list[CorridorResult]:
    """Returns all candidates, eligible ones first sorted by composite score
    descending, then ineligible ones (order preserved) with failure reasons."""

    results: list[CorridorResult] = []
    for c in candidates:
        failed = _evaluate_gates(c)
        scores = _sub_scores(c)
        eligible = len(failed) == 0
        composite = round(sum(scores.values()) / len(scores), 4) if eligible else None
        results.append(
            CorridorResult(
                name=c.name,
                eligible=eligible,
                failed_gates=failed,
                sub_scores=scores,
                composite_score=composite,
            )
        )

    eligible_results = sorted(
        (r for r in results if r.eligible), key=lambda r: r.composite_score, reverse=True
    )
    ineligible_results = [r for r in results if not r.eligible]
    return eligible_results + ineligible_results
