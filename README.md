# Equity Research Desk

A Python prototype that gathers SEC filing data, calculates financial facts, and runs an equity research workflow. Research, financial, advisory, and manager roles contribute to a report that is then checked by a verifier. A local browser interface and a command-line interface are available.

## Setup

You need Python 3.12, network access, a Purdue GenAI Studio API key, and an SEC user agent that identifies you and includes contact information. Model and data requests may incur charges.

From the repository folder in PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Open `.env` in a text editor. Set `PURDUE_API_KEY` and replace `SEC_USER_AGENT` with your name and email address. Optionally set `PURDUE_MODEL` and `FINDATA_API_KEY`; without the latter, the Financial Datasets cross-check is recorded as unavailable. Keep `.env` private. The desk reads its settings from this file.

## Run the desk

Start the browser interface:

```powershell
.\.venv\Scripts\python.exe desk_ui.py
```

Open <http://127.0.0.1:8765/> if it does not open automatically. Enter a ticker and, if wanted, peer tickers and a price. Keep the terminal open while the desk runs; press Ctrl+C to stop the server.

Or run it from the command line:

```powershell
.\.venv\Scripts\python.exe desk_flow.py MSFT --peers AAPL GOOGL --price 400
```

Replace the example ticker, peers, and price. The supplied price is an unverified user input. The workflow saves its inputs, intermediate outputs, and reports under `equity_research_runs/`.

For a newly listed company without a 10-K, the desk can use its Form 10 information statement and 10-Q when available. It keeps annual 10-K figures unavailable rather than treating quarterly figures as annual. Review the verifier's findings and filing sources before relying on a report.

To verify a saved run again:

```powershell
.\.venv\Scripts\python.exe desk_flow.py --verify-only "C:\path\to\saved\run"
```

This creates a new verification subfolder. See [the flow guide](docs/DESK_FLOW.md) for the workflow, cross-check, and verifier limitations. The separate source-text research agent is described in [its guide](docs/RESEARCH_ANALYST.md).

## Run the other scripts

Run these commands from the repository folder in PowerShell, after completing setup above.

### Run one SEC data step

The data desk runs one step at a time and needs `SEC_USER_AGENT` in `.env`. For example, to look up a ticker:

```powershell
.\.venv\Scripts\python.exe equity_research_data_desk.py MSFT --step 1
```

Replace `1` with the step you need:

| Step | Action |
| --- | --- |
| 1 | Resolve the ticker to a company and CIK |
| 2 | Select recent filings |
| 3 | Download filings and convert them to text |
| 4 | Select annual XBRL facts |
| 5 | Calculate ratios and free cash flow |
| 6 | Find quarterly revenue and diluted EPS in the earnings release |
| 7 | Retrieve peer facts; provide peers with `--peers AAPL GOOGL` |

Some steps fetch data needed for that step. The data desk does not run the full report without `--step`; use `desk_flow.py` for that.

### Run the separate research agent

Create a `sources.json` file with dated source text as shown in the [research agent guide](docs/RESEARCH_ANALYST.md). Set `OPENAI_API_KEY` in `.env` or your environment, then run:

```powershell
.\.venv\Scripts\python.exe research_analyst.py sources.json --output research_brief.json
```

The agent analyzes the text supplied in the JSON file; it does not fetch sources itself. It writes the result to `research_brief.json` if validation succeeds.

### Run the legacy environment check

```powershell
.\.venv\Scripts\python.exe scripts\check_env.py
```

This prints the SEC user agent and the first four characters of the legacy `API_KEY` and `FINDATA_API_KEY` values. It does not check `PURDUE_API_KEY` or validate whether a key works. Avoid sharing its output.

The files in `equity_desk/` are supporting Python modules. The entry-point scripts import them automatically; they are not intended to be run on their own.

## Spinoff seeker

The seeker skill is included in .agents/skills/us-spinoff-seeker/, so GitHub receives the instructions, scripts, and tests with this project. The local desk page runs this project copy. spinoff_factors.json sets the 90-day window and user-selected thresholds: market capitalization at or below USD 2 billion, decline of at least 15% from the first post-distribution close, and insider ownership of at least 5%. Each active factor is worth 25 points; analyst coverage has weight 0 until a verified data source is available.

The report identifies its index date, search limits, missing sources, and unranked names. The search starts with the year before the requested start date. The SEC filing extractors cover limited formats, so the report is a screen and can miss filings or facts. The LSEG close path uses the user's stated `TR.CLOSEPRICE(Adjusted=0)` and primary RIC assumptions; the report discloses the remaining limits. Missing active factors leave a company unranked. The report ends with `screens, not recommendations`.

Run the seeker from the page with a distribution start date. To run it from PowerShell:

```powershell
& "$env:USERPROFILE\.codex\venvs\us-spinoff-lseg\Scripts\python.exe" .\.agents\skills\us-spinoff-seeker\scripts\seeker.py --start 2025-11-13 --config .\spinoff_factors.json --env .\.env --output .\spinoff_runs
```

Run the skill tests:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s .\.agents\skills\us-spinoff-seeker\scripts -p "test_*.py"
```

Keep .env private. The isolated LSEG Python environment is machine-specific; on another computer, install the LSEG library there and set the SEC User-Agent and LSEG App Key in its local .env.

## Lab 07 worksheet

Our team chose to own the spinoff factor check; the [initial protocol](docs/factor_check_protocol.md) and synthetic demonstration are in place, and the historical WRDS check remains to be built.

The local Week 4 reports for Shlok (TTWO/VYLR), Sam (Sagard/HONA), and Ryan (LCID/REZI) are under `runs/live/`; the folders disclose missing figures and late filing windows. No commit or push was made. Lab 07 pre-work is in the repository. The worksheet skill is `.agents/skills/us-spinoff-worksheet/`; its `SKILL.md` gives the source-collection, LSEG reader, calculation, save, validation, and hit-rate-table commands. The input rules are in `lab07_worksheet_rules.md`, and the qualitative persona is `personas/investment_advisor.md`.

The seeker close reader now also returns daily share volume. Its official reader requires listing evidence and an exchange spot check; its candidate reader is explicitly unverified. The worksheet hook definition is configured in `.codex/hooks.json` and has been trusted. A live PostToolUse check blocked an altered worksheet and allowed the corrected copy. A live Stop event with an erroneous worksheet has not been observed.

The worksheet values owner cash flow as equity directly because the course formula starts with after-tax earnings. Do not call that result firm or enterprise value, or add cash and subtract debt from it. Report cash, debt, and liabilities as separate sourced facts. The rules file contains the formulas, thresholds, missing-data behavior, and conviction conditions.

The Vylor team run and a dated worksheet now exist. The latest is [the Vylor worksheet](equity_research_runs/Vylor_Inc_2026-11-14_01-08-41_219149_-0500/worksheet-20261114-025135-330558.md). It includes pro forma financing assumptions and conditional separation obligations, but diluted share counts and several filing facts remain unestablished; affected per-share values and the Take-Two live view remain `not computed`. The Vylor research report's verifier recorded unresolved unsupported and incorrect claims, so review its sources before relying on it.

LSEG bars were obtained with `TR.CLOSEPRICE(Adjusted=0)` under the user's stated interpretation of that field. The report discloses that an independent exchange-price comparison was not completed. The local files in `%TEMP%` are licensed reader data and are not included in the repository. Vylor volume is from the selected NYSE instrument, not necessarily consolidated market volume.

For the live hit-rate table, run `.\.venv\Scripts\python.exe .\.agents\skills\us-spinoff-worksheet\scripts\hit_rate_table.py --runs ".\runs\live"`. For practice, replace the folder with `.\runs\practice`. The command rereads available reader files but does not refresh them; keep one view record per run folder. The saved Take-Two release is a practice record marked `after`, with a view of `not computed`. No qualifying live report has been filed yet.

Run the focused closes-reader tests from the repository root:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s .\.agents\skills\us-spinoff-seeker\scripts -p "test_closes_reader.py"
```

`run_worksheet.py` collects sources, extracts supported facts, calculates in code, makes one qualitative model request, and saves a dated worksheet. It now renders numeric markers and checks the rendered file before saving it. The extractor covers limited filing formats and records gaps; a guard pass is not proof that source context, reporting tags, units, or every spelled-out number are correct. The project page's saved-run selector opens a run's report and latest dated worksheet together. A separately reviewed Vylor worksheet corrects an unsupported model comparison and adds filing-backed financing facts; future generated worksheets only include facts the automatic reader establishes. The hook's live Stop behavior on an erroneous worksheet and its source-check limitations remain open. The hit-rate table reads saved live views only; it does not validate investment performance. Vylor is the selected spinoff company, with the partner's agreement; Take-Two is the separate live-release company.

## Tests

Run the local test suite from the repository folder:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

## Repository layout

| Path | Contents |
| --- | --- |
| `desk_ui.py`, `desk_ui/` | Main browser interface and page |
| `desk_flow.py` | Main command-line workflow |
| `equity_research_data_desk.py` | SEC data collection; also supports individual steps from the command line |
| `research_analyst.py` | Separate research agent for supplied source text |
| `equity_desk/` | Supporting modules for roles, calculations, filing excerpts, and verification |
| `scripts/` | Extra utilities, including the legacy environment check |
| `roles/` | Role instructions used by the workflow |
| `tests/` | Local tests |
| `docs/` | Guides, prior reports, and reference material |
| `equity_research_runs/` | Saved desk runs |
| `verifier_trials/` | Saved verifier trials |

New generated runs and trials are ignored by Git; files already tracked remain tracked. The desk is a prototype: its verifier does not check every possible numerical claim, and its model only sees selected filing excerpts. Review the report and its sources independently. A recommendation is not evidence of future investment performance.
