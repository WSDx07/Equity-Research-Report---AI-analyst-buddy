"""Fixed-order CrewAI Flow for the existing equity research data desk."""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import re
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Literal

from crewai.flow import Flow, listen, start
from dotenv import dotenv_values
from google.genai import types
from pydantic import BaseModel, Field

from equity_research_data_desk import Desk
from equity_desk.equity_research_roles import Advice, Financial, ProviderRouter, Research, Review, SECTIONS, numbered, research_errors
from equity_desk.desk_verifier import verify
from equity_desk.financialdatasets_check import compare, fetch_statements
from equity_desk.filing_excerpts import numbered_excerpt
from equity_desk.insight_checks import insight_errors, release_first_paragraph
from equity_desk.report_metrics import metrics, render_metric

ROOT = Path(__file__).resolve().parent

INSIGHT_OUTPUT = (' End with an insight field containing exactly one line: '
                  '"Insight: <one supported claim> — <10-K, 10-Q, 8-K or EX-99.1> line <number>: <exact quote>". '
                  'The claim must add more than a figure repeated from the release first paragraph. '
                  'If no evidence supports such a claim, use an empty insight field and explain the gap.')

class ResearchWithInsight(Research):
    insight: str = ""

class FinancialWithInsight(Financial):
    insight: str = ""

class AdviceWithInsight(Advice):
    insight: str = ""

class InsightDecision(BaseModel):
    status: Literal["pass", "fail", "unassessed"] = "unassessed"
    reason: str = ""

class ManagerReview(Review):
    research_insight: InsightDecision = Field(default_factory=InsightDecision)
    financial_insight: InsightDecision = Field(default_factory=InsightDecision)
    advisor_insight: InsightDecision = Field(default_factory=InsightDecision)


def purdue_client(settings):
    key = (settings.get("PURDUE_API_KEY") or "").strip()
    if not key:
        raise ValueError("PURDUE_API_KEY is missing or empty in .env")
    model = (settings.get("PURDUE_MODEL") or "").strip() or "gpt-oss:120b"
    return ProviderRouter(None, key, model), model


def json_decimal(value):
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def save_json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=json_decimal) + "\n", encoding="utf-8")


def financial_insight_sources(text: str, document: str = '10-K') -> list[dict]:
    """Give analysts short, exact statement lines with their original numbers."""
    matches = []
    for index, line in enumerate(text.splitlines(), 1):
        if len(line) <= 500 and re.search(r'\b(?:net sales|total revenue|operating income|net income|cash.*operating activities)\b', line, re.I) and re.search(r'\d', line):
            matches.append({'document': document, 'line': index, 'quote': line})
    return matches[:20]


class DeskState(BaseModel):
    ticker: str = ""
    peers: list[str] = Field(default_factory=list)
    price: str | None = None
    folder: str = ""
    research: dict = Field(default_factory=dict)
    financial: dict = Field(default_factory=dict)
    advice: dict = Field(default_factory=dict)
    review: dict = Field(default_factory=dict)


class EquityDeskFlow(Flow[DeskState]):
    def __init__(self, client=None, **kwargs):
        super().__init__(**kwargs)
        self.client = client
        self.desk = None
        self.contexts = {}
        self.counts = {"research": 0, "financial": 0, "advisor": 0, "manager": 0}

    def role(self, name, role_file, task, context, expected, schema):
        self.counts[name] += 1
        if self.counts[name] > (1 if name == "manager" else 2):
            raise RuntimeError(f"Role call limit exceeded: {name}")
        print({"research": "Research Analyst", "financial": "Financial Analyst", "advisor": "Investment Advisor", "manager": "Strategy Manager"}[name], flush=True)
        folder = Path(self.state.folder)
        payload = {"task": task, "context": context, "expected_output": expected}
        prefix = f"{name}_{self.counts[name]}"
        save_json(folder / f"{prefix}_input.json", payload)
        instructions = (ROOT / "roles" / role_file).read_text(encoding="utf-8")
        if name == 'research' and self.contexts.get('source_form') == '10-Q':
            instructions = instructions.replace('10-K', '10-Q')
        if name in {"research", "financial", "advisor"}:
            instructions += "\nThe separate required Insight field may contain a sourced number even when other prose must not contain digits."
        response = self.client.models.generate_content(
            model=self.model, contents=json.dumps(payload, ensure_ascii=False, default=json_decimal),
            config=types.GenerateContentConfig(system_instruction=instructions, response_mime_type="application/json", response_schema=schema),
        )
        output = schema.model_validate(response.parsed) if response.parsed is not None else schema.model_validate_json(response.text)
        save_json(folder / f"{prefix}_output.json", output.model_dump())
        return output.model_dump()

    @start()
    def steps(self):
        print("Steps", flush=True)
        self.desk = Desk(self.state.ticker, self.state.peers, Decimal(self.state.price) if self.state.price else None, 1)
        for index in range(1, 8):
            print(f"Step {index} started", flush=True)
            self.desk.step = index
            capture = io.StringIO()
            with contextlib.redirect_stdout(capture):
                self.desk.run()
            print(capture.getvalue(), end="", flush=True)
            folder = self.desk.folder()
            self.state.folder = str(folder)
            save_json(folder / f"step_{index}_input.json", {"ticker": self.state.ticker, "peers": self.state.peers, "price": self.state.price})
            save_json(folder / f"step_{index}_output.json", {"output": capture.getvalue()})
        settings = dotenv_values(ROOT / ".env")
        if self.client is None:
            self.client, self.model = purdue_client(settings)
        else:
            self.model = (settings.get("PURDUE_MODEL") or "").strip() or "gpt-oss:120b"
        desk = self.desk
        folder = desk.folder()
        filings = desk.choose_filings()
        facts = desk.fact_data()
        source_form = '10-K' if '10-K' in filings else '10-Q'
        self.contexts['source_form'] = source_form
        first = release_first_paragraph(desk.filing_text["EX-99.1"])
        self.contexts["first_paragraph"] = first
        self.contexts["research"] = {"analysis_date": facts["as_of"], source_form: numbered_excerpt(desk.filing_text[source_form], 100000), "EX-99.1": numbered_excerpt(desk.filing_text["EX-99.1"], 30000), "filing_metadata": {k: {"accession": filings[k]["accessionNumber"], "url": filings[k]["index_url"], "filed": filings[k]["filingDate"]} for k in (source_form, "8-K")}, "source_limit": "No annual 10-K is available; the 10-Q covers interim periods." if source_form == '10-Q' else None}
        self.contexts["financial"] = {"facts": facts, "calculator_results": json.loads((folder / "calculations.json").read_text(encoding="utf-8")), "quarter_release": {"source": desk.downloads.get("EX-99.1"), "text_with_line_numbers": numbered_excerpt(desk.filing_text["EX-99.1"], 30000)}, "peer_facts": json.loads((folder / "peer_facts.json").read_text(encoding="utf-8")) if (folder / "peer_facts.json").exists() else {}}
        print("Financial Datasets cross-check", flush=True)
        save_json(folder / "financialdatasets_input.json", {"ticker": desk.ticker, "period": "annual", "analysis_date": facts["as_of"]})
        try:
            response = fetch_statements(desk.ticker, settings.get("FINDATA_API_KEY") or "", facts["as_of"])
            save_json(folder / "financialdatasets_response.json", response)
            comparison = compare(facts, response)
            comparison["status"] = "completed"
            print("Financial Datasets cross-check completed; see financialdatasets_comparison.json.", flush=True)
        except (ValueError, RuntimeError) as exc:
            comparison = {"status": "unavailable", "reason": str(exc), "analysis_date": facts["as_of"], "rows": []}
            print(f"Financial Datasets cross-check unavailable: {exc}", flush=True)
        save_json(folder / "financialdatasets_comparison.json", comparison)
        self.contexts["financial"]["financialdatasets_crosscheck"] = comparison

    def do_research(self, feedback=None):
        context = dict(self.contexts["research"])
        context["release_first_paragraph"] = self.contexts["first_paragraph"]
        if feedback:
            context["revision_feedback"] = feedback
        self.state.research = self.role("research", "research_analyst.txt", "Assess business model, competitive position, catalysts and developments.", context, "Return sourced claims with exact quotes and line numbers, and gaps." + INSIGHT_OUTPUT, ResearchWithInsight)

    def do_financial(self, feedback=None):
        context = dict(self.contexts["financial"])
        form = self.contexts['source_form']
        context["filing_10k" if form == '10-K' else "filing_10q"] = self.contexts["research"][form]
        context["insight_source_candidates"] = financial_insight_sources(self.desk.filing_text[form], form)
        context["release_first_paragraph"] = self.contexts["first_paragraph"]
        if feedback:
            context["revision_feedback"] = feedback
        self.state.financial = self.role("financial", "financial_analyst.txt", "Evaluate financial evidence and valuation limits.", context, "Return qualitative observations without digits and gaps; do not perform arithmetic. The Insight may contain a sourced number." + INSIGHT_OUTPUT, FinancialWithInsight)

    def do_advisor(self, feedback=None):
        form = self.contexts['source_form']
        context = {"research": self.state.research, "financial": {**self.state.financial, "calculator_results": self.contexts["financial"]["calculator_results"]}, ("filing_10k" if form == '10-K' else "filing_10q"): self.contexts["research"][form], "release_first_paragraph": self.contexts["first_paragraph"]}
        if feedback:
            context["revision_feedback"] = feedback
        self.state.advice = self.role("advisor", "investment_advisor.txt", "Synthesize the specialist evidence into an investment view.", context, "Return a recommendation, qualitative thesis, one calculator key and risks. The Insight may contain a sourced number." + INSIGHT_OUTPUT, AdviceWithInsight)

    @listen(steps)
    def research_analyst(self):
        self.do_research()

    @listen(research_analyst)
    def financial_analyst(self):
        self.do_financial()

    @listen(financial_analyst)
    def investment_advisor(self):
        self.do_advisor()

    @listen(investment_advisor)
    def strategy_manager(self):
        form = self.contexts['source_form']
        automatic = {"research_issues": research_errors(Research.model_validate(self.state.research), {form: self.desk.filing_text[form], "EX-99.1": self.desk.filing_text["EX-99.1"]}), "financial_issues": [], "advisor_issues": []}
        for name in ("research", "financial", "advisor"):
            output = getattr(self.state, "advice" if name == "advisor" else name)
            automatic[f"{name}_issues"].extend(insight_errors(output.get("insight", ""), self.desk.filing_text, self.contexts["first_paragraph"]))
        if not self.state.financial["observations"]:
            automatic["financial_issues"].append("Valuation Insights has no financial observations.")
        if any(re.search(r"\d", s) for s in self.state.financial["observations"]):
            automatic["financial_issues"].append("Financial observations contain digits.")
        if not self.state.advice["thesis"].strip():
            automatic["advisor_issues"].append("The investment thesis is missing.")
        metric = self.state.advice.get("deciding_metric")
        calculations = self.contexts["financial"]["calculator_results"]
        if not metric or metric == "inputs" or calculations.get(metric) is None:
            automatic["advisor_issues"].append("Select one available calculator result as the deciding metric and explain why it drives the recommendation.")
        if any(re.search(r"\d", s) for s in [self.state.advice["thesis"], *self.state.advice["risks"]]):
            automatic["advisor_issues"].append("Advisor prose contains digits.")
        self.state.review = self.role("manager", "strategy_manager.txt", "Check all five sections for completeness and consistency; assign issues to each specialist. For each role independently inspect its Insight and the supplied release first paragraph. Fail if the Insight is missing or its claim only restates a figure from that paragraph; consider metric, period, and meaning, not just matching numbers. Use unassessed if the paragraph or evidence is insufficient.", {"sections": SECTIONS, "research": self.state.research, "financial": self.state.financial, "advisor": self.state.advice, "release_first_paragraph": self.contexts["first_paragraph"], "facts": self.contexts["financial"]["facts"], "calculator_results": self.contexts["financial"]["calculator_results"], "financialdatasets_crosscheck": self.contexts["financial"]["financialdatasets_crosscheck"], "automatic_checks": automatic}, "Return issue lists by role and unresolved overall issues. Set research_insight, financial_insight and advisor_insight to objects with status pass, fail or unassessed and a reason.", ManagerReview)
        for key, issues in automatic.items():
            self.state.review[key].extend(issues)
        for name in ("research", "financial", "advisor"):
            verdict = self.state.review[f"{name}_insight"]
            if verdict["status"] != "pass":
                self.state.review[f"{name}_issues"].append("Insight review " + verdict["status"] + ": " + (verdict["reason"] or "No explanation supplied."))
        review = self.state.review
        if review["research_issues"]:
            self.do_research(review["research_issues"])
        if review["financial_issues"]:
            self.do_financial(review["financial_issues"])
        if review["advisor_issues"] or review["research_issues"] or review["financial_issues"]:
            self.do_advisor(review["advisor_issues"] or ["Upstream evidence changed; reassess the recommendation."])
        self.state.review["post_revision_insight_issues"] = {}
        for name in ("research", "financial", "advisor"):
            output = getattr(self.state, "advice" if name == "advisor" else name)
            remaining = insight_errors(output.get("insight", ""), self.desk.filing_text, self.contexts["first_paragraph"])
            if self.counts[name] > 1:
                remaining.append("Revised Insight has not received a second Manager semantic review.")
            if remaining:
                self.state.review["post_revision_insight_issues"][name] = remaining
        save_json(Path(self.state.folder) / "insight_review_final.json", self.state.review["post_revision_insight_issues"])
        self.compile_report()

    def compile_report(self):
        desk, folder = self.desk, Path(self.state.folder)
        filings = desk.choose_filings()
        facts = desk.fact_data()
        forms = ('10-K' if '10-K' in filings else 'Form 10', '10-Q', '8-K')
        lines = ["Filings: " + "; ".join(f"{k} {filings[k]['accessionNumber']} filed {filings[k]['filingDate']} {filings[k]['index_url']}" for k in forms), f"# {desk.company_info()['name']} ({desk.ticker})", f"Analysis date: {facts['as_of']}", ""]
        if facts.get('limitation'):
            lines.extend([f"Data limitation: {facts['limitation']}", ""])
        for section in SECTIONS:
            lines.extend([f"## {section}", ""])
            claims = [c for c in self.state.research["claims"] if c["section"] == section]
            for claim in claims:
                lines.append(f"- {claim['claim']} — {claim['document']} line {claim['line']}: {claim['quote']}")
            if section in (SECTIONS[0], SECTIONS[1], SECTIONS[3]) and not claims:
                lines.append("Evidence unavailable for this section.")
            if section == SECTIONS[1]:
                lines.append(self.state.research.get("insight") or "Insight: unavailable; no supported research insight was supplied.")
            if section == SECTIONS[2]:
                lines.extend(self.state.financial["observations"] or ["Evidence unavailable for this section."])
                rows = metrics(facts, self.contexts['financial'].get('peer_facts', {}), self.state.price)
                lines.extend(['', '| Measure | Result | Inputs, source and calculation |', '|---|---:|---|'])
                lines.extend(render_metric(key, row, self.state.price) for key, row in rows.items())
                lines.extend(['', 'Peer periods may differ; compare their fiscal year ends and business models. The share price is a user input without an independently verified date or source.', ''])
                step6_path = folder / 'step_6_output.json'
                if step6_path.exists():
                    step6 = json.loads(step6_path.read_text(encoding='utf-8')).get('output', '')
                    release_lines = desk.filing_text['EX-99.1'].splitlines()
                    for match in re.finditer(r'^\s*(?:Quarter revenue|Diluted EPS) \(saved release line (\d+)\): (.+)$', step6, re.M):
                        line_number = int(match.group(1))
                        if 1 <= line_number <= len(release_lines) and match.group(2) in release_lines[line_number - 1]:
                            lines.append(f"- {match.group(2)} — EX-99.1 line {line_number}: {release_lines[line_number - 1]}")
                crosscheck = self.contexts["financial"]["financialdatasets_crosscheck"]
                if crosscheck["status"] != "completed":
                    lines.append(f"Financial Datasets cross-check unavailable: {crosscheck['reason']}")
                else:
                    differences = sorted({row['concept'] for row in crosscheck['rows'] if row['status'] == 'difference'})
                    unavailable = sorted({row['concept'] for row in crosscheck['rows'] if row['status'] == 'not_comparable'})
                    lines.append("Financial Datasets cross-check: detailed source values, periods and differences are saved in financialdatasets_comparison.json. Both datasets use SEC filings.")
                    if differences:
                        lines.append("Differences require review: " + ", ".join(differences) + ".")
                    if unavailable:
                        lines.append("Not comparable or unavailable: " + ", ".join(unavailable) + ".")
                lines.append(self.state.financial.get("insight") or "Insight: unavailable; no supported financial insight was supplied.")
            if section == SECTIONS[4]:
                lines.append(f"**{self.state.advice['recommendation']}** — {self.state.advice['thesis']}")
                chosen = self.state.advice.get('deciding_metric')
                rows = metrics(facts, self.contexts['financial'].get('peer_facts', {}), self.state.price)
                if chosen in rows:
                    lines.extend(['', 'Deciding metric selected by the advisor:', '', '| Measure | Result | Inputs, source and calculation |', '|---|---:|---|', render_metric(chosen, rows[chosen], self.state.price), ''])
                else:
                    lines.append('Deciding metric unavailable; the recommendation cannot be assessed against its selected calculation.')
                lines.extend(f"- Risk: {risk}" for risk in self.state.advice["risks"])
                lines.append(self.state.advice.get("insight") or "Insight: unavailable; no supported investment insight was supplied.")
            lines.append("")
        gaps = list(dict.fromkeys(self.state.research["gaps"] + self.state.financial["gaps"]))
        lines.extend(["## Evidence gaps", ""] + [f"- {gap}" for gap in gaps])
        lines.extend(["", "## Audit appendix", ""] + [f"- {gap}" for gap in dict.fromkeys(self.state.review["overall_issues"])])
        for role, issues in self.state.review.get("post_revision_insight_issues", {}).items():
            lines.extend(f"- {role} Insight: {issue}" for issue in issues)
        (folder / "equity_research_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    @listen(strategy_manager)
    def verifier(self):
        folder = Path(self.state.folder)
        return str(verify(folder, folder, self.client, self.model))


def main():
    parser = argparse.ArgumentParser(description="Run the fixed equity research desk flow.")
    parser.add_argument("ticker", nargs="?", help="SEC ticker")
    parser.add_argument("--peers", nargs="*", default=[])
    parser.add_argument("--price", type=Decimal)
    parser.add_argument("--verify-only", type=Path, help="Verify an existing saved run")
    args = parser.parse_args()
    if args.verify_only:
        if args.ticker or args.peers or args.price is not None:
            parser.error("--verify-only cannot be combined with a ticker, --peers, or --price")
        settings = dotenv_values(ROOT / ".env")
        client, model = purdue_client(settings)
        run = args.verify_only.resolve()
        result_dir = run / ("verification_" + datetime.now().astimezone().strftime("%Y-%m-%d_%H-%M-%S_%f_%z"))
        result_dir.mkdir(exist_ok=False)
        path = verify(run, result_dir, client, model)
    else:
        if not args.ticker:
            parser.error("ticker is required unless --verify-only is used")
        flow = EquityDeskFlow()
        path = flow.kickoff(inputs={"ticker": args.ticker.upper(), "peers": args.peers, "price": str(args.price) if args.price is not None else None})
    print(f"Verified report: {path}", flush=True)


if __name__ == "__main__":
    main()

