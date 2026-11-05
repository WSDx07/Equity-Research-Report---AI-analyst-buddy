# Equity desk flow — prototype

This implementation is incomplete. Do not rely on the verified report as a complete numerical audit. In particular, the verifier does not recompute ratios, does not reliably identify every number in arbitrary legacy reports, and cannot always find a supported correction. It removes unsupported claims instead of inventing replacements. It may also need more filing context than a single line to judge a period or definition.

The Flow uses the existing seven data steps, then the Research Analyst, Financial Analyst, Investment Advisor, Strategy Manager and Verifier. Each specialist may run at most twice. The Manager runs once. The four original role instructions are in `roles/`. Inputs and outputs are saved in the run folder. The `PURDUE_API_KEY` and `SEC_USER_AGENT` settings are read from the workspace `.env`. All roles and the verifier use Purdue GenAI Studio, with the model selected by `PURDUE_MODEL` or `gpt-oss:120b` by default. Runs make network requests and model calls.

After the seven steps, the flow also reads `FINDATA_API_KEY` from `.env` and requests annual statements from Financial Datasets. It saves the response and a comparison to the run folder, and gives the comparison to the Financial Analyst and Manager. Matches require the same ticker, annual period end, USD currency and filing accession, and a filing date on or before the analysis date. Only selected SEC tags with reasonably comparable normalized fields are compared. Matches and differences are exact numeric comparisons, not proof of equivalent definitions or correctness. Unavailable data, unmatched filings and unsupported definitions are marked as not comparable. If the request fails or the key is missing, the run continues and records that the cross-check is unavailable. Financial Datasets states that its financial statements also come from SEC filings; this checks a second extraction, not independent underlying data. API requests may count against your plan. `--verify-only` uses saved data and does not make a Financial Datasets request.

Install in PowerShell:

```powershell
uv venv --python 3.12 .venv
uv pip install --python .venv\Scripts\python.exe -r requirements.txt
```

Start the local browser page with:

```powershell
.\.venv\Scripts\python.exe desk_ui.py
```

The server opens `http://127.0.0.1:8765/` in the default browser. Keep the command running while the page is in use; press Ctrl+C to stop it. The page runs the same desk command, shows node progress, and displays the saved verified report. It binds to this computer only and uses the existing `.env` settings. The verifier limitations described above still apply.

Example invocation (replace the symbols and price):

```powershell
.\.venv\Scripts\python.exe desk_flow.py MSFT --peers AAPL GOOGL --price 400
```

The supplied price has no date or independent source. It remains an unverified user input. The current draft does not include calculated valuation ratios in the report.

Verification only creates a timestamped subfolder in the saved run and does not overwrite the original report:

```powershell
.\.venv\Scripts\python.exe desk_flow.py --verify-only "C:\path\to\saved\run"
```

The research and verifier model calls use bounded, line-numbered filing excerpts to fit the model's context. The full filing texts remain saved and code checks use them, but the model cannot assess omitted passages. The verifier also receives the report and saved facts. Even when the code and model mark a claim correct, independent review is needed. The paper's results do not establish that a report is factually correct or that a recommendation will outperform a benchmark.

Each analyst is asked to end its structured output with an `insight` field containing a single `Insight:` line and a filing-line quotation. The Manager checks each Insight against the candidate first paragraph of the release, and failing or unassessed roles can be revised once. The saved release text does not preserve original HTML paragraph boundaries, so the candidate paragraph must be checked against the release. The Manager's semantic decision can be wrong; after a revision it is not called a second time, so the final review records that the revised Insight has not been semantically rechecked. Missing, invalid, or unassessed Insights remain visible in the evidence gaps. Numeric Insight claims go through the existing verifier, whose limitations still apply.
