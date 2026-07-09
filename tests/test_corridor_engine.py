"""
Ground-truth check for Milestone 1: on the Pune seed data, the known-good
corridors (Wakad, Hinjewadi, Kharadi) must be exactly the top 3 ranked
corridors, and the known-weak corridors must fail the gates. See CLAUDE.md
kickoff brief for the ground truth claim.

Updated 2026-07-05: the corridor list was replaced with the user's 10-name
list (DECISIONS.md); the earlier Koregaon Park/Wagholi/Katraj entries (used
only to demonstrate gate failure) were dropped entirely. Ambegaon and Undri
are real peripheral/budget corridors that also happen to fail the gates,
so they now serve as the known-weak examples instead.
"""

from config.cities.pune import PUNE
from scoring.corridor import rank_corridors


def test_known_good_corridors_rank_top_three():
    results = rank_corridors(PUNE.corridor_candidates)
    eligible = [r for r in results if r.eligible]
    top_three_names = {r.name for r in eligible[:3]}
    assert top_three_names == {"Wakad", "Hinjewadi", "Kharadi"}


def test_known_weak_corridors_are_ineligible():
    results = rank_corridors(PUNE.corridor_candidates)
    ineligible_names = {r.name for r in results if not r.eligible}
    assert {"Ambegaon", "Undri"}.issubset(ineligible_names)


def test_composite_scores_are_descending_for_eligible():
    results = rank_corridors(PUNE.corridor_candidates)
    eligible_scores = [r.composite_score for r in results if r.eligible]
    assert eligible_scores == sorted(eligible_scores, reverse=True)


if __name__ == "__main__":
    test_known_good_corridors_rank_top_three()
    test_known_weak_corridors_are_ineligible()
    test_composite_scores_are_descending_for_eligible()
    print("All corridor engine tests passed.")
