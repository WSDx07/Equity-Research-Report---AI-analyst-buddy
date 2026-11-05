import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from desk_verifier import SemanticMark, SemanticReview, annual_revenue_growth, check_fact_source, check_line_source, diluted_eps_line, quoted_line_matches, semantic_lookup, structured_semantic_lookup, verify
from structured_claims import check_claim, formula_value
from decimal import Decimal
from report_metrics import metrics, render_metric


class VerifierTest(unittest.TestCase):
    def test_metric_rows_recompute_and_label_unsourced_price(self):
        class Model:
            def generate_content(self, **kwargs):
                return SimpleNamespace(parsed=SemanticReview(marks=[
                    SemanticMark(line=5, value='20%', supported=True, reason='matching periods'),
                    SemanticMark(line=6, value='10', supported=True, reason='matching EPS'),
                ]), text=None)
        def fact(value, tag, unit='USD'):
            return {'tag': tag, 'unit': unit, 'current': {'val':value, 'start':'2025-01-01', 'end':'2025-12-31', 'accn':'id', 'filed':'2026-01-01'}}
        facts = {'concepts': {'operating_income':fact(20, 'op'), 'total_revenue':fact(100, 'rev'), 'diluted_eps':fact(5, 'eps', 'USD/shares')}}
        rows = metrics(facts, {}, '50')
        shifted = json.loads(json.dumps(facts))
        shifted['concepts']['operating_income']['current']['end'] = '2024-12-31'
        self.assertNotIn('operating_margin_percent', metrics(shifted, {}, '50'))
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder/'facts.json').write_text(json.dumps(facts), encoding='utf-8')
            for form in ('10-K','10-Q','8-K','EX-99.1'):
                (folder/f'TEST_{form}_id.txt').write_text('Test.\n',encoding='utf-8')
            report = 'Filings: test\n## Valuation Insights\n| Measure | Result | Source |\n|---|---|---|\n' + render_metric('operating_margin_percent',rows['operating_margin_percent']) + '\n' + render_metric('price_to_earnings',rows['price_to_earnings'],'50') + '\n'
            (folder/'equity_research_report.md').write_text(report,encoding='utf-8')
            output = verify(folder,folder,SimpleNamespace(models=Model()),'fake').read_text(encoding='utf-8')
            marks = json.loads((folder/'verifier_output.json').read_text(encoding='utf-8'))
            self.assertEqual([x['mark'] for x in marks], ['correct','unsupported'])
            self.assertIn('Price to earnings (unverified)', output)
            (folder/'equity_research_report.md').write_text(report.replace('20.00 %','21.00 %'),encoding='utf-8')
            verify(folder,folder,SimpleNamespace(models=Model()),'fake')
            marks = json.loads((folder/'verifier_output.json').read_text(encoding='utf-8'))
            self.assertEqual(marks[0]['mark'], 'unsupported')

    def test_wrong_source_line_is_not_presented_as_correction(self):
        class Model:
            def generate_content(self, **kwargs):
                return SimpleNamespace(parsed=SemanticReview(marks=[]), text=None)
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            report = "Filings: sample\n## Overview\n- Revenue was 5. — 10-K line 1: Revenue was 5.\n"
            (folder / "equity_research_report.md").write_text(report, encoding="utf-8")
            (folder / "facts.json").write_text('{}', encoding="utf-8")
            for form in ("10-K", "10-Q", "8-K", "EX-99.1"):
                (folder / f"TEST_{form}_id.txt").write_text("Unresolved staff comments.\n", encoding="utf-8")
            verified = verify(folder, folder, SimpleNamespace(models=Model()), "fake").read_text(encoding="utf-8")
            self.assertNotIn("Filing text, 10-K line 1: Unresolved staff comments", verified)
            self.assertIn("wrong", verified)

    def test_repeated_invalid_quotes_have_one_notice_and_separate_marks(self):
        class Model:
            def generate_content(self, **kwargs):
                return SimpleNamespace(parsed=SemanticReview(marks=[]), text=None)
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            report = ("Filings: sample\n## Overview\n"
                      "- First claim — 10-K line 1: invented.\n"
                      "- Second claim — 10-K line 1: also invented.\n")
            (folder / "equity_research_report.md").write_text(report, encoding="utf-8")
            (folder / "facts.json").write_text('{}', encoding="utf-8")
            for form in ("10-K", "10-Q", "8-K", "EX-99.1"):
                (folder / f"TEST_{form}_id.txt").write_text("Actual text.\n", encoding="utf-8")
            result = verify(folder, folder, SimpleNamespace(models=Model()), "fake").read_text(encoding="utf-8")
            marks = json.loads((folder / "verifier_output.json").read_text(encoding="utf-8"))
            self.assertEqual(result.count("Unsupported claim removed;"), 1)
            self.assertEqual([m["report_line"] for m in marks], [3, 4])

    def test_omitted_structured_mark_gets_one_retry_without_guessing(self):
        class Model:
            calls = 0
            def generate_content(self, **kwargs):
                self.calls += 1
                marks = [] if self.calls == 1 else [SemanticMark(line=3, value="120 USD million", supported=True, reason="Period and definition match")]
                return SimpleNamespace(parsed=SemanticReview(marks=marks), text=None)
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            fact = {"tag":"us-gaap:Revenue", "unit":"USD", "current":{"val":120000000,"end":"2025-12-31"}}
            (folder / "facts.json").write_text(json.dumps({"concepts":{"total_revenue":fact}}), encoding="utf-8")
            filing = "(amounts in millions) December 31, 2025 | December 31, 2024\nTotal revenue | 120 | 100\n"
            for form in ("10-K", "10-Q", "8-K", "EX-99.1"):
                (folder / f"TEST_{form}_id.txt").write_text(filing, encoding="utf-8")
            claim = {"id":"revenue", "label":"Revenue", "reported":"120", "unit":"USD million", "definition":"annual total revenue", "formula":"a", "inputs":{"a":{"value":"120","unit":"USD million","document":"10-K","line":2,"column":1,"period_end":"2025-12-31","concept":"total_revenue","tag":"us-gaap:Revenue","fact_period":"current"}}}
            line = "- Revenue: 120 USD million — 10-K line 2: Total revenue | 120 | 100 <!-- FINANCIAL_CLAIM " + json.dumps(claim) + " -->"
            (folder / "equity_research_report.md").write_text("Filings: sample\n## Valuation Insights\n" + line + "\n", encoding="utf-8")
            model = Model()
            verify(folder, folder, SimpleNamespace(models=model), "fake")
            marks = json.loads((folder / "verifier_output.json").read_text(encoding="utf-8"))
            self.assertEqual(model.calls, 2)
            self.assertEqual(marks[0]["mark"], "correct")
            self.assertTrue((folder / "verifier_retry_output.json").exists())

    def test_eps_correction_locates_only_per_share_row(self):
        filing = {"10-K": "NET INCOME PER COMMON SHARE:\nBasic | 4.30 | 3.10\nDiluted | 4.20 | 3.00\nShares used\nDiluted | 123 | 120\n"}
        self.assertEqual(diluted_eps_line(filing, {"val": "4.20"}), (3, "Diluted | 4.20 | 3.00"))
        self.assertIsNone(diluted_eps_line(filing, {"val": "4.25"}))

    def test_growth_recomputes_only_with_matching_filing_and_fact_inputs(self):
        facts = {"concepts": {"total_revenue": {"unit": "USD", "current": {"val": 120000000, "end": "2025-12-31"}, "prior": {"val": 100000000, "end": "2024-12-31"}}}}
        filing = {"10-K": "Total revenue | 120 | | 100"}
        line = "- Annual total revenue growth was 24.00%, calculated as (120 - 100) / 100 x 100. — 10-K line 1: Total revenue | 120 | | 100"
        result = annual_revenue_growth(line, facts, filing)
        self.assertEqual(result["status"], "wrong")
        self.assertIn("20.00%", result["formula"])
        self.assertEqual(annual_revenue_growth(line.replace("/ 100", "/ 110"), facts, filing)["status"], "unsupported")

    def test_structured_claim_checks_facts_period_columns_and_arithmetic(self):
        filing = {"10-K": "(amounts in millions) Year ended December 31, 2025 | December 31, 2024\nTotal revenue | 120 | | 100"}
        facts = {"concepts": {"total_revenue": {"tag":"us-gaap:Revenue", "unit":"USD", "current":{"val":120000000,"end":"2025-12-31"}, "prior":{"val":100000000,"end":"2024-12-31"}}}}
        base = {"document":"10-K", "line":2, "unit":"USD million", "concept":"total_revenue", "tag":"us-gaap:Revenue"}
        claim = {"id":"growth", "label":"Revenue growth", "reported":"20.00", "unit":"%", "definition":"change in total revenue", "formula":"(a-b)/b*100", "inputs":{"a":base | {"value":"120","column":1,"fact_period":"current","period_end":"2025-12-31"}, "b":base | {"value":"100","column":2,"fact_period":"prior","period_end":"2024-12-31"}}}
        self.assertEqual(check_claim(claim, facts, filing)["status"], "candidate")
        self.assertEqual(check_claim(claim | {"reported":"24.00"}, facts, filing)["status"], "wrong")
        broken = claim | {"inputs": {**claim["inputs"], "b":claim["inputs"]["b"] | {"column":1}}}
        self.assertEqual(check_claim(broken, facts, filing)["status"], "unsupported")
        wrong_period = claim | {"inputs": {**claim["inputs"], "a":claim["inputs"]["a"] | {"period_end":"2024-12-31"}}}
        self.assertEqual(check_claim(wrong_period, facts, filing)["status"], "unsupported")
        with self.assertRaises(ValueError):
            formula_value('__import__("os")', {"a":Decimal(1)})

    def test_same_end_date_does_not_confuse_quarter_and_full_year(self):
        filing = {"EX-99.1": "(dollars in millions)\n16 Weeks Ended | 52 Weeks Ended\nDecember 31, 2025 | December 31, 2024 | December 31, 2025 | December 31, 2024\nTotal revenue | 10 | 8 | 40 | 30"}
        claim = {"id":"quarter", "label":"Quarter revenue", "reported":"40", "unit":"USD million", "definition":"quarterly revenue", "formula":"a", "inputs":{"a":{"value":"40", "unit":"USD million", "document":"EX-99.1", "line":4, "column":3, "period_end":"2025-12-31", "duration_weeks":16}}}
        self.assertEqual(check_claim(claim, {}, filing)["status"], "unsupported")
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
        percentage = [SemanticMark(line=6, value="10.14", supported=True, reason="Matched")]
        self.assertTrue(structured_semantic_lookup(percentage, 6, "10.14", "%").supported)
        percentage.append(SemanticMark(line=6, value="10.14%", supported=False, reason="Conflict"))
        self.assertFalse(structured_semantic_lookup(percentage, 6, "10.14", "%").supported)
        amounts = [SemanticMark(line=7, value="303154 USD million", supported=True, reason="Matched"), SemanticMark(line=8, value="0.1721 ratio", supported=True, reason="Matched")]
        self.assertTrue(structured_semantic_lookup(amounts, 7, "303154", "USD million").supported)
        self.assertTrue(structured_semantic_lookup(amounts, 8, "0.1721", "ratio").supported)
        self.assertIsNone(structured_semantic_lookup(amounts, 7, "303154", "%"))

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
