---
name: us-spinoff-seeker
description: Find and screen U.S. corporate spinoffs using SEC filings, a start date, user scoring rules, and LSEG Workspace closes.
---

# U.S. spinoff seeker

Run the seeker with the start date, the user's factor file and `.env`. The default command reads SEC indexes and filing folders, searches parent filings, saves a provenance registry, fetches LSEG closes when Workspace is available, and writes a dated report. The user chose to use `TR.CLOSEPRICE(Adjusted=0)` and a primary regular-way RIC without further verification. Preserve the report's statement that regular-way identity, exchange-close semantics and completeness are based on those user-supplied assumptions. Do not substitute guessed values when data or symbol mapping is unavailable.

The current filing extractors cover limited formats and can miss names and facts. The default search starts with the year before the requested distribution start, so the report names the earlier registration history not searched. Set `--index-from 1994` to search available earlier indexed registrations, accepting the longer runtime. Filing read failures, absent facts, missing prices and missing active factor inputs must remain explicit; do not claim exhaustive discovery. The analyst factor is disabled in the user's configuration. Preserve the exact final line `screens, not recommendations`.

Use the SEC User-Agent from `.env`, the built-in rate limit and only SEC hosts. Keep licensed raw pulls and credentials out of the repository and prompts. Use the user's provided window, weights and thresholds, print actual dates for prices, and show unranked names with reasons. The first selected price is the first returned close strictly after distribution under the user's supplied LSEG assumptions.

From the project directory, run (replace the date):

```powershell
& "$env:USERPROFILE\.codex\venvs\us-spinoff-lseg\Scripts\python.exe" .\.agents\skills\us-spinoff-seeker\scripts\seeker.py --start 2026-01-01 --config .\spinoff_factors.json --env .\.env --output .\spinoff_runs
```

Test the skill:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s .\.agents\skills\us-spinoff-seeker\scripts -p "test_*.py"
```

The local desk page uses the same command. `--partial` retains a bounded diagnostic mode; `--max-registrants` sets a sample limit. For the optional evidence-backed price path, see [lseg_official_reader.md](references/lseg_official_reader.md). Change synthetic tests before changing rules.
