import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from desk_verifier import SemanticMark, SemanticReview, check_fact_source, check_line_source, quoted_line_matches, semantic_lookup, verify


class VerifierTest(unittest.TestCase):
    def test_investment_insight_number_is_not_skipped_with_thesis(self):
        class Model:
            def generate_content(self, **kwargs):
                return SimpleNamespace(parsed=SemanticReview(marks=[SemanticMark(line=4, value="5%", supported=True, reason="Matches")]), text=None)
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            report = "Filings: sample\n## Investment Recommendation\n**Hold** — Thesis.\nInsight: Margin rose 5%. — 10-K line 1: Margin rose 5%.\n"
            (folder / "equity_research_report.md").write_text(report, encoding="utf-8")
            (folder / "facts.json").write_text('{}', encoding="utf-8")
            for form in ("10-K", "10-Q", "8-K", "EX-99.1"):
                (folder / f"TEST_{form}_id.txt").write_text("Margin rose 5%.\n", encoding="utf-8")
            verify(folder, folder, SimpleNamespace(models=Model()), "fake")
            marks = json.loads((folder / "verifier_output.json").read_text(encoding="utf-8"))
            self.assertTrue(any(mark["report_line"] == 4 and mark["number"] == "5%" for mark in marks))
            self.assertTrue(any(line.startswith("Insight:") for line in (folder / "verified_report.md").read_text(encoding="utf-8").splitlines()))

    def test_checks_qualitative_quotes_against_cited_line(self):
        filing = {"10-K": "Heading\nThe company sells products.\n"}
        self.assertTrue(quoted_line_matches("- Claim — 10-K line 2: The company sells products.", filing))
        self.assertFalse(quoted_line_matches("- Claim — 10-K line 1: The company sells products.", filing))

    def test_semantic_lookup_accepts_units_but_not_extra_numbers(self):
        marks = [SemanticMark(line=4, value="331,839,000,000 USD", supported=True, reason="Matched"), SemanticMark(line=5, value="10 USD and 11 USD", supported=True, reason="Ambiguous")]
        self.assertTrue(semantic_lookup(marks, 4, "331839000000").supported)
        self.assertIsNone(semantic_lookup(marks, 5, "10"))
        self.assertIsNone(semantic_lookup(marks, 4, "331839000000%"))
        conflict = marks + [SemanticMark(line=4, value="331839000000 USD", supported=False, reason="Conflict")]
        self.assertFalse(semantic_lookup(conflict, 4, "331839000000").supported)

    def test_exact_fact_and_wrong_value(self):
        facts = {"concepts": {"revenue": {"tag": "us-gaap:Revenue", "unit": "USD", "current": {"val": 1200, "end": "2025-12-31", "filed": "2026-02-01"}, "prior": None}}}
        base = "- revenue: {} USD; tag us-gaap:Revenue; period end 2025-12-31; filed 2026-02-01."
        self.assertEqual(check_fact_source("1200", base.format("1200"), facts)[0], "candidate")
        self.assertEqual(check_fact_source("1100", base.format("1100"), facts)[0], "wrong")

    def test_line_format_and_wrong_number(self):
        filings = {"10-K": "Sales   were 1,200 USD.\n"}
        line = "- Sales were 1,200 USD. — 10-K line 1: Sales were 1,200 USD."
        self.assertEqual(check_line_source("1,200", line, filings)[0], "candidate")
        self.assertEqual(check_line_source("99", line, filings)[0], "wrong")

    def test_model_semantics_can_reject_and_does_not_overwrite_report(self):
        class Model:
            def generate_content(self, **kwargs):
                return SimpleNamespace(parsed=SemanticReview(marks=[SemanticMark(line=3, value="1,200", supported=False, reason="Wrong period")]), text=None)
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            out = run / "check"
            out.mkdir()
            report = "Filings: sample\n## Overview\n- Sales were 1,200 USD. — 10-K line 1: Sales were 1,200 USD.\n"
            (run / "equity_research_report.md").write_text(report, encoding="utf-8")
            (run / "facts.json").write_text(json.dumps({"concepts": {}}), encoding="utf-8")
            for form in ("10-K", "10-Q", "8-K", "EX-99.1"):
                (run / f"TEST_{form}_id.txt").write_text("Sales were 1,200 USD.\n", encoding="utf-8")
            path = verify(run, out, SimpleNamespace(models=Model()), "fake")
            self.assertEqual((run / "equity_research_report.md").read_text(encoding="utf-8"), report)
            verified = path.read_text(encoding="utf-8")
            self.assertTrue(verified.startswith("Filings: sample\n"))
            self.assertIn("unsupported", verified)
            self.assertIn("Unsupported numeric claim removed", verified)


if __name__ == "__main__":
    unittest.main()
