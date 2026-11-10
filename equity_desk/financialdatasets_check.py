"""Compare selected SEC XBRL facts with Financial Datasets annual statements."""
from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal, InvalidOperation

import requests

URL = "https://api.financialdatasets.ai/financials/"

# Only map concepts where the SEC tag has a reasonably comparable definition.
# Even for these, matching amounts are not proof of identical definitions.
MAPPINGS = {
    "total_revenue": ("income_statements", "revenue", {"us-gaap:Revenues", "us-gaap:RevenueFromContractWithCustomerExcludingAssessedTax", "us-gaap:SalesRevenueNet"}),
    "operating_income": ("income_statements", "operating_income", {"us-gaap:OperatingIncomeLoss"}),
    "net_income": ("income_statements", "net_income", {"us-gaap:NetIncomeLoss"}),
    "diluted_eps": ("income_statements", "earnings_per_share_diluted", {"us-gaap:EarningsPerShareDiluted"}),
    "stockholders_equity": ("balance_sheets", "shareholders_equity", {"us-gaap:StockholdersEquity"}),
    "cash_from_operations": ("cash_flow_statements", "net_cash_flow_from_operations", {"us-gaap:NetCashProvidedByUsedInOperatingActivities"}),
}


def fetch_statements(ticker: str, api_key: str, as_of: str, session=requests) -> dict:
    if not api_key.strip():
        raise ValueError("FINDATA_API_KEY is missing or empty in .env")
    try:
        response = session.get(URL, params={"ticker": ticker, "period": "annual", "limit": 4, "report_period_lte": as_of}, headers={"X-API-KEY": api_key.strip()}, timeout=30, allow_redirects=False)
    except requests.RequestException as exc:
        raise RuntimeError(f"Financial Datasets request failed ({type(exc).__name__})") from None
    if response.status_code != 200:
        raise RuntimeError(f"Financial Datasets returned HTTP {response.status_code}")
    try:
        data = json.loads(response.text, parse_float=Decimal)
    except (ValueError, TypeError):
        raise ValueError("Financial Datasets returned invalid JSON") from None
    if not isinstance(data, dict) or not isinstance(data.get("financials"), dict):
        raise ValueError("Financial Datasets response has no financials object")
    return data


def compare(facts: dict, data: dict) -> dict:
    as_of = facts["as_of"]
    statements = data["financials"]
    rows = []
    for name, concept in facts.get("concepts", {}).items():
        for label in ("current", "prior"):
            fact = concept.get(label)
            row = {"concept": name, "period_label": label, "sec_tag": concept.get("tag"), "sec_unit": concept.get("unit"), "sec_fact": fact, "status": "not_comparable", "reason": "No safe mapping for this SEC tag and provider field."}
            mapping = MAPPINGS.get(name)
            if not fact:
                row["reason"] = "SEC fact is unavailable."
            elif mapping and concept.get("tag") in mapping[2]:
                collection, field, _ = mapping
                row.update({"provider_statement": collection, "provider_field": field})
                available = statements.get(collection)
                available = available if isinstance(available, list) else []
                candidates = [s for s in available if isinstance(s, dict) and isinstance(s.get("ticker"), str) and s["ticker"].upper() == facts["company"]["ticker"].upper() and s.get("period") == "annual" and s.get("report_period") == fact.get("end") and s.get("currency") == "USD" and isinstance(s.get("filing_date"), str) and s["filing_date"] <= as_of and s.get("accession_number") == fact.get("accn")]
                if len(candidates) != 1:
                    row["reason"] = "No unique annual USD statement with the same period and filing accession, filed by the analysis date."
                elif candidates[0].get(field) is None:
                    row["reason"] = "Provider field is unavailable."
                else:
                    statement = candidates[0]
                    row["provider_fact"] = {key: statement.get(key) for key in ("ticker", "report_period", "period", "currency", "filing_date", "accession_number", "filing_url")}
                    row["provider_fact"]["value"] = statement[field]
                    try:
                        sec_value = Decimal(str(fact["val"]))
                        provider_value = Decimal(str(statement[field]))
                        if not sec_value.is_finite() or not provider_value.is_finite():
                            raise InvalidOperation
                        row["difference_provider_minus_sec"] = str(provider_value - sec_value)
                        row["status"] = "numeric_match" if provider_value == sec_value else "difference"
                        row["reason"] = "Exact numeric comparison; normalized definitions and possible restatements still require review."
                    except (InvalidOperation, ValueError, TypeError):
                        row["reason"] = "One of the values is not a finite number."
            rows.append(row)
    return {"source": URL, "retrieved_at": datetime.now().astimezone().isoformat(), "analysis_date": as_of, "basis": "Both sources derive from SEC filings; numeric agreement does not independently establish correctness or definition equivalence.", "rows": rows}
