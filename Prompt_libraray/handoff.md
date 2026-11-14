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
