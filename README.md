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

Replace the example ticker, peers, and price. The supplied price is an unverified user input. The workflow saves its inputs, intermediate outputs, and reports under `equity_research_runs/`. To verify a saved run again:

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

## Spinoff seeker (in development)

The local page has a start-date form for a future spinoff screen. The full seeker is not ready: the SEC filing reader is incomplete, and an LSEG export and exchange check are still needed before using prices. The page reports this instead of displaying a screen as complete.

`spinoff_factors.json` contains **provisional** settings: a 90-calendar-day window and three independent 10-point factors. The current starter thresholds are market capitalization at or below USD 2 billion, a price decline of at least 20%, and documented insider ownership of at least 5%. These are editable examples, not validated investment rules. Set a factor's `weight` to `0` to omit its points; other factors' points do not change. Missing inputs remain unavailable.

The prototype's offline tests run from PowerShell:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s "$env:USERPROFILE\.codex\skills\us-spinoff-seeker\scripts" -p "test_*.py"
```

LSEG Workspace web exports must stay outside this repository. The prototype can read mapped CSV or XLSX exports, but it must first be configured for the actual exported fields and checked against an exchange. It does not send raw price series to the model. The optional diagnostic run is labeled partial and is not a complete spinoff screen; generated outputs are ignored by Git.

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
