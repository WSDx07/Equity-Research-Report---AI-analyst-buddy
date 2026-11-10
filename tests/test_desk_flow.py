import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from desk_flow import EquityDeskFlow, purdue_client, ResearchWithInsight, FinancialWithInsight, AdviceWithInsight, ManagerReview
from equity_desk.equity_research_roles import Advice, Financial, Research, Review, SECTIONS


class FlowTest(unittest.TestCase):
    def test_role_serializes_decimal_exactly_in_saved_and_sent_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            class Models:
                def generate_content(self, **kwargs):
                    self.payload = json.loads(kwargs["contents"])
                    return SimpleNamespace(parsed=Financial(observations=["Evidence available."], gaps=[]), text=None)
            models = Models()
            flow = EquityDeskFlow(client=SimpleNamespace(models=models))
            flow.state.folder = tmp
            flow.model = "test"
            flow.role("financial", "financial_analyst.txt", "Analyze", {"provider_value": Decimal("0.10000000000000000001")}, "Observations", Financial)
            saved = json.loads((Path(tmp) / "financial_1_input.json").read_text(encoding="utf-8"))
            self.assertEqual(saved, models.payload)
            self.assertEqual(models.payload["context"]["provider_value"], "0.10000000000000000001")

    def test_purdue_configuration_uses_purdue_key_and_model(self):
        client, model = purdue_client({"API_KEY": "other-key", "PURDUE_API_KEY": "purdue-key", "PURDUE_MODEL": "chosen-model"})
        self.assertEqual(model, "chosen-model")
        self.assertEqual(client.current, "Purdue")
        self.assertIsNone(client.google)
        self.assertEqual(client.purdue_key, "purdue-key")
        self.assertEqual(client.purdue_model, "chosen-model")
        with self.assertRaisesRegex(ValueError, "PURDUE_API_KEY"):
            purdue_client({"API_KEY": "other-key"})

    def test_verify_only_uses_purdue_client(self):
        import sys
        from desk_flow import main
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "verified_report.md"
            settings = {"PURDUE_API_KEY": "purdue-key", "PURDUE_MODEL": "chosen-model"}
            with patch.object(sys, "argv", ["desk_flow.py", "--verify-only", tmp]), patch("desk_flow.dotenv_values", return_value=settings), patch("desk_flow.verify", return_value=output) as run:
                main()
            args = run.call_args.args
            self.assertEqual(args[2].current, "Purdue")
            self.assertEqual(args[3], "chosen-model")

    def test_fixed_sequence_and_single_revision(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            calls = []
            class Desk:
                def __init__(self, *args):
                    self.step = 1
                    self.ticker = "TEST"
                    self.filing_text = {"10-K": "Statement.", "EX-99.1": "City, January 1, 2026 - Issuer announced earnings.\nRelease."}
                    self.downloads = {"EX-99.1": "https://example.test"}
                def folder(self): return folder
                def run(self):
                    calls.append(f"step{self.step}")
                    if self.step == 5:
                        (folder / "calculations.json").write_text(json.dumps({"operating_margin_percent": "1", "inputs": {}}))
                def company_info(self): return {"name": "Example", "ticker": "TEST"}
                def fact_data(self): return {"as_of": "2026-01-01", "concepts": {}}
                def choose_filings(self):
                    return {k: {"accessionNumber": "id", "index_url": "https://example.test", "filingDate": "2026-01-01"} for k in ("10-K", "10-Q", "8-K")}
            class Models:
                def generate_content(self, **kwargs):
                    schema = kwargs["config"].response_schema
                    calls.append(schema.__name__)
                    insight = "Insight: Statement. — 10-K line 1: Statement."
                    if schema is ResearchWithInsight:
                        value = ResearchWithInsight(claims=[{"section": s, "claim": "Statement.", "document": "10-K", "line": 1, "quote": "Statement."} for s in (SECTIONS[0], SECTIONS[1], SECTIONS[3])], gaps=[], insight=insight)
                    elif schema is FinancialWithInsight:
                        value = FinancialWithInsight(observations=["Profitability is positive."], gaps=[], insight=insight)
                    elif schema is AdviceWithInsight:
                        value = AdviceWithInsight(recommendation="Hold", thesis="Evidence is mixed.", deciding_metric="operating_margin_percent", risks=[], insight=insight)
                    else:
                        value = ManagerReview(research_issues=["Clarify"], financial_issues=[], advisor_issues=[], overall_issues=[], research_insight={"status":"pass"}, financial_insight={"status":"fail", "reason":"Only repeats the release figure"}, advisor_insight={"status":"pass"})
                    return SimpleNamespace(parsed=value, text=None)
            def fake_verify(*args):
                calls.append("Verifier")
                return folder / "verified_report.md"
            with patch("desk_flow.Desk", Desk), patch("desk_flow.verify", fake_verify), patch("desk_flow.fetch_statements", return_value={"financials": {}}):
                flow = EquityDeskFlow(client=SimpleNamespace(models=Models()))
                flow.kickoff(inputs={"ticker": "TEST"})
            self.assertEqual(calls, [*(f"step{i}" for i in range(1, 8)), "ResearchWithInsight", "FinancialWithInsight", "AdviceWithInsight", "ManagerReview", "ResearchWithInsight", "FinancialWithInsight", "AdviceWithInsight", "Verifier"])
            self.assertTrue((folder / "research_2_input.json").exists())
            self.assertTrue((folder / "equity_research_report.md").exists())
            self.assertEqual(sum(line.startswith("Insight:") for line in (folder / "equity_research_report.md").read_text(encoding="utf-8").splitlines()), 3)
            self.assertEqual(json.loads((folder / "financialdatasets_comparison.json").read_text())["status"], "completed")
            financial_input = json.loads((folder / "financial_1_input.json").read_text())
            self.assertIn("financialdatasets_crosscheck", financial_input["context"])
            self.assertIn("Only repeats the release figure", json.loads((folder / "financial_2_input.json").read_text())["context"]["revision_feedback"][0])
            self.assertIn("financial", json.loads((folder / "insight_review_final.json").read_text()))


if __name__ == "__main__":
    unittest.main()
