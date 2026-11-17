# Latest continuation — November 16, 2026: Lab 08 joined desk

The user asked to check the Lab 08 One Desk contract and update this handoff and `README.md`. The joined command is implemented in `one_desk.py`; the Lab 05 page now submits ticker or `screen` to it. The fixed order is seeker for `screen`, pick, agent team, worksheet, then hook. A ticker run uses the latest saved seeker registry. If its CIK is absent, the worksheet marks spinoff items `not applicable` and continues.

Runs are saved under `one_desk_runs/<TICKER>_<start-time>/`, with seeker files, team files, worksheet sources and output, final report, and `run.json`. The seeker saves `filing_reads.json`; the final report's first line combines those accessions with source filings in the team facts, team filing text, worksheet manifest, and seeker registry. The worksheet source collector reuses matching team filing text for Form 10, release, distribution, and first post-spin sources. It still fetches other required spinoff documents that the team did not save. No role currently consumes seeker or worksheet output, so the skill-output handoff rule does not apply to a role in this pipeline.

The hook checks the seeker report when present, validates the saved worksheet, and checks that the final report contains the verified team report and the exact worksheet text. Replay reruns these checks against saved files, prints the saved final report, and makes no filing requests. The worksheet hook false trigger was fixed: source inspection and `--help` no longer count as running the worksheet script.

For Lab 08 proof, `scripts/replay_offline.py RUN_FOLDER` runs the replay with socket connections and DNS lookups blocked. The November 16 VYLR run at `one_desk_runs/VYLR_2026-11-16_20-17-13_428177_-0500/` replayed successfully; `replay-offline-proof.json` records the saved report hash, exact-output match, and zero network attempts. To run the hook on an edited copy, save it inside its run folder and use `one_desk.py --check-copy PATH`. The hook now validates the worksheet section in a copy before checking exact equality, so it can name the changed amount's final-report line, source filing, and section. The VYLR seeded copy changed 575 to 576 and was refused at line 116; `seeded-copy-hook-output.txt` contains the refusal.

Commands from the project root:

```powershell
.\.venv\Scripts\python.exe one_desk.py YOUR_TICKER
.\.venv\Scripts\python.exe one_desk.py screen
.\.venv\Scripts\python.exe one_desk.py --replay ".\one_desk_runs\YOUR_TICKER_<timestamp>"
.\.venv\Scripts\python.exe one_desk.py --check-copy ".\one_desk_runs\YOUR_TICKER_<timestamp>\seeded-copy-final-report.md"
.\.venv\Scripts\python.exe one_desk.py --finish-empty-screen ".\one_desk_runs\SCREEN_<timestamp>"
```

End-to-end check completed on November 16, 2026, with `COST`. The run exited 0 and saved to `one_desk_runs/COST_2026-11-16_16-49-00_960078_-0500/`. Ticker-mode seeker and spinoff worksheet sections were `not applicable` because COST was absent from the registry; the worksheet manifest recorded `registry_present=false`, zero Form 4 filings checked, and no collection errors. The team, worksheet, and hook completed in 183.16, 4.19, and 0.10 seconds. The final report's first line lists all three filings read: 10-K accession `000090983226000093`, 10-Q `000090983226000051`, and 8-K `000090983226000084`. The hook passed.

Offline replay of that saved run exited 0, printed the saved report, and passed the hook without fetching filings. The Lab 05 page returned HTTP 200; its saved-run list found this run and loaded the report and worksheet. This confirms the integrated COST path and replay. It does not establish clean research conclusions: `verifier_output.json` records 14 unsupported marks and 23 correct marks, and worksheet market prices and reader data were unavailable, so related comparisons remain `not computed`. Review the report before relying on it.

An earlier COST attempt exposed a bug that caused Form 4 collection for an unregistered ticker. The collector now skips Form 4 collection unless registry presence and a distribution date are established. The two interrupted attempt folders were retained, as required by the run-folder contract; use the completed run above for replay.

The VYLR known-answer run completed in `one_desk_runs/VYLR_2026-11-16_16-56-52_060202_-0500/`. Its final report starts with the 10-Q accession `000212862626000012`, 8-K `000212862626000009`, and Form 10 `000119312526396054`. `sources.json` records the live-release 8-K as a reused saved filing. The worksheet manifest records `registry_present=false`; spinoff fields were `not applicable`, while the team and worksheet completed. Timings: pick 0.00s, team 252.09s, worksheet 4.85s, hook 0.25s. The team verified report is included in the final report; it has no numeric counterpart for the worksheet's FY2025 amounts, so direct numeric equality between those sections was not established. Two worksheet inputs were checked against the saved Form 10: USD 575 million net income at line 19762 and USD 806 million depreciation at line 19990. These are historical Seed Business combined statements, not post-spin standalone results.

The VYLR replay passed with Python socket connects and DNS lookups blocked; it printed the identical saved report. A separate copied report with after-tax earnings changed from 575 to 576 USD millions was refused at worksheet line 19 (Form 10 line 19762); the dependent owner-cash-flow calculation was also refused at line 23. The original report remains unchanged. The saved copy is under `hook_seeded_copy/` in the VYLR run folder.

The latest complete seeker scan inspected registrant 170 of 170 in 2,375.44 seconds and produced no ranked name. Vylor remained in-window but unranked because the screen had no size or insider inputs. Its report, registry, and filing-read log are under `one_desk_runs/SCREEN_2026-11-16_20-16-45_506614_-0500/seeker/`. All 136 seeker tests had passed after the share-count and insider-reader changes.

The earlier transient SEC `IncompleteRead` is also addressed: `one_desk.py` streams subprocess output, and the seeker retries an incomplete SEC response up to three total attempts. If all attempts fail, the command stops and preserves the run folder. Two focused synthetic retry tests passed.

## November 16, 2026 — empty-screen handling

`one_desk.py` treats an explicit empty ranked section (`None established.`) as a normal outcome. The first full screen reached this branch, marked pick, team, and worksheet not applicable, then failed during finalization with `TypeError: unsupported operand type(s) for /: 'NoneType' and 'str'`. The seeker report, registry, and filing-read log were preserved. The finalization code is now a reusable local-only function. Run `one_desk.py --finish-empty-screen RUN_FOLDER` to complete a saved empty screen without rerunning the seeker. It creates `pick.json`, the final report, and successful `run.json`; its hook checks the exact seeker report and filing list. The saved run `one_desk_runs/SCREEN_2026-11-16_20-16-45_506614_-0500/` has now completed this path, and offline replay passed with zero network attempts. Future failures save a traceback and name the failing hook part.

# Latest continuation ? November 14, 2026: three local weekly reports completed

The user asked for local files and folders only. No commit or push was made. The reporting week is November 9?15, 2026. Each member folder under `runs/live/` has a `report.md`, `run_info.json`, saved team output or fund evidence, verifier output where available, and a worksheet plus its `worksheet.json` index.

- **Shlok ? Take-Two (TTWO) / Vylor (VYLR):** `runs/live/Shlok_TTWO_VYLR/`. The new worksheet is `worksheet-20261114-182151-280352.md`. Its saved view time is 18:21:51 Eastern on November 14. The original worksheet and its 02:51:35 Eastern view record remain saved; its JSON was renamed `worksheet-original-view.json`, and the live index points to the newer view. The view is `not computed`; the Take-Two price reaction is +8.31% and the view is `after`. Vylor diluted shares remain unknown, so per-share values and price comparison remain not computed. This is late against the 24-hour course rule.
- **Sam ? Sagard Private Income Fund Inc. / Honeywell Aerospace (HONA):** `runs/live/Sam_Sagard_HONA/`. Sagard is not exchange-listed and has no price reaction. The saved Form D was accepted November 10 at 16:17:15 Eastern; the local report was created after its November 11 16:17:15 deadline. The worksheet uses the HONA Form 10 and the selected Sagard Form D. HONA separated June 29, 2026, 138 days before the analysis date, outside the 90-day window. The listed-company desk was not used for Sagard because it is unlisted. The separate fund role review has 65 unresolved verification issues; do not treat it as a verified conclusion.
- **Ryan ? Lucid Group (LCID) / Resideo (REZI):** `runs/live/Ryan_LCID_REZI/`. The selected weekly filing is Lucid Form 4 accession 000162828026073829, accepted November 13 at 16:10:11 Eastern. Its 24-hour deadline was November 14 at 16:10:11 Eastern. Local files were created after that deadline, so this is late. The reaction and view are not computed because the reader has no post-filing close. REZI separated in 2018, outside the 90-day window; diluted shares and per-share values remain unknown.

The three worksheets passed the direct saved-worksheet number guard. The hit-rate command is:

```powershell
.\.venv\Scripts\python.exe .\.agents\skills\us-spinoff-worksheet\scripts\hit_rate_table.py --runs ".\runs\live"
```

It shows one observed reaction, but that view is marked `after`; agreements remain 0/0. It shows `not computed` for the unlisted fund and for Lucid because no post-filing close is available. LSEG closes still use the user's interpretation of `TR.CLOSEPRICE(Adjusted=0)`; no independent exchange-price comparison was completed, and segmented venue volume may not be consolidated market volume. The reports are local artifacts only and do not establish the course's commit-and-push record or 24-hour compliance.

# Latest continuation - November 14, 2026: hit-rate table and late release

The user requested the hit-rate table and the week's live report. The selected Take-Two release was accepted 2026-11-09 at 16:10:58 Eastern. The saved Vylor worksheet's Take-Two view was recorded 2026-11-14 at 02:51:35 Eastern, after the first available post-filing close, and its direction is `not computed`. The selected LSEG reader has a 2026-11-09 pre-release close of USD 207.40 and a 2026-11-10 close of USD 224.64, producing about +8.31%; the field interpretation is user supplied and no independent exchange comparison was completed. This is not a scoreable or timely live view. The Take-Two report contains unsupported and wrong verifier marks. Do not backdate a view, claim the report passed cleanly, or label the retrospective record as timely.

The original `worksheet.json` was copied byte-for-byte with its original view and timestamp into `runs/practice/TTWO_20261109_after/`, with the saved report and worksheet and an explicit caution. No actual live run was created and no live report was committed; the requested pre-close window had passed. `runs/live/README.md` records that no qualifying live report has been filed. The original saved report and worksheet remain unchanged.

`hit_rate_table.py` now displays missing and ambiguous run records, preserves saved ticker/view/time when reader data is missing, checks a reader's root ticker, and displays the reason column. It rereads the existing reader file on each run without changing views or timestamps; it does not fetch new reader data. A folder should contain one subfolder per run and exactly one `worksheet.json` within each. It uses the first available reader close after filing; incomplete data can make that differ from the actual first close. The live command is `.\.venv\Scripts\python.exe .\.agents\skills\us-spinoff-worksheet\scripts\hit_rate_table.py --runs '.\runs\live'`; replace the path with `.\runs\practice` for practice. Practice output shows TTWO, `not computed`, `after`, and 8.31%; denominator 0/0. All 43 worksheet tests passed, including reaction-update, unchanged-record, missing/ambiguous-run, and late-view tests.

# Earlier continuation - November 14, 2026: factor-check ownership start

The user asked to choose the easiest Lab 07 ownership option and record it as the team's choice. The team chose the spinoff factor check. The README has one ownership line. `docs/factor_check_protocol.md` specifies a single proposed comparison and an initial historical design using the existing factor thresholds; its dates, holding period, benchmark, eligibility and point-in-time requirements are design choices, not established results. The protocol does not claim the team has never seen historical returns or that an external preregistration occurred. Freeze a final version before accessing the selected historical returns, record later changes, and count all additional comparisons.

`scripts/factor_check_demo.py` runs only synthetic data and makes no network request; it demonstrates the score, missing-input exclusion, benchmark-adjusted return and one group comparison. The demo ran and three focused tests passed. No historical factor check, WRDS connection, corporate-action or delisting handling, or investment finding is complete. The run command is `.\.venv\Scripts\python.exe scripts\factor_check_demo.py`.

# Earlier continuation - November 14, 2026: live post-tool hook check

The user requested the Lab 07 seeded-error test. Created `seeded-vylor-worksheet.md` beside the clean marked worksheet and changed after-tax earnings from 575 to 576 USD million. The direct guard refused line 21 (amount absent from filing line 19762) and line 26 (owner cash flow mismatch); the clean worksheet check returned exit code zero and no output. Presented the seeded path as `run_worksheet.py` output through an actual Codex tool call. The trusted PostToolUse hook fired, blocked the tool result, and returned both lines plus the instruction to fix them before finishing. Restored the seeded copy to 575, checked it directly, and presented it again; the live post-tool hook allowed the clean copy. The original worksheet was not changed. `seeded-vylor-worksheet.md` is now corrected, not intentionally wrong.

This demonstrated a real trusted PostToolUse event, not merely a simulation. It did not observe a live `Stop` event while the worksheet was erroneous: the hook's returned instruction required repair before this turn could finish. The earlier clean and altered Stop checks were simulations. Keep this distinction and retain the guard's source-tag, period, unit, source-column, semantic-context, and spelled-number limitations.

# Earlier continuation - November 14, 2026: hook configured, trust pending

The user explicitly asked to enable the worksheet hook. Copied the previously presented staged definition byte-for-byte to `.codex/hooks.json`; it configures `PostToolUse` for Bash and `Stop`, both invoking `.agents/skills/us-spinoff-worksheet/hooks/worksheet_hook.py`. The project config exists, but Codex requires the user to review and trust this exact non-managed definition before it runs. Trust has not been observed and the actual trusted lifecycle has not been tested; do not claim the hook is active. The source checker still does not independently verify every filing tag, period, source column, unit, semantic context, or spelled-out number.

Simulated real hook events against the marked Vylor worksheet: clean PostToolUse and Stop did not block, while changing the earnings input from 575 to 576 USD million caused both events to return `decision: block`, with the failed line and calculation. The altered copy was temporary. This is a simulation, not a trusted live Codex lifecycle test. README and worksheet skill documentation now reflect configuration and outstanding trust. See https://learn.chatgpt.com/docs/hooks.

# Earlier continuation - November 14, 2026: generator uses marked format

The user asked to change the worksheet generator. `run_worksheet.py` now uses `marked_worksheet.py` to render separate numeric claims and guard markers, including source filing lines, rule values, reader bars, calculations, and Form 4 code-P rows. It writes a temporary rendered file, runs the direct guard, and only then moves it to the dated worksheet path. It still makes one qualitative model request. The staged hook is not enabled and a format pass is not complete semantic verification: filing tag, period, source column, units, context, and all spelled-out numbers are not independently verified. Review sourced facts and qualitative output.

A dry run used the saved Vylor and Take-Two filing packs and LSEG reader files with a stub qualitative judgment, not a new model or team call. The rendered temporary copy had no direct guard failures; changing Vylor earnings from 575 to 576 USD million produced filing-line and cash-flow failures. The Vylor owner cash flow remained USD 1.035 billion. All 39 worksheet tests passed. The latest reviewed worksheet was not overwritten; the generator will include only facts found by its automatic reader, so it does not automatically preserve all manually reviewed additions in the marked copy. The direct guard still needs lifecycle tests and the unresolved semantic/source checks before enablement.

During the real-data test, a copied Take-Two 10-K inside the Vylor source pack contaminated Vylor's automatic financial selection. The copied file was removed; the marked Vylor worksheet now references the saved Take-Two run directly. The fetched Take-Two 10-Q copy was renamed with a `live_` prefix, and annual extraction now limits named issuer sources when the ticker is known. The regression suite covers an unrelated issuer filename. Do not claim this filename filter proves all possible cross-company contamination is impossible. Reader limitations and missing diluted shares remain unchanged.

# Earlier continuation - November 14, 2026: marked Vylor worksheet copy

The user asked to make the worksheet use the guard format. Created `equity_research_runs/Vylor_Inc_2026-11-14_01-08-41_219149_-0500/worksheet-20261114-131000-marked.md` as a separate, manually reformatted copy; the existing original and reviewed worksheet were not overwritten. Numeric claims are separated and carry filing, reader, rule or calculation markers. The guard supports the printed USD-millions inputs and the magnitude of a negative cash-flow outflow, and checks the two indicated source number words. The Take-Two 10-K text was copied into the existing source pack, and its June 2026 10-Q was fetched from EDGAR into that pack to support the pre-release cover share count. The page's saved-run selector now chooses the marked copy as the latest worksheet.

A direct clean check of this marked copy returned exit code zero with no output. A copy in `%TEMP%` with after-tax earnings changed from 575 to 576 was rejected on its filing line and its owner-cash-flow calculation. The worksheet suite passed 36 tests. These checks do not prove full hook compliance: the automatic renderer was not changed and still emits the old format; reporting tag, period, source column, unit scale, and semantic context are not fully verified for filing markers; the current guard does not detect every spelled-out number; and enabled lifecycle tests remain outstanding. Do not enable or claim the hook is complete. The hook remains staged. Price caveats and the missing diluted share counts remain unchanged.

# Earlier continuation - November 14, 2026: further hook hardening

The user asked to make all changes needed to prepare the hook for enabling. The hook is still not ready. `worksheet_guard.py` now requires a fact marker's XBRL tag, reporting tag, filing accession, and FY period to match its saved facts entry. It fails closed when `reporting_tag` is absent; existing saved runs usually lack that field. It now persists a failed state when a worksheet writer does not provide a usable output path, so the subsequent Stop check does not silently pass. It also detects numbers directly followed by text and rejects unsupported scientific notation. Synthetic tests cover these behaviors; the complete worksheet suite passed 34 tests. `SKILL.md` documents the stricter fact marker.

The existing renderer is still incompatible with the guard. The real reviewed Vylor worksheet has not passed a clean check, and a seeded real copy has not been checked. An evidence-backed approach is needed for reporting tags and source amounts expressed in millions; do not populate or infer tags in `facts.json` merely to pass the hook. End-to-end lifecycle behavior for an actual rendered worksheet and the live reader still needs testing. The staged hook remains disabled, and there is no project `.codex/hooks.json`. The user explicitly wants to review the exact definition before enablement.

# Earlier continuation - November 14, 2026: hook guard review

The user requested the worksheet hook and asked to see its file before enabling it. The staged configuration and source remain at `.agents/skills/us-spinoff-worksheet/hooks/hooks.json`, `hooks/worksheet_hook.py`, and `scripts/worksheet_guard.py`; no project hook was enabled. The guard now checks numbers in visible Markdown link text, does not discard an ordinary number at the beginning of a line, removes whole URL identifiers before other identifier patterns, prints the failing worksheet line, and returns valid empty JSON on a clean or unrelated Stop. New tests cover clean/changed marked synthetic lines and these parsing cases. These focused checks are not a clean/seeded validation of the actual worksheet.

Directly checking `worksheet-20261114-125500-reviewed.md` still fails because the worksheet renderer and manually reviewed copy lack the guard's required one-number-per-line markers; several source values also need careful handling of scale and filing lines. The guard currently does not establish that a requested reporting tag actually matches a saved fact's provenance, and lifecycle coverage must be verified for the actual writer and tool path. Do not enable or claim completion. Integrate and validate the real renderer with exact source/period/tag matching, then run clean and altered-number checks on a real saved worksheet before requesting review and trust. Official documentation: https://learn.chatgpt.com/docs/hooks.

# Earlier continuation - November 14, 2026: diluted share review

The user asked to establish diluted shares and complete the Vylor per-share valuation and Take-Two live view. Reviewed the saved filings and the pre-release Take-Two June 2026 10-Q. Vylor's 10-Q management discussion has a line called diluted shares outstanding, but it is part of a Corteva EPS reconciliation and refers to period averages, not Vylor point-in-time diluted shares. Take-Two's 10-Q filed August 7 reports 186,980,443 common shares outstanding as of July 27, 2026, not diluted shares. Its FY2026 10-K describes diluted weighted-average shares and excludes potentially dilutive awards due to the loss. Do not substitute either for point-in-time diluted shares or use the later same-day Take-Two 10-Q as a pre-release source. The latest worksheet `worksheet-20261114-125500-reviewed.md` records this review and keeps the affected values and live view not computed. To calculate with a proxy would require an explicit change to the user's existing share-count rule. The live report's original timing and other completion gaps do not become satisfied by a later reconstruction.

# Earlier continuation - November 14, 2026: worksheet page and source review

The user requested Lab 07 step 2. The existing Vylor team run and original model-generated worksheet were reused; the team and model were not rerun. A new reviewed copy, `equity_research_runs/Vylor_Inc_2026-11-14_01-08-41_219149_-0500/worksheet-20261114-030000-reviewed.md`, removes the model's unsupported claim that low-case per-share value exceeds price, and identifies the text as an editorial correction. It adds actual October 1 credit-facility borrowing and use, the approximately $761 million cash distribution subject to adjustment, and a 0.60 credit covenant with filing sources; these are separate from the earlier pro forma assumptions. Diluted shares, per-share valuation and the live view remain not computed. Additional filing review is still needed, the report has unresolved verifier flags, and the numerical guard has not validated the worksheet. Do not claim Lab 07 step 2 is fully verified.

The project page now offers a saved-run selector, which opens the matching report and latest dated worksheet together. The report warns users to review verifier marks. `run_worksheet.py` now tells the model not to imply a price comparison when the per-share comparison is missing; the qualitative output still requires review. The skill documentation now distinguishes the authorized user-asserted LSEG reader from the strict independently checked path. No independent price comparison was completed. The hook remains incomplete and disabled. The underlying seeker and report limitations remain as described below.

# Earlier continuation - November 14, 2026: worksheet facts and hook progress

The user asked to complete the missing worksheet facts and finish the hook, then asked to save progress here. Both tasks are still incomplete. The latest worksheet is [worksheet-20261114-025135-330558.md](../equity_research_runs/Vylor_Inc_2026-11-14_01-08-41_219149_-0500/worksheet-20261114-025135-330558.md). The Vylor team run and separate Take-Two live-release run both exist. Vylor's report has unresolved verifier flags described below; do not treat its name `verified_report.md` as proof that all claims passed.

`worksheet_evidence.py` now reads two pro forma assumptions from the registry Form 10 information statement: $5.558 billion of assumed principal indebtedness, net of applicable issuance costs, and an expected $3.499 billion cash distribution to the former parent. It also records a conditional tax indemnity whose amount is not stated and conditional restrictions on certain transactions for two years following the distribution. The filing was dated September 21, 2026; these are assumptions or expected arrangements, not established final outcomes. The cash distribution is not labeled as debt proceeds, since the cited sentence does not establish that connection. Source URLs, sections, and lines appear in the worksheet. The current extractor remains format-limited; review the actual filings for additional debt, covenants, parent liabilities, restrictions, and parent-after-spin facts before calling the worksheet complete.

Take-Two FY2026 depreciation of $166.4 million was recovered from its 10-K cash-flow statement. The worksheet calculates owner cash flow as -$298.2 million + $166.4 million - $162.8 million = -$294.6 million. Its diluted share count was not established, so the live per-share value and view remain `not computed`. Vylor's 667,303,030 cover-page common shares are now labeled as common shares, not diluted shares. Do not reuse the previously printed $15.51 and $22.60 per-share values: diluted shares have not been established, so the current per-share values and price-versus-low-case comparison remain `not computed`. Do not invent diluted shares or confuse weighted-average diluted shares with shares outstanding.

The user authorized use of `TR.CLOSEPRICE(Adjusted=0)` and asked to skip long verification. LSEG Workspace opened in `C:\Users\Shlok Bairagi\.codex\venvs\us-spinoff-lseg\Scripts\python.exe`. `TR.OFFICIALCLOSEPRICE(Adjusted=0)` returned blank prices; the user-specified close field returned bars. The separate `read_user_asserted_bars.py` reader checked primary quote, exchange, and ordinary-share metadata and wrote `%TEMP%\vylr-bars.json` (32 bars, `VYLR.N`) and `%TEMP%\ttwo-bars.json` (6 bars, `TTWO.OQ`). These licensed files stay outside Git and may disappear when temporary files are cleared. Their `user_asserted_official_unadjusted` label records the user's field interpretation: no independent exchange-price comparison was completed. Vylor volume is for the selected NYSE instrument, not necessarily consolidated market volume. The current report prints the field and this limitation. The worksheet skill documentation still describes the stricter original reader and needs updating to describe the user-asserted reader accurately.

The staged `worksheet_guard.py` hook now recognizes a completed `run_worksheet.py` output and checks that its reported path is inside the run. It still cannot validate the automatic renderer: a direct check of the latest clean worksheet rejects multiple lines because the renderer lacks the guard's one-number-per-line markers. Do not enable or describe the hook as finished. Next, integrate the automatic renderer with the guard's source and calculation markers, run a clean-copy pass and a deliberately altered-number failure, then configure the project hook. Codex requires the user to review and trust the exact hook definition via `/hooks` before it can run; see https://learn.chatgpt.com/docs/hooks. No project `.codex/hooks.json` has been created yet.

Latest checks: 28 worksheet tests passed with `./.venv/Scripts/python.exe -m unittest discover -s ./.agents/skills/us-spinoff-worksheet/scripts -p 'test_*.py'`. A direct guard check of the clean latest worksheet failed as described above. One earlier worksheet rerun was rejected because the model returned digits; a subsequent single-call run completed. The latest worksheet's expected-cash-distribution label was corrected after rendering to avoid implying the filing had established the source of the cash; the renderer now uses that corrected label for future runs.

The user has not asked to put the worksheet on the project page in this turn. The ASD-STE100 rewrite is a user task and has not been verified. Update the README or this handoff if subsequent work changes these statuses. Older sections below are historical and may describe earlier states.

# Earlier continuation - November 14, 2026: Vylor team run completed

The user ran `desk_flow.py VYLR` and it stopped because Vylor has no 10-K. The desk now supports a registrant with a Form 10 registration, 10-Q, and earnings 8-K: it saves the Form 10 information statement under its actual form name, uses the 10-Q for interim research, and leaves annual 10-K facts and calculations unavailable when they cannot be established. It does not annualize quarterly values or relabel a Form 10 as a 10-K.

The 42 project tests passed. A real Vylor rerun completed, saved `facts.json` and `filings.json`, and produced [verified_report.md](../equity_research_runs/Vylor_Inc_2026-11-14_01-08-41_219149_-0500/verified_report.md). Its verifier recorded 9 unsupported and 6 wrong marks, including mismatched quoted lines; the final insight review also recorded unresolved issues. A completed run is not proof that its claims are reliable. Review the verifier output and sources before using the report. The user's first failed run remains in its separate folder.

# Continuation - November 14, 2026: worksheet command added

The user asked to complete the worksheet skill. `.agents/skills/us-spinoff-worksheet/scripts/run_worksheet.py` now connects SEC source collection, conservative filing-fact extraction, deterministic calculations, one Purdue model request, and dated worksheet output. It accepts separate saved runs and verified reader-bar files for the worksheet and live-release companies. When price data or a pre-release acceptance time is missing, the relevant view stays `not computed`. Annual financial inputs for a release are limited to filings dated before that release, preventing same-day or later filings from entering its view. The `SKILL.md` gives the command. The 19-test fake-data suite passed, and one separate live model check returned both required qualitative fields. No saved Vylor team run was found, so no Vylor worksheet was generated.

The extractor handles a limited set of statement and narrative patterns; an unsupported fact is explicitly reported as not established, not assumed absent. It does not establish complete coverage of covenants or parent restrictions. The generated worksheet does not yet use the staged hook's numeric markers, so the hook cannot yet validate this renderer's output. Do not imply that the actual Lab 07 report, hook activation, or seeded/clean checks are complete.

# Continuation - November 14, 2026: year-back seeker run finished

The user completed the year-back seeker run. Its [screen report](../spinoff_runs/spinoff-screen-2026-11-14_00-03-25_599158_-0500_8d9efe96.md) and [fact registry](../spinoff_runs/registry-2026-11-13_22-39-11_137090_-0500_ddc00b3d.json) were reviewed. The report states run date November 13, 2026, price date November 13, 2026, and index date November 12, 2026. The report does not record the requested start date.

The registry contains 236 CIK entries, four of which have at least one established fact. The report has no ranked names and no watch-list names. It lists Vylor Inc. as unranked because size and insider ownership are missing; its displayed close is $72.54 on November 13, 2026. The registry records Corteva as parent, a 1:1 ratio, September 24, 2026 as the record date, and October 1, 2026 as the distribution date, with filing sources. The report drops 44 registrants: 36 labeled funds and eight labeled as having no information statement. Those classifications were not independently audited during the review.

The report says registration indexes before 2024 were not searched and the filing extractor has limited coverage. Its data-limits section contains over 26,000 nonblank lines, mostly attachment-read issues; the report may miss names or facts. LSEG regular-way identity, exchange-close semantics, and historical completeness remain based on the user's stated assumptions, not independent verification. Do not present the run as exhaustive or the unranked Vylor entry as a scored pick.

# Continuation - November 14, 2026: Lab 07 pre-work is ready; actual lab not started

The user asked to complete the preparation work only, not perform Lab 07. The pre-work is now represented in the repository by `.agents/skills/us-spinoff-worksheet/`, `docs/lab07_worksheet_rules.md`, and `personas/investment_advisor.md`.

The seeker closes reader in `.agents/skills/us-spinoff-seeker/scripts/closes_reader.py` now returns daily close and share volume from export, candidate, and official Workspace reader paths. Candidate data is labeled unverified. The official reader requires filing-based listing evidence and an exchange spot check; do not treat a candidate-bars response as verified official close history. The reader's focused synthetic suite passed **24 tests**. Python syntax checks passed for the new worksheet scripts, and the staged hook JSON parsed successfully. A live LSEG candidate-bars query returned two rows for a generic instrument, which confirms field delivery only; it does not validate a real spinoff's official primary-listing series.

The worksheet skill covers SEC source collection, the Workspace bars reader, deterministic calculations, worksheet saving and checking, and the read-only hit-rate table. Raw licensed LSEG histories must stay outside Git and model context. The worksheet rule file was corrected so after-tax-earnings-based owner cash flow is capitalized directly as **equity value**. Do not call it firm/enterprise value or bridge cash and debt into it; report those as separate sourced facts.

The worksheet hook and its `hooks.json` are staged only inside `.agents/skills/us-spinoff-worksheet/hooks/`. They are **not enabled** in the project Codex configuration. Before activation, inspect the source/configuration, review and trust it, and run the seeded-copy and clean-copy checks required by Lab 07. Official Codex hook review guidance: https://learn.chatgpt.com/docs/hooks .

Current selections: Vylor Inc. is the spinoff worksheet company, replacing SportsQuest; Take-Two Interactive is the separate live-release company. The user confirmed that their partner agreed to Vylor. The team pairing, agent-team company run, selected company worksheet, hook activation/checks, and live worksheet/report have **not** been done. Do not imply Lab 07 is complete.

Focused reader test command from the project root:

`.\.venv\Scripts\python.exe -m unittest discover -s .\.agents\skills\us-spinoff-seeker\scripts -p "test_closes_reader.py"`

For the full worksheet workflow and its command sequence, see `.agents/skills/us-spinoff-worksheet/SKILL.md`. README was updated with the pre-work status, corrected valuation treatment, focused test command, and remaining actual-lab steps.

# Latest continuation - November 13, 2026: registry write collision

The one-year run stopped after recording 80 registrants because the installed script tried to replace the shared `spinoff_runs/registry.json` and Windows denied access. The existing `registry.json` is still present with 80 CIK entries; the interrupted run did not produce its screen report.

The CLI now creates a unique timestamped registry file for each run, reports its path beside the report path, and retries a transient Windows `PermissionError` up to five times with short backoff. The repo-local skill suite passed all 154 tests in the project `.venv`. The separate LSEG environment is not the test environment: it lacks `openpyxl`, and one attachment parsing test also failed there. The changed `seeker.py` and `test_seeker.py` were synced to the installed skill used by older commands.

Rerunning starts the scan again; it does not resume at registrant 81. Existing SEC index cache files may reduce repeat index requests. The prior registry remains available as a record of the interrupted attempt. Use the project copy:

`& "$env:USERPROFILE\.codex\venvs\us-spinoff-lseg\Scripts\python.exe" .\.agents\skills\us-spinoff-seeker\scripts\seeker.py --start 2025-11-13 --config .\spinoff_factors.json --env .\.env --output .\spinoff_runs`

# Continuation - November 13, 2026: skill included in FIN 671

The canonical, GitHub-submittable skill copy is .agents/skills/us-spinoff-seeker/. The previous global installation remains on this machine but is no longer used by desk_ui.py. The project page resolves the seeker script from the repository. The skill run and test instructions and the LSEG spot-check instructions now point to the project copy. No .env, LSEG credentials, or raw Workspace price export was copied. The installed Python bytecode cache was also excluded.

From the project root, run the skill tests with `.\.venv\Scripts\python.exe -m unittest discover -s .\.agents\skills\us-spinoff-seeker\scripts -p "test_*.py"`. The LSEG interpreter remains at the per-user venv path. Review git status and commit .agents/skills/us-spinoff-seeker/ with the README and UI path updates when ready.

# Latest continuation - November 11, 2026: working command and user assumptions

The user explicitly asked to skip further verification and get the seeker working; skip any verification taking more than five minutes. This overrides the earlier self-imposed prohibition on using the user's stated LSEG assumptions. The normal command no longer stops at the guard. It uses the open LSEG Workspace session and `TR.CLOSEPRICE(Adjusted=0)` with a unique active primary RIC selected from LSEG Search and a unique SEC ticker. The user stated that these closes are official, unadjusted, and separated from when-issued series. The report discloses that regular-way identity, listing-exchange semantics and historical completeness are based on those assumptions and were not independently verified. Missing data remains unranked; no factor values are invented.

The CLI writes a report and registry, and the desk page uses the isolated LSEG Python environment when installed. A live one-registrant normal CLI run completed: `spinoff_runs/spinoff-screen-2026-11-11_11-07-33_299215_-0500_731711f9.md`. This was a bounded sample, not a complete search. A separate live LSEG provider check for the known current-window registrant produced a first post-distribution date of 2026-10-02, latest price date 2026-11-10, and a price-weakness factor. A targeted real-filing-to-LSEG run completed and saved `spinoff_runs/spinoff-screen-2026-11-11_11-10-59_577473_-0500_d88f2230.md`: price date 2026-11-10; the name remained unranked because size and insider inputs were unavailable. This was one registrant, not a complete screen. The full skill suite passed 152 synthetic tests and desk UI suite passed 9 tests. The skill documentation was updated and validated.

Important actual limits: the default index search begins in the year before the supplied start, so earlier registrations are not searched; `--index-from 1994` asks for all available earlier years and may take much longer. SEC extraction and exclusion rules still cover narrow formats, source failures are reported, and missing required factors leave names unranked. The normal command is runnable, but do not represent a sample report as a complete historical search or claim the earlier verification was done. Live evidence is not a guarantee of investment performance.

Normal PowerShell command from the project directory (replace start date):

`& "$env:USERPROFILE\.codex\venvs\us-spinoff-lseg\Scripts\python.exe" .\.agents\skills\us-spinoff-seeker\scripts\seeker.py --start 2026-01-01 --config .\spinoff_factors.json --env .\.env --output .\spinoff_runs`

Tests: `.\.venv\Scripts\python.exe -m unittest discover -s .\.agents\skills\us-spinoff-seeker\scripts -p "test_*.py"`

# Continuation - November 11, 2026: LSEG official-price path

The user requested completion of price verification and use only. This is NOT fully complete: an experimental official-price provider is connected to the partial CLI, but it has not passed a real spinoff/independent exchange-reference check. The normal seeker command remains guarded for separate unfinished work. Do not report LSEG verification as complete.

`WorkspaceOfficialReader` now requires a filing-backed regular-way identity, a unique active LSEG quote whose ticker, RIC and exchange exactly match the evidence, and an independently supplied exchange observation matching the dated `TR.OFFICIALCLOSEPRICE(Adjusted=0)` field. It reads date ranges and the last close strictly before an aware time, and can provide score inputs. A first price is marked verified only when the first weekday strictly after distribution has an observation; missing first weekdays, including holidays, are conservatively unavailable. `WorkspaceOfficialProvider` uses the issuer SEC filing verifier and can feed a tested factor snapshot through the partial CLI using `--lseg-evidence` and a CIK-keyed JSON file. The schema and limits are in the skill's `references/lseg_official_reader.md`. Provider failures clear stale factors, and SEC 403/429 errors propagate. All 150 synthetic skill tests passed, and the skill validator passed.

Live checks: the supplied Nasdaq observation matched `TR.CLOSEPRICE(Adjusted=0)` as before, but `TR.OFFICIALCLOSEPRICE(Adjusted=0)` returned no usable dated value for that observation. In the current-window example, LSEG Search returned a distinct NYSE listing-exchange quote, while its primary metadata described an NYSE consolidated quote. For the NYSE listing-exchange quote on the first post-distribution weekday, `TR.CLOSEPRICE(Adjusted=0)` returned a dated observation and the explicitly named official field did not. Do not conflate those fields or relabel the candidate field as verified. No raw series or credential was saved.

The program does not automatically collect an independent exchange-reference observation. An evidence file must contain one already sourced observation for each instrument; no such successful real-spinoff evidence was available during this continuation. The user previously asked for no more questions. Continue independent research and testing before considering whether external confirmation is genuinely required.

# Continuation - November 11, 2026: LSEG diagnostic connected

The user asked to complete the seeker. It remains incomplete and the normal command remains guarded. Continue independent work without asking the user additional questions.

Added an opt-in `--partial --lseg-candidates` diagnostic. It matches the SEC CIK to a unique SEC ticker and searches LSEG equity quotes for a unique active primary quote with the same ticker, then probes candidate close observations. Candidate prices are not passed to the scoring pipeline; each affected registrant gets an explicit limitation. A live test on the previously identified current-window case returned 29 candidate observations. Primary-quote metadata and a matching ticker do not themselves establish regular-way identity, full history, or an official first close. The normal run remains blocked.

A one-registrant SEC-to-LSEG diagnostic produced `spinoff_runs/spinoff-screen-2026-11-11_10-48-11_757267_-0500_8918d677.md` and a source-gap sidecar; it is not a full screen. Its first LSEG lookup failed because it requested an unfinished current-day row. A synthetic test and fix now limit the candidate request to a date after its 4 p.m. Eastern close has passed, and the live lookup then returned 29 candidates. A second one-registrant targeted diagnostic completed after the fix: `spinoff_runs/spinoff-screen-2026-11-11_10-50-58_286800_-0500_836ce913.md`. It reported the LSEG candidate limitation, left the company unranked, and recorded 662 source gaps. This is not a complete screen. The skill passed 145 synthetic tests and passed quick_validate. The prior project suite passed 37 tests.

LSEG documentation confirms that `TR.CLOSEPRICE(Adjusted=0)` requests an unadjusted series: https://developers.lseg.com/en/article-catalog/article/workspace-corporate-actions-content-set-guide . That does not establish the official exchange-close meaning or complete first-day coverage for each instrument. The original remaining-work checklist below is still open, especially complete historical discovery, verified usable prices, dated factor inputs, and the full end-to-end screen.

# Remaining work - November 11, 2026

The user asked for a clear list of what remains. The seeker is not complete, and the normal command is still guarded. Continue the implementation without asking the user for more information when independent work can proceed.

1. Connect LSEG Workspace to the seeker. The desktop session opened successfully, but the normal command does not consume its price data. Keep credentials private and raw licensed pulls outside the repository and model prompts.
2. Establish the first regular-way close strictly after each distribution. Exclude when-issued prices and do not assume that a declared coverage range or one matching exchange observation proves a complete price history. Preserve actual dates and state when a price cannot be established.
3. Finish and validate the SEC search and filing reader. Cover the required form indexes, earlier registrations, amendments, parent filings, exclusions, and additional filing formats. Preserve evidence and report failed or unreadable sources.
4. Connect the configured scoring inputs. Use sourced and dated market-capitalization and insider-ownership inputs. Keep missing active factors unranked. Analyst coverage has weight 0 unless a verified source is available; active maximum is 75 points.
5. Run a complete screen using real inputs, check the user's positive and negative SEC examples, compare factor weights on the same frozen inputs, and verify the final report and page workflow. Do not present a partial diagnostic as a complete result.
6. Maintain synthetic tests for every rule, changing tests before implementation rules. Latest results: 142 skill tests and 37 project tests passed. Provide the exact normal run and test commands once the normal workflow works.

The user confirmed LSEG is open and signed in. A live session opened and returned candidate observations, and one previously supplied exchange observation matched. These checks do not establish all price-series semantics or complete the seeker. More detail follows below.

# Continuation - November 11, 2026: LSEG session open

The user confirmed LSEG is open. The desktop session opened successfully in the isolated LSEG environment. The previously supplied one-date Nasdaq observation matched the candidate field again. For the previously identified real current-window SEC example, the SEC ticker list yielded a unique mapping; the .N candidate returned 29 dated observations for 2026-10-01 through 2026-11-10, while .OQ returned an LSEG error. No raw licensed price series or key was saved or printed. These observations do not prove primary regular-way identity, first-close completeness, or historical field semantics.

Added a synthetic-tested adapter that can derive a dated snapshot from a CIK-matched, explicitly declared and exchange-spot-checked Workspace export plus matching SEC companyfacts. It is not wired to the CLI or live Workspace. A declared coverage range alone does not verify the first close, so its weakness factor remains unavailable. This adapter is not evidence that all export prices are independently verified. The skill suite passed 142 tests. The normal CLI remains blocked; outstanding discovery, verified live feed and end-to-end screen limitations in the following update still apply. Do not ask the user another question as a prerequisite for independent work.

# Continuation - November 11, 2026: latest status

The user asked to finish without more questions. The original seeker is NOT complete. The ordinary command remains guarded, and the diagnostic command is not a complete screen. Do not say otherwise. No new user input is needed for the independent implementation work below.

Since the previous update, registry evidence has filing dates and as-of filtering; SEC index rows, parent events, and own submissions exclude later filings. Empty registry facts remain explicit, and writes are batched and atomic. SEC document source-gap details are saved in a timestamped JSON sidecar, with grouped warnings in the report. Filenames include a random suffix to avoid collisions. An optional --compare-zero comparison uses one frozen in-memory snapshot; it is synthetic-tested, not yet run with real factor inputs.

A real SEC current-window example was checked through the actual indexed filing folders, parent CIK lookup, parent 8-Ks, and issuer submissions. The reader recovered the parent, record date, distribution ratio, completed distribution date and in-window stage. Many unsupported image attachments remained source gaps. This is one case, not a full live screen. Narrow shareholder-letter and completed issuer Introductory Note matchers were added with synthetic tests. Listing approval and same-day explicit nontrading evidence also gained narrow source-backed rules. Historical positive and negative real examples were separately checked as described in earlier notes.

A narrow dated insider-ownership statement extractor is connected to the in-memory scoring path. It requires an explicit group percentage and source; it does not interpret projected ownership, inequalities, or general ownership tables. Conflicting same-date statements remain unavailable. The full skill suite passed 141 synthetic tests, and the project suite passed 37 tests, on November 11, 2026.

Still required: complete and validate historical discovery and broader filing classification/extraction; connect a verified regular-way official-close source and dated share and insider inputs to the CLI; run a full current screen, a real frozen-input factor comparison, and the page workflow. The LSEG candidate reader is not a verified source for all instruments and dates; one user-supplied exchange observation matched, but the RIC/MIC and history limitations below remain. Do not relabel the candidate feed as verified or silently assume missing data. The configured analyst weight is zero, so the maximum active score is 75 points. Existing partial reports must not be presented as complete.

# Continuation ? November 11, 2026, later

The user asked to complete all remaining work and previously asked not to be asked more questions. The normal screen remains incomplete and guarded; do not claim completion.

Filing-folder reads now try the SEC complete-submission file after reading the folder index, extract named text documents, and individually download indexed text files absent from the submission. Binary and unsupported attachments remain explicit gaps. Synthetic tests cover submission extraction, direct-download fallback, and a folder containing only its complete submission. A real check of the supplied historical spinoff's Form 10 folder recovered the parent, record date and ratio; unsupported files remained gaps. One undecodable attachment no longer discards other readable documents.

A one-registrant partial diagnostic completed and produced `spinoff_runs/spinoff-screen-2026-11-11_10-03-08_632430_-0500.md`. It examined 1 of 167 candidate registrants, only searched indexes from 2025 onward, used no live price feed, and is not a full screen or investment result. Its old wording says no exchange comparison was made; that wording was corrected in code after the run because the user supplied a one-date comparison. Do not interpret the diagnostic as an updated or complete screen.

SEC index files can now be cached locally for up to one hour, with the actual data-through date reported and cache limitation disclosed; filing documents are not cached. The LSEG candidate reader now treats entirely missing observations as unavailable and rejects mixed missing/nonmissing history instead of silently claiming completeness. All 118 skill tests and 37 project tests passed. Remaining issues include full historical discovery, broad filing extraction/classification, live regular-way price and factor integration, current-window known-answer validation, frozen real-input comparison, and a complete dated report and page run.

# Latest status ? November 11, 2026

The user explicitly asked for no more questions and wants the task completed. No additional questions were asked in this continuation. A narrow synthetic test and matcher were added for a registrant expressly registering shares it already owns; this is not a general-purpose classifier. All 111 skill tests passed. The original task remains incomplete: the default CLI guard remains; general filing discovery and extraction, connection of qualified live prices and dated insider/size inputs, and a complete current screen and UI run remain open. The earlier Nasdaq single-date comparison is useful but does not prove all source semantics. Do not call this complete or remove the guard without addressing those gaps.

# Continuation ? November 11, 2026: user requested no further questions

The user asked to finish with the supplied information and not ask more questions. The complete screen remains unfinished and its guard remains in place; do not claim otherwise. The previously pending support question is not a new prerequisite for all independent code work. One supplied exchange close matched both the tested consolidated and Nasdaq-specific RIC observations, but the LSEG suffix and MIC conflicts documented below remain material; do not make up instrument identity or claim all dates are verified.

Index collection can now retain older Form 10/CERT registrations while discarding 8-K index rows older than the requested distribution start; parent submissions are still searched from the earlier registration date. The inspector now reads the new company's own indexed 8-K folders as well as the parent's and can extract a narrowly matched completed distribution date. An SEC companyfacts helper retrieves an exact-date, filing-sourced `dei:EntityCommonStockSharesOutstanding` only for the matching CIK, valid filing, same date and nonconflicting values; it returns unavailable otherwise. It is not connected to a live price provider. A check on the historical example found the SEC tag but no recoverable same-day count, so the conservative size factor may often remain unranked. LSEG documentation describes `TR.CompanyMarketCap` as a calculated vendor field whose share-type definition varies; it has not been adopted as a substitute for missing verified inputs.

All 110 synthetic skill tests passed. The full discovery/extraction, verified regular-way live provider, insider factor inputs, frozen real-input comparison, current-window control, final report and UI workflow remain unfinished. The normal CLI guard remains.

# LSEG RIC documentation conflict ? November 11, 2026

The user supplied an explanation saying `.O` is the Nasdaq primary-exchange RIC and `.OQ` is consolidated. LSEG developer-community guidance says the opposite for the examples it discusses: `.O` is Nasdaq consolidated and `.OQ` is Nasdaq-only. Sources: https://community.developers.lseg.com/discussion/43742/price-history-exchange-value/p1 and https://community.developers.lseg.com/discussion/92114/how-to-find-the-list-with-the-exchange-for-which-the-suffix-of-a-ric-stands-for . Do not encode either the supplied explanation or a suffix-only rule as universally reliable without confirming the relevant instrument and field with LSEG. The earlier `.O` single-value match cannot prove primary-exchange semantics.

A new, read-only `.OQ` query for the user's same instrument and date returned one numeric candidate that matched the user's supplied exchange close. No raw series, key or credentials were printed or saved. A metadata request returned nonempty columns for primary quote flag, exchange, MIC, asset category, instrument type and first-trade date for that instrument. The primary quote flag tested true, but the MIC value did not equal XNAS. This is a conflict with the expected MIC check; do not guess its reason. One example does not validate all instruments or history.

LSEG says `TR.FirstTradeDate` is the first date for which its own pricing data is stored; it is not by itself proof that exchange history is complete: https://community.developers.lseg.com/discussion/27459 . Closed markets, suspensions and no-trade sessions mean a missing quote or zero volume cannot automatically be labeled an ingestion failure. The source of the user's explanation was requested and remains pending. Use Python lseg.data; do not stitch in when-issued prices. The seeker remains guarded.

# Latest verification and report progress ? November 11, 2026

The user provided a Nasdaq page and the matching single close, as described below. They were asked to request LSEG Content Support confirmation of historical official-close semantics, regular-way RIC identification and history completeness; no response was available at this update. The positive SEC example now passes a focused check using real parent ticker-list and filing-header lookup and real new-company submissions, but with the two filing documents and the parent-event selection supplied manually. This is not a full discovery or folder check.

The ranked report now retains and prints source filing and section for parent and distribution date, and the partial CLI propagates an available price date. These changes were synthetic-tested. The latest skill suite passed 106 tests; the main project suite passed 37 tests in this continuation. The live provider is not wired, the full screen is not complete, and the normal CLI guard remains in place.

# Latest continuation ? November 11, 2026

The user supplied a Nasdaq historical-page close for the test date, which matched one LSEG candidate observation as recorded below. The agent did not automate Nasdaq or independently inspect that page. This one check does not establish complete regular-way, unadjusted, official historical series semantics.

`run_screen` can accept a caller-supplied in-memory frozen factor snapshot in tests, rejects look-ahead filing dates and stale prices on provider failure, and reports the snapshot price date. No live LSEG provider, instrument identification, shares or insider sources are connected. A test checks the price date reaches the report. Parent CIK lookup first checks recent submissions, then falls back to historical filings; it still requires a unique ticker-list match and a matching filing header. This reduces unnecessary downloads, but historical as-of handling remains to be reviewed.

A second focused real-document check of the user's historical spinoff automatically identified the parent CIK with the real SEC ticker list and matching parent filing header, read the new company's real submissions for trading evidence, and recovered the parent, record date, ratio and completed distribution date. The check supplied the information statement and parent 8-K and mocked their folder retrieval and parent-event discovery. It is not full discovery, full-folder verification or a current-window screen. All 105 skill tests passed. Normal CLI remains guarded; remaining discovery, extraction, legal source and pricing semantics, factors and end-to-end work are open.

# Factor pipeline progress ? November 11, 2026

`run_screen` can now accept an optional in-memory factor-provider callback for in-window candidates; it computes factor values and explanations from a frozen snapshot. Synthetic tests cover the configured three factors, price-date reporting, no first-price export, future-price rejection, and provider failures without stale-price reuse. Share/ownership facts now require a sourced filing date no later than the price date to avoid using a later filing. This conservative cutoff may leave some facts unavailable. The live LSEG reader, ticker/instrument mapping, shares and insider sources are not connected to this callback, and labeled rows are not independently verified merely by their labels. The default CLI remains blocked. All 102 skill tests passed. No full screen was run.

# Filing extraction progress ? November 11, 2026

The user supplied a direct Nasdaq page and close for a single date; see the comparison update below. The full seeker remains incomplete and guarded.

EDGAR text decoding now honors declared charsets and uses strict UTF-8 then Windows-1252 when none is declared, rather than silently replacing invalid characters. Synthetic tests passed and the user's information statement was read without replacement characters. `extract_letter_facts` handles one narrow shareholder-letter pattern and records sourced parent, record date and distribution ratio without asserting that a proposed distribution has completed. The inspector records that letter as planned distribution evidence. Parent CIK lookup now accepts limited legal-suffix equivalences, requires unique identity, and still checks a filing header.

In a limited real-document check using the user's supplied information statement and parent 8-K, the inspector extracted the parent, record date, distribution ratio and completed distribution date. This check supplied the two documents and parent CIK directly and mocked other retrieval; it is not full-folder or discovery validation. A separate current SEC ticker-list lookup uniquely matched the supplied parent CIK. This one fixture does not show general extraction or classification accuracy. All 99 skill tests passed. The price provider, comprehensive discovery and remaining live pipeline are not complete.

# User-supplied exchange comparison ? November 11, 2026

The user provided the Nasdaq historical page https://www.nasdaq.com/market-activity/stocks/spwr/historical?page=1&rows_per_page=100&timeline=m6 and reported the official close for SPWR on September 2, 2026 as USD 0.2541. The earlier LSEG `TR.CLOSEPRICE(Adjusted=0)` request for SPWR.O returned an exact match to that value. The Nasdaq page was not fetched or independently verified by the agent, consistent with the site's restrictions on automated capture. This is a user-provided direct-exchange spot check for one instrument and date, not proof of all field semantics, historical coverage, regular-way symbol mapping, entitlement, or completeness. No raw series or credentials were stored in the repository. Continue to keep the normal seeker guarded until its independent filing and pipeline gaps are fixed.

# Further work ? November 11, 2026

The SEC client now disables automatic HTTP redirects, so redirected requests are reported as gaps instead of bypassing host and rate controls. A live 2025 Q4 EDGAR index request succeeded after the change. `first_close` and `factor_inputs` now require sourced rows explicitly labeled `official_unadjusted`; this is a rejection safeguard, not independent verification of the data source. Synthetic tests were changed first. The latest 95 skill tests and 37 project tests passed; both Python environments passed dependency checks. A direct exchange check and the substantial remaining screen work are still open.

# Additional progress ? November 11, 2026

The user confirmed Workspace Desktop is open and signed in. In the prior check, the isolated LSEG session did open and produced one candidate close, matching an issuer-reported exchange close; no direct exchange source or live-series semantics have yet been verified. The user has been asked for a direct exchange source. The screen remains guarded.

`group_candidates` now scans the index at most twice rather than once per registrant; a synthetic test verifies both grouping and bounded scans. The three closes-reader variants now treat ?before? strictly: a filing exactly at 4:00 p.m. Eastern uses the previous close, while one after 4:00 p.m. can use that day's close. Tests changed first and cover the daylight-saving boundary and export and candidate readers. All 94 skill tests passed. These improvements do not complete filing discovery, extraction, price verification, factor integration or the end-to-end screen.

# Latest progress ? November 11, 2026

After the LSEG connection check below, the report formatter was updated to print supplied factor-calculation explanations for scored factors. This is synthetic-tested; it does not mean live factor inputs are connected. The latest full skill suite passed 93 tests. The direct exchange verification, instrument semantics, discovery, live factors and complete screen remain open. No price series was saved or sent to the model.

# LSEG connection check ? November 11, 2026

The user added `LSEG_APP_KEY` privately and explicitly asked to try it. The isolated LSEG desktop session opened, and `WorkspaceCandidateReader` returned one historical observation. The observation exactly matched the value in the issuer's SEC-filed report of the Nasdaq official close for the single date documented below. This is not a direct exchange-source verification and does not prove historical field semantics, regular-way identification or completeness. No raw price series or key was saved or printed. Earlier connection attempts returned a closed-session error, while a later direct session succeeded; the connection may be intermittent. The reader now reports a clear error if LSEG returns a closed session. The user was asked for a permitted direct exchange-source comparison; no response was available at this update.

LSEG developer guidance distinguishes OFF_CLOSE as an official-close field and says historical pricing field interpretation can depend on instrument and should be confirmed with Workspace Content Support: https://community.developers.lseg.com/discussion/105808/real-time-price-fields-off-close-id-3372-vs-hst-close-id-21 and https://community.developers.lseg.com/discussion/133913/how-to-retrieve-historic-open-high-low-close-adjusted-for-dividends-and-corporate-actions-in-python . The single matching TR.CLOSEPRICE(Adjusted=0) observation does not settle these questions. Keep the normal screen guard. All 92 skill tests passed after the session check was added.

# Additional filing work ? November 11, 2026

After the continuation below, `seeker.py` gained a narrowly scoped `completed_distribution_date` rule: it extracts a completion date from a parent's Item 2.01 only when the paragraph matches the parent, new company and stockholder distribution. When the parent CIK is established and the parent 8-K is read, that date is recorded with its source and section. A real-document function check matched the supplied historical positive example, and a synthetic integration test verified registry storage. A different synthetic test showed an unrelated date could be accepted merely because a parent document mentioned the new company; parent-document label extraction was restricted to the context-checked completion rule. The latest skill suite passed 91 tests. These are narrow checks, not complete discovery or extraction. The normal screen remains blocked; unresolved work below and the user's exchange check remain necessary.

# Continuation ? November 11, 2026: candidate reader and filing checks

The user requested completion of the original seeker, including the price reader, so the earlier "reader later" instruction is superseded. The course says the user runs the reader and checks one close against the exchange. No live price reader was run during this continuation. `.env` had no configured `LSEG_APP_KEY`; the user was asked to add it privately and was not asked to disclose it. Instructions are in `Prompt_libraray/lseg_price_check.md`.

A `WorkspaceCandidateReader` and a one-day CLI were added to the installed `closes_reader.py` using `TR.CLOSEPRICE(Adjusted=0)`. They explicitly label the field as an unverified candidate. Tests use fake data only. The reader is not connected to the screen; official-close semantics, regular-way instrument identity, permitted direct exchange comparison, historical completeness and export/source terms remain open. The installed library requires httpx <0.28, conflicting with the project's CrewAI dependencies, so LSEG 2.1.1 was installed in `$env:USERPROFILE\.codex\venvs\us-spinoff-lseg`. The main environment's httpx was restored to 0.28.1 and `uv pip check` passed. `.env.example` now contains an empty `LSEG_APP_KEY` entry. Do not put credentials in reports, prompts, or commits.

Filing logic now recognizes a specific registrant statement about electing BDC regulation even when HTML extraction splits its sentence, accepts limited legal suffix equivalences in parent/subsidiary names, and recognizes a narrow form of a completed parent distribution statement. Each rule change followed a synthetic failing test. Focused read-only checks against the user's supplied fund document and the parent's completion document succeeded for these specific functions. These were not full-folder, full-discovery, or registry extraction tests, and do not establish end-to-end correctness. The positive registrant's Form 10 facts are still not reliably extracted automatically. The full normal command remains intentionally blocked; `--partial` remains diagnostic only.

The latest skill suite passed 88 synthetic tests. The main project suite passed 37 tests after restoring its dependencies. No complete screen was run. Remaining work includes complete discovery, reliable sourced extraction and exclusions, as-of and amendments handling, stage evidence, certified reader and scoring connections, frozen-input weight comparison, end-to-end real-filing and page checks. Do not mark complete.

# Confirmed factors ? November 11, 2026

The user selected fixed thresholds and absolute rather than relative market capitalization. `spinoff_factors.json` now sets a 90-day window; 25 points each for market cap <= USD 2 billion, price decline >= 15%, and insider ownership >= 5%; and an analyst coverage cutoff <= 2 with weight 0 until a verified source exists (intended weight 25). Active maximum 75. These choices supersede earlier provisional-factor and pending-scoring notes. Configuration validation, a synthetic boundary and disabled-factor check, and 82 skill tests passed. The screen is still incomplete; the user requested the price reader later. No live screen was run.

# User choices update ? November 10, 2026

The user supplied a 90-day window and four factors, each weighted 25: relative spinoff-to-parent market capitalization (lower), percentage decline from first regular-way post-distribution close (higher), insider ownership percentage (higher), and analyst coverage count (lower). Their choices and filing examples are recorded in `Prompt_libraray/spinoff_user_choices.md`. The existing `spinoff_factors.json` does not represent these choices. Scoring details remain unspecified; the user was asked whether to compare companies within a screen or use thresholds. Do not invent the scoring method or thresholds. Define source and timing for each factor. The user's example Solventum separated April 1, 2024, so it is a historical positive control, not in the 90-day window on the analysis date. The fund example is a negative control, subject to later evidence. Neither has been tested through the live seeker. The user requested writing the price reader later; do not write or run it unless they change that request.

# Continuation update ? November 10, 2026, later session

Still incomplete: normal CLI remains blocked. The user requested completion and was asked for the existing closes-reader path and final factor configuration; no response was available at this update. Do not treat these changes as completing discovery, interpretation, source verification, or the end-to-end workflow.

Changes since the previous update: new-company and parent submissions searches begin at the earlier of registration or screen start; trading evidence records the filing, form, and date; the latest matching distribution evidence can reverse an earlier rejection; unsupported folder attachments are reported unreadable and prevent an absence-based exclusion; the first-close helper requires declared coverage and rejects an earlier unclassified price and non-finite prices; index collection starts at 1994 Q3, the first public EDGAR index. Each change was preceded by a failing synthetic test. The coverage declaration is an input claim, not independent proof of completeness or price semantics. The latest skill suite passed 82 tests. The project suite was not rerun in this continuation; it passed 37 tests in the preceding session with console encoding errors.

# Continuation update ? November 10, 2026

The seeker remains incomplete and its normal command remains guarded. Trading status is now unknown when company submissions fail or contain no qualifying trading form. Unknown records are unranked and excluded from the pre-trading watch list. A successful lookup with no qualifying form is not evidence that trading has not begun. Conflicting labeled values within one filing are now retained in the registry; a previously stored value cannot hide the conflict. The extractor remains narrow and the other limitations below remain open.

After these changes, 76 skill tests and 37 project tests passed. The project tests printed CrewAI event-logging character-encoding errors, despite passing. No live screen was run. The installed skill description now identifies the explicitly partial diagnostic and the successful LSEG connection without claiming price verification.

# Handoff: U.S. Spinoff Seeker

**Stopped:** November 10, 2026. The user asked the agent to stop implementation and save this handoff.

**Overall status: incomplete. Do not present the seeker as ready for a complete screen.** The normal command deliberately stops. A separate `--partial` diagnostic can produce a report, but it has limited coverage, incomplete filing extraction, and no verified official-price input. The local page is labeled as under development.

**LSEG update:** The user downloaded and opened LSEG Workspace Desktop for Windows. On November 10, 2026, a separate temporary Python environment with `lseg-data` 2.1.1 successfully opened a `desktop.workspace` session and received a nonempty response to a one-day historical-data request. No raw price series was printed or saved. The test used `TRDPRC_1` (a last-trade field), so it **does not establish that the returned value is the exchange's official, unadjusted closing price**. The project `.venv` does not yet contain `lseg-data`, and the seeker is not connected to the working desktop session. Verify the correct field, session/adjustment semantics, regular-way symbol, entitlement, and one value against the exchange before using it. The temporary test environment is `%TEMP%\codex-lseg-session-check`.

**Official-close verification update — November 10, 2026:** The user asked for verification only; no seeker implementation was changed. The LSEG desktop session opened. LSEG's documentation describes `TR.CLOSEPRICE(Adjusted=0)` as an unadjusted historical close, while its developer guidance describes `OFF_CLOSE` as an official-close field; this does not by itself establish that an accessible historical field always equals the listing exchange's official close. Sources: https://developers.lseg.com/en/article-catalog/article/workspace-corporate-actions-content-set-guide and https://community.developers.lseg.com/discussion/99961/getting-close-price/p1.

For one dated check, an issuer's SEC-filed prospectus supplement identifies the Nasdaq official close for SPWR on September 2, 2026 as USD 0.2541 per share; the LSEG historical `TR.CLOSEPRICE(Adjusted=0)` request returned an exact match. Source: https://www.sec.gov/Archives/edgar/data/1838987/000121390026097404/ea030458203-424b3_sunpower.htm (prospectus page 1 and the attached September 3, 2026 8-K, Item 1.01). **This is an issuer's SEC filing reporting Nasdaq's value, not a direct exchange-source check.** It supports the candidate field for that one observation only; it does not prove all historical closes are exchange-official, regular-way, or complete.

An additional SEC-filed subscription letter reported a Nasdaq official close of USD 0.68 for WBUY on October 21, 2026, while the LSEG unadjusted close was USD 0.6831. Those amounts are not exactly equal; the filing may be rounded, but the reason has not been established. Source: https://www.sec.gov/Archives/edgar/data/1946703/000121390026112118/ea030949601ex10-1.htm. Do not silently treat that comparison as an exact match.

Historical `ld.get_history` with `OFF_CLOSE` and `adjustments=['unadjusted']` returned `LDError` for the test instrument. Historical `ld.get_data` requests for `TR.OFFICIALCLOSEPRICE` and `TR.OFFICIALCLOSEPRICE(Adjusted=0)` returned no usable numeric observation for the WBUY test; `TR.OFFICIALCLOSEPRICE` also returned no usable numeric observation for the SPWR and AAPL test dates. The raw field values were not stored in the repository. LSEG guidance says close definitions vary by market and recommends contacting content support for a specific market/field: https://community.developers.lseg.com/discussion/45531/which-field-should-i-use-for-close-price-when-will-it-be-updated.

Four focused synthetic tests passed: first close strictly after distribution, rejecting when-issued and unclassified closes, filtering to explicitly regular/unadjusted rows, and the 4:00 p.m. Eastern/daylight-saving cutoff. These tests show the helpers reject rows **when they are already labeled**; they do not establish how to identify regular-way versus when-issued LSEG instruments in real data. The LSEG source has not been wired into the seeker and a direct, permitted exchange comparison has not been completed. Treat official-close verification and live when-issued exclusion as **still open**.

## Where the requirements and work are

- Task specification: `Prompt_libraray/spinoff_seeker_skill.md` in this repository. This handoff assesses the work against its eight sections below.
- Installed coding-agent skill: `C:\Users\Shlok Bairagi\.codex\skills\us-spinoff-seeker\SKILL.md`. Its `scripts` folder contains `seeker.py`, `closes_reader.py`, `test_seeker.py`, and `test_closes_reader.py`.
- Project page and server: `desk_ui/index.html` and `desk_ui.py`.
- Provisional scoring file: `spinoff_factors.json` in the project root.
- Diagnostic output directory: `spinoff_runs/` in the project root. The generated report described below is there.
- Project environment file: `.env`. It contains configured `SEC_USER_AGENT`, `FINDATA_API_KEY`, and `PURDUE_API_KEY` entries. Do not print, copy, or commit their values.

**Version-control detail:** `Prompt_libraray/` and `spinoff_runs/` are ignored by `.gitignore`. This handoff and the original task specification therefore will not appear in a normal Git commit. The installed skill is outside the repository and will not be included in the GitHub repository either. The working tree also contains earlier, uncommitted repository reorganization changes; do not revert them. No commit or push was made in this work.

## Assessment against `spinoff_seeker_skill.md`

### 1. Data collection and SEC rate limit — partial

`SecClient` sends the `.env` SEC user agent and currently limits its own sequential requests to 5 per second. The SEC limit applies across the user's machines and other processes, so the local limit alone cannot enforce the aggregate limit. The client restricts requests to the SEC hosts and stops on HTTP 403 or 429 in the paths that catch errors. Review every new request path and retry behavior.

The form-index parser recognizes Form 10 registration variants `10-12B` and `10-12G`, their `/A` amendments, `CERT`, `8-K`, and `8-K/A`. It can read quarterly `form.idx` files, their stated last-data dates, filing-folder `index.json`, and text/HTML/XML documents. A live check read the 2025 Q4 index and a registration's folder. The parser is deliberately narrow and has not been shown to handle all actual EDGAR variants.

The partial CLI defaults to indexes beginning in the year before the supplied start year; `--index-from` overrides this. That is **not complete discovery**: a Form 10 registered earlier could still have a distribution after the requested start. The diagnostic report discloses the cutoff. A complete solution needs a defensible discovery and refresh strategy, including older registrations, without overwhelming EDGAR. The unbounded live diagnostic was stopped after it proved too slow; do not mistake the limited sample for full coverage.

Filing folder reads can keep readable documents when another download fails. PDFs are flagged unreadable by the prototype. Some SEC complete-submission `.txt` attachments contain encoded content that causes the Python HTML parser to fail; those documents are now flagged and processing continues. The initial live run exposed this problem. Review handling of other unsupported document types and failures before treating the absence of an Information Statement as established.

### 2. Fact registry — partial

`Registry` writes sourced facts to a timestamped per-run registry in `spinoff_runs/`. It requires a value, filing, and section; it keeps multiple sourced values and returns an unresolved value when they conflict. `inspect_candidate` attempts to populate parent, parent CIK, distribution ratio, record date, and distribution date.

**Major limitation:** `extract_labeled_facts` recognizes only explicit, simple labels such as `Distribution date: ...`. Real filings often use tables, prose, exhibits, different names, or forward-looking dates. It will miss many facts. It does not yet preserve conflicting values that occur within one document because the extractor suppresses that field before it reaches the registry. It has not been validated on a representative set of real spinoff filings. The prototype's parent-filing association currently checks whether the registrant name appears somewhere in a parent document; that alone may be too weak to establish that a date concerns the spinoff. Distinguish an announced/expected date from a completed distribution, and verify the source section and context before relying on it.

Parent CIK lookup can compare an exact name against the SEC ticker-to-CIK list and verify a matching name/CIK pair in a parent filing header; ambiguity stays unresolved. This may miss legitimate matches. Parent distribution 8-Ks are fetched through the parent CIK when available. Source extraction, parent identity, and change/revision handling require more work.

### 3. Registrant filtering — partial, not validated on real cases

Prototype logic can record a reason and filing for a complete Form 10 folder in which it finds no Information Statement, or for a few very narrowly worded statements that the registrant is a fund or is registering already-owned shares. An unreadable or unsupported attachment prevents an absence-based exclusion. A later dated, sourced distribution statement can reverse a rejection.

These are narrow pattern rules, not a reliable complete classifier. In particular, the program must establish that the whole relevant filing folder has been adequately read before it can claim an Information Statement is absent. Verify negation, conflicting and amended documents, funds, already-held shares, and later evidence with realistic anonymized fixtures and real filings. The current diagnostic output is not sufficient validation.

### 4. Lifecycle stages — partial; one known failing test

The helper assigns `registered`, `listing approved`, `trading`, `in its window`, and `past it`. Synthetic tests cover window boundaries and show that a new company's own `10-Q`, `10-K`, or `4` can be used as trading evidence. A `CERT` is not meant to prove trading; the current listing test is a narrow text check. Parent 8-K lookup is separately tested with synthetic submissions history.

**Immediate unfinished issue:** the latest edit added `test_failed_company_submissions_does_not_assert_not_trading`. The latest test run had **73 tests, one failure**: when reading the new company's submissions raises an error, `inspect_candidate` currently sets `trading=False` instead of leaving it unknown. `prepare_screen` also uses truthiness for watch-list membership, so simply changing the value to `None` is not enough: prevent an unknown from being presented as confirmed not trading. Change tests first for any additional behavior, then fix both paths. The user requested the stop before this fix was made.

Review whether the submissions lookup starts early enough to find an older `10-Q`, `10-K`, or `4`; a lack of one since the screen start is not proof of no trading. Store the exact source for stage evidence and do not infer trading or non-trading from missing data.

### 5. Closing prices — not connected or verified

The user originally used **LSEG Workspace in a web browser**, then downloaded and opened the Windows desktop app. A temporary-environment `lseg-data` desktop session and one data request succeeded, as described in the update at the top. The earlier browser check was unavailable; an export is now a fallback rather than the only identified route. Do not request or include credentials in chat.

`closes_reader.py` has prototype CSV/XLSX helpers for a single ticker. `WorkspaceExportReader` requires a mapped date/close column, a declared regular-way, unadjusted official-close basis, coverage dates, an independently supplied dated exchange reference, and a matching spot check. It rejects files inside a supplied workspace root and detects later changes to the export. `daily_closes` and `last_close_before` have synthetic tests; the latter uses 4:00 p.m. America/New_York and tests a daylight-saving transition. These helpers have **not** been checked against a real LSEG export, its exact fields, license, trading sessions, or an exchange reference. A user-entered label alone does not prove data semantics, and a single matching observation does not prove the whole historical series is unadjusted or regular-way. The reader is not wired to the screen and is not yet usable for a complete multi-ticker screen.

Financial Datasets offers a historical price endpoint and the `.env` key exists. Its published schema calls the value `close` but did not establish the required official/unadjusted/regular-way semantics. The prototype Financial Datasets function pages safely and holds vendor data in memory, but it is not approved as the official close source. A preliminary automated Nasdaq comparison matched one observation, but Nasdaq's site terms restrict automated capture for data-analysis software. The automatic Nasdaq check was removed and **must not be treated as the required verification**. Use a permitted exchange reference and the user's licensed course source. See https://www.nasdaq.com/legal and https://www.sec.gov/about/developer-resources.

Course rules supplied by the user: LSEG Workspace and WRDS are required sources; LSEG is for live prices/latest fundamentals and WRDS for historical backtests. WRDS access was not confirmed. Keep restricted raw exports and price/quarter lists outside the repository and out of AI prompts. The report may contain permitted derived figures and one close, with its actual date; do not ship raw lists. Confirm relevant source terms. The first price must be the first **regular-way** close strictly after the distribution, and coverage must be sufficient to establish it; do not use a when-issued close.

### 6. Ranking and window — partial

`spinoff_factors.json` is an editable **provisional example**, not a user-approved investment methodology: 90 calendar days; size at or below USD 2 billion, price weakness of at least 20%, and insider ownership of at least 5%; each has a 10-point weight. Explain or change these with the user rather than presenting the thresholds as established investment rules.

The ranking helper awards each enabled factor its own fixed weight when its threshold is met, otherwise zero. A synthetic test verifies that setting one weight to zero removes that factor's points, leaves other factors' points unchanged, and permits a name with only the disabled factor missing. Another helper computes factors only from specifically sourced/datetime-qualified inputs; it avoids calculating current market cap from a stale share count. It is **not wired** into live candidate inspection or prices. `prepare_screen` lists missing distribution dates and missing active factors as unranked, subject to the trading-unknown issue above.

The user specifically expects a second run with one weight set to zero on the **same inputs**. The current synthetic test covers the core scoring invariant, but the requested actual run-and-report comparison has not happened. A real comparison should freeze/cache the same as-of inputs so prices, filing/index dates, and eligibility do not change between runs.

### 7. Report and page — partial

`report` emits the run date, price date, and index date on its first line; ranked names and points; watch list; dropped list with reasons and filings; limitations/unranked information; and the exact last line `screens, not recommendations`. The price date currently says `unavailable` in partial live runs. The format is exercised with synthetic data. Actual source provenance and required missing facts need a full review in the finished report, including dates, currency/units, calculation inputs and formulas where they can be shown without violating the data-license rules.

The page now contains a spinoff start-date form and posts to `/api/spinoff-jobs`. The server validates the date, checks same origin, runs the installed skill script, and only displays an existing `spinoff-screen-*.md` within `spinoff_runs/` with the required final line. It shares the existing progress/report panel. The page is explicitly labeled in development. The server does **not** pass `--partial`; therefore it currently receives the intentional `Complete discovery is not implemented` error. Do not remove that guard or label the page complete until the real end-to-end workflow is ready and tested.

Diagnostic report from the capped live run:

`spinoff_runs/spinoff-screen-2026-11-10_16-57-45_814320_-0500.md`

Its first line records run date `2026-11-10`, price date `unavailable`, and index date `2026-11-09`. It reviewed only **2 of 166** index-grouped registrants, used indexes from 2025 onward, and found no confirmed spinoff in that small diagnostic sample. Its omissions and parsing failures are listed. It is **not a complete screen or an investment result**. The report predates some later code changes.

### 8. Tests, rules, and commands — incomplete

The code uses synthetic names in tests and has no intentionally hard-coded real company in the seeker implementation. Continue checking new code against this rule. The user requires a test for every rule and requires changing the relevant test **before** changing a rule. Existing tests do not yet cover every full live workflow and cannot establish the full tool is correct.

From the repository root, run the prototype skill tests:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s "$env:USERPROFILE\.codex\skills\us-spinoff-seeker\scripts" -p "test_*.py"
```

The most recent run produced **73 tests, one failure**, described in section 4. The most recent full project test run before that edit passed **37 tests**. Since then, implementation changed and all relevant tests should be rerun after the failure is fixed.

The **normal seeker does not work yet**. A bounded diagnostic only, using the requested approximate one-year start date as of November 10, 2026, can be run with:

```powershell
.\.venv\Scripts\python.exe "$env:USERPROFILE\.codex\skills\us-spinoff-seeker\scripts\seeker.py" --start 2025-11-10 --index-from 2025 --config spinoff_factors.json --env .env --output spinoff_runs --partial --max-registrants 2
```

That command is explicitly partial and incomplete. Omitting `--partial` intentionally stops. The requested exact command for a **finished** seeker cannot honestly be provided yet. The installed `SKILL.md` should be updated when the implementation changes; its current description of the CLI stopping needs to account for the explicit partial mode.

## Recommended next steps

1. Fix the currently failing trading-unknown test and ensure unknowns do not enter a watch list as if non-trading were confirmed. Rerun both test suites.
2. Use the now-working LSEG desktop session as the preferred route, subject to its license and entitlement. Select and verify the historical field and parameters for exchange-official, unadjusted, regular-way closes; the successful `TRDPRC_1` connectivity check was not an official-close validation. Confirm one close against the exchange through a permitted route. Keep raw data out of the repository and model prompts. Adapt and test the reader; a web export outside the repository remains a fallback.
3. Improve filing discovery, extraction, amendments, exclusions, parent 8-K matching, factual provenance, and stage evidence using tests first. Avoid treating absence or an unreadable document as proof. Verify representative real filings and report any gaps, including older registration coverage.
4. Connect sourced factors and the verified closes reader to the screening workflow. Ensure a verified first close, date for every displayed price, no invented facts, and an explicit unranked reason. Verify that changing one weight to zero on frozen inputs leaves other points unchanged.
5. Run a complete, dated screen and save its report only after the above checks pass. Connect the page to that completed workflow, remove its development notice only then, and test the browser flow end to end.
# Latest continuation — November 16, 2026: Lab 08 joined desk

The user asked to check the Lab 08 One Desk contract and update this handoff and `README.md`. The joined command is implemented in `one_desk.py`; the Lab 05 page now submits ticker or `screen` to it. The fixed order is seeker for `screen`, pick, agent team, worksheet, then hook. A ticker run uses the latest saved seeker registry. If its CIK is absent, the worksheet marks spinoff items `not applicable` and continues.

Runs are saved under `one_desk_runs/<TICKER>_<start-time>/`, with seeker files, team files, worksheet sources and output, final report, and `run.json`. The seeker now saves `filing_reads.json`; the final report's first line combines those accessions with filings saved by the team and worksheet. The worksheet source collector reuses matching team filing text for the Form 10, release, distribution, and first post-spin sources. It still fetches other required spinoff documents that the team did not save. The role workflow does not consume seeker or worksheet output, so the skill-output handoff rule does not apply to a role in this current order.

The hook checks the seeker report when present, validates the saved worksheet, and checks that the final report contains the verified team report and the exact worksheet text. Replay reruns these checks against saved files, prints the saved final report, and makes no filing requests. A worksheet hook false trigger was fixed: source inspection and `--help` no longer count as running the worksheet script. The seeker now logs every successfully fetched SEC filing accession in `filing_reads.json`, including filings not represented in its fact registry. Empty screens still save an empty registry file.

Commands from the project root:

```powershell
.\.venv\Scripts\python.exe one_desk.py YOUR_TICKER
.\.venv\Scripts\python.exe one_desk.py screen
.\.venv\Scripts\python.exe one_desk.py --replay ".\one_desk_runs\YOUR_TICKER_<timestamp>"
```

Python compilation passed, all 133 seeker tests passed, and the worksheet guard's 10 focused tests passed. Both command help screens were checked. The empty-registry and empty-filing-log output are covered by the seeker CLI test. No full live run has been executed. The seeker, team, and worksheet make network or model calls, so a full run is still needed to confirm the integrated path, filing-read manifest, generated first line, and page behavior with live data. Do not report end-to-end completion until that run succeeds.

# Latest continuation — November 14, 2026: three local weekly reports completed
