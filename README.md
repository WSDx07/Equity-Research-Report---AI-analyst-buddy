# Equity Research Desk

A Python prototype that gathers SEC filing data, calculates financial facts, and runs an equity research workflow. Research, financial, advisory, and manager roles contribute to a report that is then checked by a verifier. A local browser interface and a command-line interface are available.

## Team ownership and join

**We own:** the spinoff factor check. **Our join:** `one_desk.py` runs the seeker for `screen` input, then pick, the agent team, worksheet, and hook; ticker input goes through pick, team, worksheet, and hook using the latest saved seeker registry when available. The worksheet is a pipeline step after the team report, not a tool called by an analyst role.

## Lab 09 - Prove It Together status (November 17, 2026)

The Checkpoint 3 draft is `docs/checkpoint3_draft.md`. Its member roles are proposed assignments for review, and `Team 3` is a working label; confirm the Brightspace team name and member responsibilities before submission. The AI-partner NVDA and HD run folders are under `one_desk_runs/`; both have reports and offline replay proofs, and the NVDA run has the completed three-column comparison. A second automated Manager semantic review was not rerun for either partner report; the saved source review is manual.

The current TSN/GEV record is `runs/live/Week 11-16to11-22/Shlok_TSN_GEV/report.md`. TSN's view is computed, but it was recorded 32.94 hours after filing and after the first post-filing close, so it is outside the 24-hour window. The GEV worksheet now cites its original Form 10 and Information Statement for the 1:4 distribution ratio; it is not a response to GEV's latest earnings release. The Lab 09 files remain local and uncommitted; no Brightspace upload is recorded here.

## Setup

You need Python 3.12, network access, a Purdue GenAI Studio API key, and an SEC user agent that identifies you and includes contact information. Model and data requests may incur charges.

From the repository folder in PowerShell (Windows):

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

From the repository folder in Terminal (macOS or Linux):

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
```

On macOS and Linux, every command below that starts with `.\.venv\Scripts\python.exe` runs as `.venv/bin/python` instead, and paths use `/` in place of `\`. Example: `.venv/bin/python one_desk.py YOUR_TICKER`. If `python3.12` is not found, install Python 3.12 from python.org or Homebrew first.

LSEG is optional. Without LSEG Workspace and the `lseg-data` library, the desk still runs end to end: the agent team, worksheet, and hook finish, and price-based worksheet comparisons say `not computed`. Leave `LSEG_APP_KEY` empty in `.env` in that case.

Open `.env` in a text editor. Set `PURDUE_API_KEY` and replace `SEC_USER_AGENT` with your name and email address. Optionally set `PURDUE_MODEL` and `FINDATA_API_KEY`; without the latter, the Financial Datasets cross-check is recorded as unavailable. Keep `.env` private. The desk reads its settings from this file.

## Run the desk

Start the browser interface:

```powershell
.\.venv\Scripts\python.exe desk_ui.py
```

```bash
.venv/bin/python desk_ui.py
```

Open <http://127.0.0.1:8765/> if it does not open automatically. Enter a ticker or `screen`. Keep the terminal open while the desk runs; press Ctrl+C to stop the server.

The joined desk runs these parts in code order: seeker when you enter `screen`, ticker pick, agent team, worksheet skill, and output hook. It saves them under one folder in `one_desk_runs/<TICKER>_<start-time>/`. The screen uses the latest report produced by that seeker run. It starts with the configured window unless you set `--screen-start`.

```powershell
.\.venv\Scripts\python.exe one_desk.py YOUR_TICKER
.\.venv\Scripts\python.exe one_desk.py screen
.\.venv\Scripts\python.exe one_desk.py --replay ".\one_desk_runs\YOUR_TICKER_<timestamp>"
.\.venv\Scripts\python.exe one_desk.py --check-copy ".\one_desk_runs\YOUR_TICKER_<timestamp>\seeded-copy-final-report.md"
.\.venv\Scripts\python.exe one_desk.py --finish-empty-screen ".\one_desk_runs\SCREEN_<timestamp>"
```

Replace `YOUR_TICKER` with a ticker and replace the replay path with a saved run folder. Replay checks the saved outputs, prints the saved final report, and does not fetch filings. To check an edited copy, first copy that run's `final_report.md` to `seeded-copy-final-report.md` inside the same run folder. `--check-copy` runs the hook on that copy and reports a refused numeric claim by report line, filing, and section. The first report line lists the filings read. Each part prints its elapsed seconds. If a ticker is absent from the selected seeker registry, its spinoff sections say `not applicable`; the team and worksheet continue. A failed part stops the command and keeps its run folder. Worksheet source collection reuses matching filing text already saved by the team.

For an offline replay check, run:

```powershell
.\.venv\Scripts\python.exe scripts\replay_offline.py ".\one_desk_runs\YOUR_TICKER_<timestamp>"
```

It blocks socket and DNS calls, requires the saved final report to match the replay output, and writes a proof JSON and output capture in the run folder.

The integrated command completed a live COST run on November 16, 2026, and offline replay passed. COST was absent from the seeker registry, so the spinoff worksheet path correctly reported `not applicable` and checked zero Form 4 filings. The team, worksheet, and hook took 183.16, 4.19, and 0.10 seconds. The final report lists the 10-K, 10-Q, and 8-K it read on its first line. The hook passed, and the Lab 05 page loaded the saved run's report and worksheet.

The pipeline completed, but the report needs review before use: its verifier output has 14 unsupported marks and 23 correct marks. Worksheet market prices and reader data were unavailable, so related comparisons are `not computed`. Replay the saved run with the command above; replay does not fetch filings.

A VYLR ticker run also completed in `one_desk_runs/VYLR_2026-11-16_16-56-52_060202_-0500/`. The final report's first line lists the 10-Q, 8-K, and Form 10 accessions. The worksheet reused the saved 8-K. VYLR was absent from the selected seeker registry, so spinoff fields were `not applicable`, while the team and worksheet continued. The saved team report is included unchanged; it does not contain numeric counterparts for the worksheet's historical amounts. Two worksheet inputs were checked against the Form 10: USD 575 million net income at line 19762 and USD 806 million depreciation at line 19990. These are historical Seed Business combined-statement figures, not post-spin standalone results.

The later VYLR run in `one_desk_runs/VYLR_2026-11-16_20-17-13_428177_-0500/` also passed replay while socket connections and DNS lookups were blocked. Its saved replay proof records the report hash and confirms there were no network attempts. A copy with after-tax earnings changed from 575 to 576 USD millions was refused at final-report line 116: `576 is not in VYLR_Form 10_0001193125-26-396054.txt, Combined Statements of Operations`. The original report was unchanged. The copied report and hook output are saved in that run folder.

Screen progress streams to the terminal. The seeker retries truncated SEC responses up to three total attempts and prints a retry notice. If all attempts fail, it stops and keeps the run folder. After the ranking-reader updates, a complete screen inspected registrant 170 of 170 in 2,375.44 seconds and returned no ranked name. Vylor remained in-window but unranked because size and insider inputs were unavailable. The report and registry are saved in `one_desk_runs/SCREEN_2026-11-16_20-16-45_506614_-0500/seeker/`. The saved Vylor data gives 667,303,030 shares as of November 5, filed November 12; USD 71.80 close on November 16; estimated market cap USD 47,912,357,554; and expected insider ownership of about 0.1385% from 924,111 / 667,196,000. The insider figure is a pre-spin expectation dated August 31, not verified current ownership. All 136 seeker tests passed.

If the seeker completes and its ranked section says `None established.`, pick, agent team, and worksheet are marked `not applicable`. The first complete 170-registrant screen reached that branch but then failed while finalizing. Its saved SEC outputs were kept. Finish that saved screen without running the seeker again with `.\.venv\Scripts\python.exe one_desk.py --finish-empty-screen ".\one_desk_runs\SCREEN_2026-11-16_20-16-45_506614_-0500"`. The command writes the filing list, final report, and successful `run.json`, then applies the hook. The recovered run passed offline replay with zero network attempts; its proof is `replay-offline-proof.json` in the same folder.

The older team-only command remains available for a stand-alone run:

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

Run the standalone seeker from PowerShell with a distribution start date. The joined desk's `screen` option runs it with the configured window. To run the seeker by itself:

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

The local Week 4 reports for Shlok (TTWO/VYLR), Sam (Sagard/HONA), and Ryan (LCID/REZI) are under `runs/live/`; the folders disclose missing figures and late filing windows. No commit or push was made. Lab 07 pre-work is in the repository. The worksheet skill is `.agents/skills/us-spinoff-worksheet/`; its `SKILL.md` gives the source-collection, LSEG reader, calculation, save, validation, and hit-rate-table commands. The input rules are in `docs/lab07_worksheet_rules.md`, and the qualitative persona is `personas/investment_advisor.md`.

The seeker close reader now also returns daily share volume. Its official reader requires listing evidence and an exchange spot check; its candidate reader is explicitly unverified. The worksheet hook definition is configured in `.codex/hooks.json` and has been trusted. A live PostToolUse check blocked an altered worksheet and allowed the corrected copy. A live Stop event with an erroneous worksheet has not been observed.

The worksheet values owner cash flow as equity directly because the course formula starts with after-tax earnings. Do not call that result firm or enterprise value, or add cash and subtract debt from it. Report cash, debt, and liabilities as separate sourced facts. The rules file contains the formulas, thresholds, missing-data behavior, and conviction conditions.

The Vylor team run and a dated worksheet now exist. The latest is [the Vylor worksheet](equity_research_runs/Vylor_Inc_2026-11-14_01-08-41_219149_-0500/worksheet-20261114-025135-330558.md). It includes pro forma financing assumptions and conditional separation obligations, but diluted share counts and several filing facts remain unestablished; affected per-share values and the Take-Two live view remain `not computed`. The Vylor research report's verifier recorded unresolved unsupported and incorrect claims, so review its sources before relying on it.

LSEG bars were obtained with `TR.CLOSEPRICE(Adjusted=0)` under the user's stated interpretation of that field. The report discloses that an independent exchange-price comparison was not completed. The local files in `%TEMP%` are licensed reader data and are not included in the repository. Vylor volume is from the selected NYSE instrument, not necessarily consolidated market volume.

For the live hit-rate table, run `.\.venv\Scripts\python.exe .\.agents\skills\us-spinoff-worksheet\scripts\hit_rate_table.py --runs ".\runs\live"`. For practice, replace the folder with `.\runs\practice`. The command rereads available reader files but does not refresh them; keep one view record per run folder. The saved Take-Two release is a practice record marked `after`, with a view of `not computed`. The Week 11-16to11-22 folder now contains a TSN view, but it was recorded 32.94 hours after filing and after the first post-filing close, so it is not a qualifying 24-hour event-window observation.

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
| `one_desk.py` | Joined desk command, fixed pipeline, saved-run replay, and hook checks |
| `desk_flow.py` | Main command-line workflow |
| `equity_research_data_desk.py` | SEC data collection; also supports individual steps from the command line |
| `research_analyst.py` | Separate research agent for supplied source text |
| `equity_desk/` | Supporting modules for roles, calculations, filing excerpts, and verification |
| `scripts/` | Extra utilities, including the legacy environment check |
| `roles/` | Role instructions used by the workflow |
| `tests/` | Local tests |
| `docs/` | Guides, prior reports, and reference material |
| `equity_research_runs/` | Saved desk runs |
| `one_desk_runs/` | Saved joined-desk runs, seeker inputs, team run, worksheet, and final report |
| `verifier_trials/` | Saved verifier trials |

New generated runs and trials are ignored by Git; files already tracked remain tracked. The desk is a prototype: its verifier does not check every possible numerical claim, and its model only sees selected filing excerpts. Review the report and its sources independently. A recommendation is not evidence of future investment performance.
