---
name: us-spinoff-worksheet
description: "Build a sourced Lab 07 investment worksheet from a saved agent-team run, SEC filings, the seeker's registry, the local worksheet rules, and verified close and volume data. Use it when preparing a spinoff worksheet or checking one of its numeric claims."
---

# U.S. Spinoff Worksheet

Use this skill to prepare a Lab 07 worksheet from a saved company run. Keep the selected ticker generic. Do not put a company name in code or assume that an example company is the selected ticker.

## Automated command

From the project root in PowerShell, substitute the saved run and reader-file paths:

```powershell
.\.venv\Scripts\python.exe .\.agents\skills\us-spinoff-worksheet\scripts\run_worksheet.py --run "<worksheet-run-folder>" --live-run "<live-release-run-folder>" --registry ".\spinoff_runs\registry-2026-11-13_22-39-11_137090_-0500_ddc00b3d.json" --env ".\.env" --bars "<worksheet-bars.json>" --live-bars "<live-release-bars.json>"
```

The saved runs need `facts.json`, `filings.json`, and the saved filing text. The `.env` needs `SEC_USER_AGENT` and `PURDUE_API_KEY`. Reader files must be output from the verified regular-way closes and volume reader and stay outside the repository. Use the same-company form without `--live-run` and `--live-bars` when the worksheet and release are for the same ticker. Omit a missing bars argument to produce `not computed` for the corresponding price and view. `--release-accession` selects an 8-K; otherwise the most recent saved 8-K with Item 2.02 is used. If its SEC acceptance time is unavailable, the pre-release price and view stay `not computed`.

The command saves an SEC source pack and a dated worksheet in the saved run, calculates in Python, and makes one Purdue model request for the qualitative judgment. Its filing-text extraction is conservative and supports limited statement and narrative formats. It identifies unsupported or ambiguous facts as not established, rather than claiming the filing does not contain them. It does not establish that all covenants or restrictions have been found. The staged numeric-claim hook uses a separate marked draft format; the automatic renderer's output has not been integrated with that guard.

The sections below document the individual helper workflow and the marked-draft format. They are not additional model calls required by the automated command.

## Scope and inputs

- Read `lab07_worksheet_rules.md` before extracting or calculating a fact. Treat it as the source for client size, periods, units, valuation rates, liquidity lookback, conviction, and missing-data rules.
- Use one saved agent-team run. It must contain `facts.json`, `filings.json`, and saved filing text. The ticker must match the run.
- Use the seeker's registry file. A CIK entry in the registry means the company is registry-present, even when all facts in that entry are blank. Use `not known` for missing fields. Use `not applicable` only when the CIK entry is absent.
- Read the user's `personas/investment_advisor.md`. Read it as qualitative guidance. The worksheet rules file controls the calculations and output.
- Use the closes reader's dated close and share volume. Accept scoring inputs only from an official, unadjusted, regular-way primary listing. Never use when-issued observations.
- Save source documents and the final dated worksheet beside the saved run. Keep raw licensed LSEG history outside Git and out of model context.

## Source collection

First save the required SEC source documents beside the run. This command reads the saved run, uses the SEC User-Agent in `.env`, and uses the seeker's SEC client, which pauses requests to remain within its 5-request-per-second limit:

```powershell
python .\.agents\skills\us-spinoff-worksheet\scripts\prepare_worksheet.py --run "<saved-run-folder>" --ticker "<ticker>" --registry ".\spinoff_runs\<registry-file>.json" --env ".\.env"
```

If the live release belongs to another ticker, also pass `--live-run "<saved-release-run-folder>"`. Use `--release-accession "<accession>"` to select a specific release 8-K.

The command only collects sources. It does not create a worksheet, calculate values, or call a model. It saves the Form 10 folder and its exhibits by the registry's filing accession when the CIK is present. It also saves the parent's distribution 8-K from the registry evidence, the first company 10-K or 10-Q after the recorded distribution date, the latest available parent 10-K/10-Q after the spin, the selected live-release 8-K folder, and transaction code `P` rows from Form 4 filings in the saved run's filing list. The live release manifest includes the SEC acceptance time when the SEC submissions file provides it. Review `sources.json` and preserve every listed retrieval gap. If the CIK is absent from the registry, the command does not fetch spinoff filings.

Read these sources:

1. The Form 10 and the information statement in its folder, when the company is registry-present.
2. The first available 10-Q or 10-K after the spin, from the selected run and its saved SEC filing data.
3. Form 4 transaction tables. Count transaction rows with code `P` only. Do not count grants, vesting, gifts, or Form 4 filings as purchases.
4. The parent's filings after the distribution, when the registry provides a parent CIK and distribution date.
5. The saved release filing for the live-view company. Use `sources.json` -> `live_release.filing_time.value` for its SEC acceptance time. A filing date without an acceptance time is not a filing time.

For an official LSEG history, first record listing evidence from the filing and a dated close from the listing exchange. Then run this reader. It checks the listing sentence on EDGAR, checks the active LSEG quote, checks the exchange spot value, and writes the bars outside the repository:

```powershell
python .\.agents\skills\us-spinoff-worksheet\scripts\read_workspace_bars.py --env ".\.env" --evidence "<listing-evidence.json>" --start "<YYYY-MM-DD>" --end "<YYYY-MM-DD>" --output "$env:TEMP\<ticker>-bars.json"
```

Run it once for the worksheet ticker and, when different, once for the live-release ticker. Keep each output file outside Git. The seeker reference `../us-spinoff-seeker/references/lseg_official_reader.md` describes the evidence fields and reader limits.

## Facts and source labels

- Write one fact per line. Include amount or value, currency and unit, period, reporting tag, filing, section, and line when the saved filing has stable numbered lines.
- Use only `historical`, `pro forma`, or `reported after the spin` as reporting tags.
- Use whole USD for dollar calculations. State when the filing reports a different scale and show the scale conversion.
- Do not infer that an absent or unreadable fact equals zero. Write `not known` and state the missing source or input.
- Keep cash, debt, liabilities, restrictions, debt raised, and cash use as separate sourced facts. Do not use a model to calculate or fill any value.
- For registry facts, show the registry filing and section beside the parent, distribution ratio, record date, and distribution date. Do not replace blank registry facts with a guess from a different source.
- For Form 4 data, state the date range covered by the saved filing list. Keep the source accession and XML document for each code-P transaction.

## Calculations

Prepare an input JSON object using the schema in `references/input-schema.md`. Each financial amount must include its tag, period, filing, and section. Each close must include its date and reader source. Put the 20 dated bars used for liquidity in the input object.

Run the deterministic calculator. It does not call a model:

```powershell
python .\.agents\skills\us-spinoff-worksheet\scripts\worksheet_math.py --inputs "<run-folder>\worksheet_inputs.json" --rules ".\lab07_worksheet_rules.md" --output "<run-folder>\worksheet_calculations.json"
```

Show the printed inputs and formulas for owner cash flow, low and mid equity value, both per-share values, margin of safety, each daily dollar volume, and the 20-day median. The course formula is after-tax earnings + depreciation - capital spending. Capitalize owner cash flow directly as equity value under the rule file. Do not add cash or subtract debt a second time. If a required amount, diluted share count, dated close, or volume is missing, print `not computed` for the affected result and name the gap.

## One qualitative model call

Make exactly one model call for the investment-advisor judgment. Use the persona file and give the call only:

- Sourced filing facts and their labels.
- The low and mid values and the calculations already produced by `worksheet_math.py`.
- The dated market price and its comparison with the low case.
- The relevant debt, restrictions, parent liabilities, and not-known items.

Do not include a raw price or volume series, reader data, or unsourced claims in the model call. Ask for two short parts only: why the company may be cheap or why the spinoff explanation does not fit; and the exact evidence in the next filing that would change the view. Do not ask the model to calculate, estimate, or make a Buy/Hold/Sell recommendation. Put the liquidity section after the call in code-generated text.

## Required worksheet output

Write the worksheet in the order from `lab07_worksheet_rules.md`:

Start the first line with the filings read. Include the live-release filing on that line.

1. Parent, distribution ratio, record date, distribution date, dated price.
2. Why the company may be cheap, or why the spinoff explanation does not fit.
3. Owner cash flow with inputs, arithmetic, and low and mid value range.
4. Debt raised, use of proceeds, liabilities, and restrictions left by the parent.
5. Parent after the spin.
6. Insider purchases with code `P` only.
7. Client purchase size, the 20 daily dollar volumes, and median liquidity result.
8. Every not-known fact or input.
9. Live-release view, deciding number and source, conviction, and the exact next-filing evidence that would change the view.

When the required close is unavailable, set the price, view, and conviction to `not computed` as required by the rule file. Do not conceal missing filing, registry, reader, or model inputs.

For the hook to verify numbers, use one numeric claim per line and add one marker at the end of each numeric line. Use these markers:

- `[fact concept=net_income period=FY2026 tag=historical filing="10-K accession" section="Consolidated Statements of Operations" source_file="worksheet_sources_<stamp>/10-K_<accession>_<document>.txt" line=123]` for an exact numeric value in `facts.json` and, when a saved text line is available, its filing.
- `[filing file=relative/path.txt line=123 section="Consolidated Statements of Operations" tag=historical period=FY2026]` for a number visible on that exact saved filing line.
- `[rule id=low_discount_rate]` for a number set by the rules file.
- `[price ticker=XYZ date=2026-11-12]` for a close in the reader file.
- `[calc id=owner_cash_flow]`, `[calc id=low_equity_value]`, `[calc id=mid_equity_value]`, `[calc id=low_value_per_share]`, `[calc id=mid_value_per_share]`, `[calc id=margin_of_safety]`, `[calc id=daily_dollar_volume]`, or `[calc id=median_dollar_volume]` for a result that the hook recomputes from printed inputs.

Print calculation inputs under these exact labels so the hook can recompute them: `After-tax earnings`, `Depreciation`, `Capital spending`, `Owner cash flow`, `Low case discount rate`, `Low case growth rate`, `Low case equity value`, `Mid case discount rate`, `Mid case growth rate`, `Mid case equity value`, `Diluted shares`, `Low case value per share`, `Dated market price`, and `Median daily dollar volume`.

Print each liquidity row as:

```text
Liquidity bar: YYYY-MM-DD | dollar_volume=10000 [calc id=daily_dollar_volume ticker=XYZ reader=target]
```

Print exactly the configured 20 daily dollar volumes in ascending date order. Mark the median line as `[calc id=median_dollar_volume ticker=XYZ reader=target]`. The hook checks each amount against the dated close and volume in the reader file, checks that the dates are the latest 20 reader observations, then recomputes the median from the 20 printed daily dollar volumes. Use `reader=live` on a bar for the live-release ticker. The hook treats dates, CIKs, accessions, line numbers, and form or item numbers as identifiers. Any other number without a valid marker fails.

## Save and check

Save the draft and the live-view JSON beside the run. Use `save_worksheet.py`; it records the reader, rules, and run paths in the worksheet itself and writes `worksheet.json` for the read-only hit-rate table:

```powershell
python .\.agents\skills\us-spinoff-worksheet\scripts\save_worksheet.py --draft "<run-folder>\worksheet_draft.md" --run "<run-folder>" --rules ".\lab07_worksheet_rules.md" --reader "<target-bars.json>" --live-reader "<release-bars.json>" --live-view "<run-folder>\live_view.json" --output "<run-folder>\worksheet-YYYYMMDD-HHMMSS.md"
```

Check a saved worksheet before you call it complete:

```powershell
python .\.agents\skills\us-spinoff-worksheet\scripts\worksheet_guard.py --worksheet "<worksheet.md>" --run "<run-folder>" --rules ".\lab07_worksheet_rules.md" --reader "<reader-bars.json>"
```

The exact check command for a seeded copy is the same command with `--worksheet` set to the copy. Do not enable the lifecycle hook until you inspect its source and its staged `hooks.json`, then run the seeded-copy and clean-copy checks required by Lab 07.

## Hit-rate table

Keep live runs in `runs/live` and practice runs in another folder. Each saved `worksheet.json` must contain a `live_view` object with `ticker`, timezone-aware ISO `filing_time`, timezone-aware ISO `view_time`, `direction`, and `reader_file`. The table command reads saved runs only. It calculates reaction from the last close before filing to the first close after filing, marks a row `after` when the view time is later than the first post-filing close, and does not write to a view or timestamp:

```powershell
python .\.agents\skills\us-spinoff-worksheet\scripts\hit_rate_table.py --runs ".\runs\live"
```

The denominator excludes rows marked `after`, views marked `not computed`, and rows with no reaction. The table reports short-term price reaction only. It does not score whether the value range was right.

## Execution limits

`prepare_worksheet.py` collects sources only. Use `run_worksheet.py` for the automated workflow. Neither the conservative extractor nor a successful model response proves that every fact in a filing has been found. Review the saved sources and preserve gaps. The automatic worksheet and the staged hook need integration before the hook can validate that output.
