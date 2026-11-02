import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import equity_research_roles as roles


class FakeResponses:
    def __init__(self):
        self.messages = []

    def generate_content(self, **kwargs):
        schema = kwargs["config"].response_schema
        context = json.loads(kwargs["contents"])
        self.messages.append((schema.__name__, context))
        if schema is roles.Plan:
            result = roles.Plan(research_task="Research", financial_task="Analyze", advisor_task="Advise")
        elif schema is roles.Research:
            result = roles.Research(claims=[roles.Claim(section=s, claim="Reported claim", document="10-K", line=1, quote="A sourced statement.") for s in (roles.SECTIONS[0], roles.SECTIONS[1], roles.SECTIONS[3])], gaps=[])
        elif schema is roles.Financial:
            result = roles.Financial(observations=["Profitability is positive."], gaps=[])
        elif schema is roles.Advice:
            result = roles.Advice(recommendation="Hold", thesis="The evidence is mixed.", deciding_metric="operating_margin_percent", risks=["Demand may weaken."])
        else:
            result = roles.Review(research_issues=[], financial_issues=[], advisor_issues=[], overall_issues=[])
        return SimpleNamespace(parsed=result, text=None)


class RoleWorkflowTest(unittest.TestCase):
    def test_backup_key_is_used_for_quota_and_stays_active(self):
        from google.genai import errors
        class Models:
            def __init__(self, fail):
                self.fail = fail
                self.calls = 0
            def generate_content(self, **kwargs):
                self.calls += 1
                if self.fail:
                    raise errors.ClientError(429, {"error": {"message": "quota"}})
                return "ok"
        first = Models(True)
        response = SimpleNamespace(raise_for_status=lambda: None, json=lambda: {"choices": [{"message": {"content": '{"research_task":"a","financial_task":"b","advisor_task":"c"}'}}]})
        config = SimpleNamespace(response_schema=roles.Plan, system_instruction="test")
        with patch.object(roles.genai, "Client", return_value=SimpleNamespace(models=first)), patch.object(roles.requests, "post", return_value=response) as post, contextlib.redirect_stdout(io.StringIO()):
            pool = roles.ProviderRouter("first", "second")
            for _ in range(2):
                result = pool.models.generate_content(model="gemini", contents="{}", config=config)
                self.assertEqual(result.parsed.research_task, "a")
        self.assertEqual((first.calls, post.call_count), (1, 2))
        self.assertTrue(all(call.kwargs['headers']['Authorization'] == 'Bearer second' for call in post.call_args_list))

    def test_quote_check_and_isolated_handoffs(self):
        bad = roles.Research(claims=[roles.Claim(section=roles.SECTIONS[0], claim="Bad", document="10-K", line=1, quote="not in text")], gaps=[])
        self.assertTrue(roles.research_errors(bad, {"10-K": "A sourced statement.", "EX-99.1": "release"}))
        unsupported = roles.Claim(section=roles.SECTIONS[0], claim="Revenue was 500", document="10-K", line=1, quote="Revenue increased.")
        self.assertFalse(roles.claim_numbers_supported(unsupported))
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            (folder / "calculations.json").write_text(json.dumps({"operating_margin_percent": "10", "inputs": {}}))
            response = FakeResponses()
            class Desk:
                started = __import__("datetime").datetime(2026, 1, 1)
                ticker = "TEST"
                filing_text = {"10-K": "A sourced statement.", "EX-99.1": "Release line."}
                downloads = {"EX-99.1": "https://example.test/release"}
                def folder(self): return folder
                def choose_filings(self): return {k: {"accessionNumber": "000-01", "index_url": "https://example.test"} for k in ("10-K", "10-Q", "8-K")}
                def company_info(self): return {"name": "Example", "ticker": "TEST"}
                def fact_data(self): return {"as_of": "2026-01-01", "concepts": {}}
                def calculate(self, facts): print("Operating margin = 10 / 100 = 10%")
                def release_lines(self): print("Quarter revenue: release line")
            with patch.object(roles.genai, "Client", return_value=SimpleNamespace(models=response)), patch.object(roles, "dotenv_values", return_value={"API_KEY": "test"}), contextlib.redirect_stdout(io.StringIO()):
                path = roles.run_roles(Desk())
            text = path.read_text(encoding="utf-8")
            self.assertTrue(text.splitlines()[0].startswith("Filings:"))
            self.assertTrue(text.splitlines()[1].startswith("Run time:"))
            self.assertTrue(all("## " + section in text for section in roles.SECTIONS))
            advisor_context = next(message["context"] for name, message in response.messages if name == "Advice")
            self.assertEqual(set(advisor_context), {"research", "financial"})


if __name__ == "__main__":
    unittest.main()
