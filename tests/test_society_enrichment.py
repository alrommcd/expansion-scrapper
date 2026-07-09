"""
Field-extraction checks for scoring/society_enrichment.py (2026-07-06). No
network needed - _extract_fields operates on raw HTML text directly. Covers
a realistic page (all 4 fields present) and the false-positive guard: a
digit string that looks like a RERA number but has no "RERA" context nearby
must NOT be extracted, same discipline as this project's other regex-based
parsers (e.g. classify/parsing.py's PIN-code-vs-RERA-number confusion caught
in DECISIONS.md 2026-07-06).
"""

from scoring.society_enrichment import _extract_fields

REALISTIC_PAGE = """
<html><head>
<title>Godrej Elements - Premium 2/3 BHK Flats in Hinjewadi, Pune</title>
<meta name="description" content="Godrej Elements offers 450 units of premium 2 and 3 BHK apartments in Hinjewadi, Pune. RERA registered project P52100012345. Ready to move possession available now.">
</head><body>
<p>450 units across 3 towers, possession by December 2024.</p>
</body></html>
"""

NO_CONTEXT_PAGE = "<html><body><p>Tracking ID: AB1234567890, contact us for pricing.</p></body></html>"


def test_extracts_all_fields_from_a_realistic_page():
    fields = _extract_fields(REALISTIC_PAGE)
    assert fields["unit_count"] == "450"
    assert fields["rera_number"] == "P52100012345"
    assert fields["possession_status"] is not None
    assert "Godrej Elements" in fields["project_description"]


def test_does_not_false_positive_a_rera_number_without_context():
    fields = _extract_fields(NO_CONTEXT_PAGE)
    assert fields["rera_number"] is None
    assert fields["unit_count"] is None
    assert fields["possession_status"] is None


if __name__ == "__main__":
    test_extracts_all_fields_from_a_realistic_page()
    test_does_not_false_positive_a_rera_number_without_context()
    print("All society_enrichment tests passed.")
