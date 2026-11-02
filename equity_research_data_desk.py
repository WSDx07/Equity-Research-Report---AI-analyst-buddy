"""Download traceable SEC inputs and calculate annual equity research facts."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlsplit

import requests
from bs4 import BeautifulSoup, NavigableString, Tag
from dotenv import dotenv_values


ROOT = Path(__file__).resolve().parent
RUNS = ROOT / "equity_research_runs"
AS_OF = date.today().isoformat()
ANNUAL_FORMS = {"10-K"}
CONCEPTS = {
    "total_revenue": (["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet"], "USD", True),
    "operating_income": (["OperatingIncomeLoss"], "USD", True),
    "net_income": (["NetIncomeLoss", "ProfitLoss"], "USD", True),
    "diluted_eps": (["EarningsPerShareDiluted"], "USD/shares", True),
    "stockholders_equity": (["StockholdersEquity"], "USD", False),
    "long_term_debt_noncurrent": (["LongTermDebtNoncurrent", "LongTermDebt"], "USD", False),
    "long_term_debt_current": (["LongTermDebtCurrent"], "USD", False),
    "cash_from_operations": (["NetCashProvidedByUsedInOperatingActivities", "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations"], "USD", True),
    "additions_to_property_and_equipment": (["PaymentsToAcquirePropertyPlantAndEquipment"], "USD", True),
}


def say(message: str) -> None:
    print(message, flush=True)


def value(number: Decimal | int | float | None, unit: str = "USD") -> str:
    if number is None:
        return "unavailable"
    amount = Decimal(str(number))
    if unit == "USD":
        return f"USD {amount / Decimal(1_000_000):,.3f} million"
    if unit == "USD/shares":
        return f"USD {amount:,.2f} per share"
    return f"{amount:,.4f}"


def percent(number: Decimal | None) -> str:
    return "unavailable" if number is None else f"{number:,.2f}%"


def safe_div(numerator: Decimal | None, denominator: Decimal | None) -> Decimal | None:
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


def text_from_html(content: bytes) -> str:
    soup = BeautifulSoup(content, "html.parser")
    for tag in soup(["script", "style", "noscript", "ix:header"]):
        tag.decompose()
    pieces: list[str] = []
    blocks = {"p", "div", "section", "article", "li", "tr", "h1", "h2", "h3", "h4", "br"}
    for element in soup.descendants:
        if isinstance(element, NavigableString):
            pieces.append(str(element))
        elif isinstance(element, Tag):
            if element.name in blocks:
                pieces.append("\n")
            elif element.name in {"td", "th"}:
                pieces.append(" | ")
    lines = [re.sub(r"\s+", " ", line).strip(" |") for line in "".join(pieces).splitlines()]
    return "\n".join(line for line in lines if line) + "\n"


def slug(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_")[:70] or "company"


class SecClient:
    def __init__(self) -> None:
        settings = dotenv_values(ROOT / ".env")
        agent = settings.get("SEC_USER_AGENT")
        if not agent or not agent.strip():
            raise ValueError("SEC_USER_AGENT is missing or empty in .env")
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": agent.strip(), "Accept-Encoding": "gzip, deflate"})
        self.last_request = 0.0

    def get(self, url: str) -> bytes:
        # Keep a margin below the SEC limit of 10 requests per second.
        delay = 0.2 - (time.monotonic() - self.last_request)
        if delay > 0:
            time.sleep(delay)
        for attempt in range(3):
            response = self.session.get(url, timeout=45)
            self.last_request = time.monotonic()
            if response.status_code in {429, 500, 502, 503, 504} and attempt < 2:
                time.sleep(2 ** attempt)
                continue
            response.raise_for_status()
            return response.content
        raise RuntimeError(f"Could not download {url}")

    def json(self, url: str) -> dict:
        return json.loads(self.get(url))


class Desk:
    def __init__(self, ticker: str, peers: list[str], price: Decimal | None, step: int | None, price_date: str | None = None, price_source: str | None = None) -> None:
        self.client = SecClient()
        self.ticker = ticker.upper()
        self.peers = [ticker.upper() for group in peers for ticker in re.split(r"[,\s]+", group.strip()) if ticker]
        self.price = price
        self.price_date = price_date
        self.price_source = price_source
        self.step = step
        self.started = datetime.now().astimezone()
        self.company: dict | None = None
        self.filings: dict | None = None
        self.facts: dict | None = None
        self.run_dir: Path | None = None
        self.downloads: dict[str, str] = {}
        self.filing_text: dict[str, str] = {}

    def selected(self, number: int) -> bool:
        return self.step is None or self.step == number

    def announce(self, number: int, label: str) -> None:
        say(f"\nStep {number}: {label}")

    def resolve(self, ticker: str) -> dict:
        url = "https://www.sec.gov/files/company_tickers.json"
        companies = self.client.json(url)
        for entry in companies.values():
            if entry["ticker"].upper() == ticker:
                return {"ticker": ticker, "name": entry["title"], "cik": int(entry["cik_str"]), "source": url}
        raise ValueError(f"Ticker {ticker} was not found in SEC company_tickers.json")

    def company_info(self) -> dict:
        if self.company is None:
            self.company = self.resolve(self.ticker)
        return self.company

    def folder(self) -> Path:
        if self.run_dir is None:
            company = self.company_info()
            stamp = self.started.strftime("%Y-%m-%d_%H-%M-%S_%f_%z")
            self.run_dir = RUNS / f"{slug(company['name'])}_{stamp}"
            self.run_dir.mkdir(parents=True, exist_ok=False)
        return self.run_dir

    def submissions(self, cik: int) -> dict:
        url = f"https://data.sec.gov/submissions/CIK{cik:010d}.json"
        submission = self.client.json(url)
        recent = submission["filings"]["recent"]
        rows = [{key: values[index] for key, values in recent.items()} for index in range(len(recent["form"]))]
        needed = {"10-K", "10-Q", "8-K"}
        def complete() -> bool:
            return (all(any(row["form"] == form and row["filingDate"] <= AS_OF for row in rows) for form in needed)
                    and any(row["form"] == "8-K" and "2.02" in (row.get("items") or "") and row["filingDate"] <= AS_OF for row in rows))
        if not complete():
            for older in submission["filings"].get("files", []):
                history = self.client.json(urljoin("https://data.sec.gov/submissions/", older["name"]))
                rows.extend({key: values[index] for key, values in history.items()} for index in range(len(history["form"])))
                if complete():
                    break
        return {"url": url, "rows": sorted((row for row in rows if row["filingDate"] <= AS_OF), key=lambda row: (row["filingDate"], row["accessionNumber"]), reverse=True)}

    @staticmethod
    def archive_urls(cik: int, accession: str) -> tuple[str, str]:
        base = f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession.replace('-', '')}/"
        return base, urljoin(base, f"{accession}-index.htm")

    def index_details(self, cik: int, row: dict) -> dict:
        base, index_url = self.archive_urls(cik, row["accessionNumber"])
        soup = BeautifulSoup(self.client.get(index_url), "html.parser")
        accepted_head = soup.find("div", class_="infoHead", string=re.compile(r"^Accepted$"))
        accepted = accepted_head.find_next_sibling("div", class_="info").get_text(" ", strip=True) if accepted_head else None
        documents = []
        for table in soup.select("table.tableFile"):
            for tr in table.select("tr"):
                cells = tr.find_all("td")
                if len(cells) < 4:
                    continue
                anchor = cells[2].find("a", href=True)
                if anchor:
                    href = anchor["href"]
                    parsed = urlsplit(href)
                    raw_document = parse_qs(parsed.query).get("doc") if parsed.path.endswith("/ix") else None
                    document_url = urljoin("https://www.sec.gov", raw_document[0]) if raw_document else urljoin(base, href)
                    documents.append({"description": cells[1].get_text(" ", strip=True), "name": anchor.get_text(" ", strip=True), "type": cells[3].get_text(" ", strip=True), "url": document_url})
        return {"accepted": accepted, "index_url": index_url, "documents": documents}

    def choose_filings(self) -> dict:
        if self.filings is not None:
            return self.filings
        company = self.company_info()
        submissions = self.submissions(company["cik"])
        rows = submissions["rows"]
        result = {"submissions_url": submissions["url"], "filing_list": [{key: row.get(key) for key in ("form", "filingDate", "accessionNumber", "items")} for row in rows]}
        for form in ("10-K", "10-Q"):
            row = next((row for row in rows if row["form"] == form), None)
            if row is None:
                raise ValueError(f"No {form} found for {self.ticker} as of {AS_OF}")
            result[form] = {**row, **self.index_details(company["cik"], row)}
        for row in rows:
            if row["form"] != "8-K" or "2.02" not in (row.get("items") or ""):
                continue
            detail = {**row, **self.index_details(company["cik"], row)}
            main = next((doc for doc in detail["documents"] if doc["type"] == "8-K"), None)
            exhibit = next((doc for doc in detail["documents"] if doc["type"] == "EX-99.1"), None)
            if main is None:
                continue
            main_text = text_from_html(self.client.get(main["url"]))
            if re.search(r"Item\s*2\.02\b", main_text, re.I):
                result["8-K"] = detail
                self.filing_text["8-K"] = main_text
                break
        if "8-K" not in result:
            raise ValueError(f"No Item 2.02 8-K found for {self.ticker} as of {AS_OF}")
        self.filings = result
        return result

    def save_json(self, name: str, data: dict) -> None:
        (self.folder() / name).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def download_documents(self) -> None:
        filings = self.choose_filings()
        for form in ("10-K", "10-Q", "8-K"):
            detail = filings[form]
            document = next((doc for doc in detail["documents"] if doc["type"] == form), None)
            if document is None:
                raise ValueError(f"Primary {form} document missing from {detail['index_url']}")
            content = self.filing_text.get(form) or text_from_html(self.client.get(document["url"]))
            filename = f"{self.ticker}_{form}_{detail['accessionNumber']}.txt"
            (self.folder() / filename).write_text(content, encoding="utf-8")
            self.downloads[form] = document["url"]
            self.filing_text[form] = content
            say(f"  Saved {filename} ({len(content):,} characters) from {document['url']}")
        exhibit = next((doc for doc in filings["8-K"]["documents"] if doc["type"] == "EX-99.1"), None)
        if exhibit is None:
            raise ValueError(f"Exhibit 99.1 is missing from the latest Item 2.02 8-K: {filings['8-K']['index_url']}")
        content = text_from_html(self.client.get(exhibit["url"]))
        filename = f"{self.ticker}_EX-99.1_{filings['8-K']['accessionNumber']}.txt"
        (self.folder() / filename).write_text(content, encoding="utf-8")
        self.downloads["EX-99.1"] = exhibit["url"]
        self.filing_text["EX-99.1"] = content
        say(f"  Saved {filename} ({len(content):,} characters) from {exhibit['url']}")
        self.save_json("filings.json", {"as_of": AS_OF, "company": self.company_info(), "filings": filings, "document_urls": self.downloads})

    @staticmethod
    def annual_record(record: dict, duration: bool) -> bool:
        if record.get("form") not in ANNUAL_FORMS or record.get("filed", "9999") > AS_OF:
            return False
        if duration:
            if "start" not in record:
                return False
            days = (date.fromisoformat(record["end"]) - date.fromisoformat(record["start"])).days
            return 330 <= days <= 380
        return "start" not in record

    def choose_tag(self, facts: dict, candidates: list[str], unit: str, duration: bool, ceiling: str | None = None) -> tuple[str | None, list[dict]]:
        choices = []
        for priority, tag in enumerate(candidates):
            records = facts.get("us-gaap", {}).get(tag, {}).get("units", {}).get(unit, [])
            annual = [record for record in records if self.annual_record(record, duration) and (ceiling is None or record["end"] <= ceiling)]
            if annual:
                choices.append((max(record["end"] for record in annual), -priority, tag, annual))
        if not choices:
            return None, []
        _, _, tag, records = max(choices)
        return tag, records

    @staticmethod
    def matching_record(records: list[dict], period_end: str, preferred_accession: str) -> dict | None:
        matches = [record for record in records if record["end"] == period_end]
        if not matches:
            return None
        return max(matches, key=lambda record: (record["accn"] == preferred_accession, record["filed"], record["accn"]))

    def collect_facts(self, company: dict) -> dict:
        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{company['cik']:010d}.json"
        raw = self.client.json(url)
        revenue_tags, revenue_unit, _ = CONCEPTS["total_revenue"]
        revenue_tag, revenue_records = self.choose_tag(raw["facts"], revenue_tags, revenue_unit, True)
        if not revenue_records:
            raise ValueError(f"No annual revenue concept found for {company['ticker']}")
        filings = self.submissions(company["cik"])["rows"]
        latest_annual = next((row for row in filings if row["form"] == "10-K"), None)
        if latest_annual is None or not latest_annual.get("reportDate"):
            raise ValueError(f"Latest 10-K fiscal year end is unavailable for {company['ticker']}")
        fiscal_end = max(record["end"] for record in revenue_records)
        if fiscal_end != latest_annual["reportDate"]:
            raise ValueError(f"Latest annual revenue ends {fiscal_end}, but the latest 10-K ends {latest_annual['reportDate']}; verify revenue tags in the filing")
        prior_ends = sorted({record["end"] for record in revenue_records if record["end"] < fiscal_end})
        prior_ends = [end for end in prior_ends if 300 <= (date.fromisoformat(fiscal_end) - date.fromisoformat(end)).days <= 430]
        if not prior_ends:
            raise ValueError(f"No prior annual revenue period found for {company['ticker']}")
        prior_end = prior_ends[-1]
        preferred = max((record for record in revenue_records if record["end"] == fiscal_end), key=lambda record: (record["filed"], record["accn"]))["accn"]
        concepts = {}
        for name, (tags, unit, duration) in CONCEPTS.items():
            tag, records = (revenue_tag, revenue_records) if name == "total_revenue" else self.choose_tag(raw["facts"], tags, unit, duration, fiscal_end)
            periods = {}
            for label, end in (("current", fiscal_end), ("prior", prior_end)):
                record = self.matching_record(records, end, preferred)
                periods[label] = None if record is None else {key: record.get(key) for key in ("val", "start", "end", "accn", "filed", "form", "fy", "fp") if key in record}
            concepts[name] = {"tag": f"us-gaap:{tag}" if tag else None, "unit": unit, **periods}
        result = {"company": company, "as_of": AS_OF, "retrieved_at": datetime.now().astimezone().isoformat(), "source": url, "fiscal_year_end": fiscal_end, "prior_fiscal_year_end": prior_end, "preferred_10k_accession": preferred, "concepts": concepts}
        return result

    def fact_data(self) -> dict:
        if self.facts is None:
            self.facts = self.collect_facts(self.company_info())
        return self.facts

    @staticmethod
    def number(facts: dict, concept: str, period: str = "current") -> Decimal | None:
        record = facts["concepts"][concept][period]
        return None if record is None else Decimal(str(record["val"]))

    def show_facts(self, facts: dict) -> None:
        say(f"  Fiscal year ended {facts['fiscal_year_end']}; prior year ended {facts['prior_fiscal_year_end']}")
        say(f"  Source: {facts['source']}")
        for name, item in facts["concepts"].items():
            say(f"  {name} [{item['tag'] or 'tag unavailable'}]")
            for label in ("current", "prior"):
                record = item[label]
                if record is None:
                    say(f"    {label}: unavailable for the selected fiscal year")
                else:
                    say(f"    {label}: {value(record['val'], item['unit'])}; end {record['end']}; filed {record['filed']}; 10-K {record['accn']}")

    def calculate(self, facts: dict) -> dict:
        get = lambda name, period="current": self.number(facts, name, period)
        rev, rev_prev = get("total_revenue"), get("total_revenue", "prior")
        op, net, eq = get("operating_income"), get("net_income"), get("stockholders_equity")
        eq_prev = get("stockholders_equity", "prior")
        debt, current_debt = get("long_term_debt_noncurrent"), get("long_term_debt_current")
        cfo, capex, eps = get("cash_from_operations"), get("additions_to_property_and_equipment"), get("diluted_eps")
        debt_tag = facts["concepts"]["long_term_debt_noncurrent"]["tag"]
        total_debt = debt + current_debt if debt_tag == "us-gaap:LongTermDebtNoncurrent" and debt is not None and current_debt is not None else None
        avg_eq = (eq + eq_prev) / 2 if eq is not None and eq_prev is not None else None
        output = {
            "revenue_growth_percent": (safe_div(rev - rev_prev, rev_prev) * 100) if rev is not None and rev_prev is not None and rev_prev != 0 else None,
            "operating_margin_percent": (safe_div(op, rev) * 100) if op is not None and rev is not None and rev != 0 else None,
            "return_on_average_equity_percent": (safe_div(net, avg_eq) * 100) if net is not None and avg_eq not in (None, 0) else None,
            "debt_to_equity": safe_div(total_debt, eq),
            "free_cash_flow_usd": (cfo - capex) if cfo is not None and capex is not None else None,
            "price_to_earnings": safe_div(self.price, eps),
            "inputs": {"price_usd_per_share": self.price, "price_date": self.price_date, "price_source": self.price_source, "debt_tag": debt_tag},
        }
        say(f"  Revenue growth = ({value(rev)} - {value(rev_prev)}) / {value(rev_prev)} = {percent(output['revenue_growth_percent'])}")
        say(f"  Operating margin = {value(op)} / {value(rev)} = {percent(output['operating_margin_percent'])}")
        say(f"  Return on average equity = {value(net)} / (({value(eq)} + {value(eq_prev)}) / 2) = {percent(output['return_on_average_equity_percent'])}")
        if debt_tag == "us-gaap:LongTermDebt":
            say("  Debt tag does not establish whether the current portion is included; verify the filing before calculating debt to equity.")
        say(f"  Debt to equity = {value(total_debt)} / {value(eq)} = {output['debt_to_equity']:.4f}x" if output["debt_to_equity"] is not None else "  Debt to equity = unavailable")
        if debt_tag != "us-gaap:LongTermDebt":
            say(f"    Debt includes noncurrent {value(debt)} + current {value(current_debt)}")
        say(f"  Free cash flow = {value(cfo)} - {value(capex)} = {value(output['free_cash_flow_usd'])}")
        if self.price is not None:
            say(f"  Price input: {value(self.price, 'USD/shares')}; date {self.price_date or 'unspecified'}; source {self.price_source or 'unspecified'}")
        say(f"  P/E = {value(self.price, 'USD/shares')} / {value(eps, 'USD/shares')} = {output['price_to_earnings']:.4f}x" if output["price_to_earnings"] is not None else "  P/E = unavailable; provide --price and annual diluted EPS")
        return {key: (str(val) if isinstance(val, Decimal) else val) for key, val in output.items() if key != "inputs"} | {"inputs": {key: (str(val) if isinstance(val, Decimal) else val) for key, val in output["inputs"].items()}}

    def release_lines(self) -> None:
        if "EX-99.1" not in self.filing_text:
            filings = self.choose_filings()
            exhibit = next((doc for doc in filings["8-K"]["documents"] if doc["type"] == "EX-99.1"), None)
            if exhibit is None:
                raise ValueError(f"Exhibit 99.1 is missing from the latest Item 2.02 8-K: {filings['8-K']['index_url']}")
            self.filing_text["EX-99.1"] = text_from_html(self.client.get(exhibit["url"]))
            source = exhibit["url"]
        else:
            source = self.downloads["EX-99.1"]
        lines = self.filing_text["EX-99.1"].splitlines()
        sentences = [(number, sentence) for number, line in enumerate(lines, 1) for sentence in re.split(r"(?<=[.!?])\s+(?=[A-Z])", line)]
        revenue = [(number, sentence) for number, sentence in sentences if re.search(r"(?:quarterly|total company|total) revenue", sentence, re.I) and re.search(r"\$|\d", sentence)]
        eps = [(number, sentence) for number, sentence in sentences if re.search(r"diluted (?:earnings|net income) per share|(?:earnings )?per diluted share|diluted EPS", sentence, re.I) and re.search(r"\$|\d", sentence)]
        say(f"  Source: {source}")
        for label, matches in (("Quarter revenue", revenue), ("Diluted EPS", eps)):
            if matches:
                number, sentence = matches[0]
                say(f"  {label} (saved release line {number}): {sentence}")
            else:
                say(f"  {label}: no explicit line found; inspect the saved release text")

    def run(self) -> None:
        if self.selected(1):
            self.announce(1, "Resolve ticker to CIK")
            say(f"  {self.company_info()['ticker']} | {self.company['name']} | CIK {self.company['cik']:010d} | {self.company['source']}")
        if self.selected(2):
            self.announce(2, "Select latest filings")
            selected_filings = self.choose_filings()
            say(f"  Filing list from {selected_filings['submissions_url']}:")
            for row in selected_filings["filing_list"]:
                say(f"    {row['filingDate']} | {row['form']} | {row['accessionNumber']} | items {row['items'] or '-'}")
            for form, detail in selected_filings.items():
                if form in ("10-K", "10-Q", "8-K"):
                    say(f"  {form}: {detail['accessionNumber']} | filed {detail['filingDate']} | Accepted {detail['accepted']} | {detail['index_url']}")
        if self.selected(3):
            self.announce(3, "Download documents and convert to plain text")
            self.download_documents()
        if self.selected(4):
            self.announce(4, "Select annual XBRL facts")
            facts = self.fact_data()
            self.show_facts(facts)
            self.save_json("facts.json", facts)
        if self.selected(5):
            self.announce(5, "Calculate ratios and free cash flow")
            self.save_json("calculations.json", self.calculate(self.fact_data()))
        if self.selected(6):
            self.announce(6, "Find quarterly revenue and diluted EPS in Exhibit 99.1")
            self.release_lines()
        if self.selected(7):
            self.announce(7, "Get peer facts and operating margins")
            if not self.peers:
                say("  No peers supplied with --peers.")
            else:
                peer_results = {}
                for ticker in self.peers:
                    company = self.resolve(ticker)
                    facts = self.collect_facts(company)
                    say(f"  Peer: {ticker} | {company['name']}")
                    self.show_facts(facts)
                    revenue = self.number(facts, "total_revenue")
                    operating = self.number(facts, "operating_income")
                    margin = safe_div(operating, revenue)
                    say(f"  {ticker} operating margin = {value(operating)} / {value(revenue)} = {percent(margin * 100 if margin is not None else None)}")
                    peer_results[ticker] = {**facts, "operating_margin_percent": str(margin * 100) if margin is not None else None}
                self.save_json("peer_facts.json", peer_results)
        if self.run_dir is not None:
            say(f"\nSaved output: {self.run_dir}")
        if self.step is None:
            from equity_research_roles import run_roles
            run_roles(self)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ticker", help="SEC ticker symbol")
    parser.add_argument("--peers", nargs="+", default=[], help="Peer tickers separated by spaces or commas")
    parser.add_argument("--price", type=Decimal, help="Share price in USD for annual P/E")
    parser.add_argument("--price-date", help="Date of the share price, YYYY-MM-DD")
    parser.add_argument("--price-source", help="URL or description of the share price source")
    parser.add_argument("--step", type=int, choices=range(1, 8), metavar="{1..7}", help="Run only one numbered step")
    args = parser.parse_args()
    try:
        if args.price is not None and args.price <= 0:
            raise ValueError("--price must be greater than zero")
        if args.price_date:
            date.fromisoformat(args.price_date)
        Desk(args.ticker, args.peers, args.price, args.step, args.price_date, args.price_source).run()
    except (ValueError, requests.RequestException, KeyError, OSError) as error:
        say(f"Error: {error}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
