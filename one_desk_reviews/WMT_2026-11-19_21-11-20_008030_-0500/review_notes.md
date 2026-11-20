# Walmart offline review notes

Company: Walmart Inc. (WMT). Original analysis date: November 19, 2026. Review date: November 19, 2026.

These notes accompany [the reviewed report](reviewed_report.md). This is an offline editorial and arithmetic review, not a new model verification. The original run is `one_desk_runs/WMT_2026-11-19_21-11-20_008030_-0500/`. No original report, worksheet, source evidence or Verifier output is replaced.

## Original automated results

The original [verifier_output.json][V] contains exactly **50 entries: 29 Correct, 17 Unsupported and 4 Wrong**. These are the original automated labels. They are not updated labels for the reviewed report. The original completed workflow and internal worksheet checks remain historical results; those checks have not been rerun on this report.

The following ledger covers every original non-Correct entry. **L** means the physical line number in `team/equity_research_report.md`, as used by the original Verifier. It does not mean the line number in the combined final report, which includes the verification table. **K** and **E** identify the saved 10-K and Exhibit 99.1 linked below.

## Offline findings on all 21 flagged entries

| Original entries | Original label and count | Offline finding | Applied correction |
| --- | --- | --- | --- |
| L77: 182, 283 | Wrong, 2 | These are source-line references, not business figures. K182 supports AI use. K283 warns about execution and investment costs, not specifically under-investment. | Do not carry the numeric Wrong judgment into the reviewed report. Remove the unsupported under-investment inference. |
| L78: 233, 12 | Wrong, 2 | These are source-line references. K233 describes automation investment; E12 reports global eCommerce growth. Neither proves that accelerated automation mitigates a specified operational risk. | Retain the disclosed activity. Do not adopt the proposed acceleration as a proven causal conclusion. |
| L9: 4,611; 50 | Unsupported, 2 | Both facts appear at K187. The original saved `verifier_input.json` also contains that sentence, contrary to the Verifier's claim that its excerpt lacks it. | Restore the FY2026 Walmart U.S. store facts with K187. |
| L16: em dash | Unsupported, 1 | The competition quote is K223; K222 is a heading. The fact is supported but the citation is wrong. | Correct citation to K223. |
| L75: em dash | Unsupported, 1 | Pandemic wording is K307, not K306. Natural-disaster support is K310-312. | Correct and separate the risk citations. |
| L21: 37% | Unsupported, 1 | E23 expressly reports Q3 FY2027 Walmart U.S. advertising growth of 37%; E63 corroborates it. | Restore the rate with period and source; do not call advertising a separate reporting segment. |
| L24 and L94: 23% | Unsupported, 2 duplicate entries | E62 supports Q3 FY2027 U.S. eCommerce growth of 23%. A missing semantic mark does not disprove the fact. | State once as a reported fact. Do not present the repeated quote alone as an additional analytical Insight. |
| L68: 188,835; 179,496; 5.2; 554,523; 522,507; 6.1 | Unsupported, 6 | All six entries are in E146. E138-142 identifies the unaudited income statement, USD-million scale, and three-/nine-month periods ended October 31, 2026/2025. | Restore as a period-labeled total-revenue table. Check growth arithmetic and retain the reported rounding. |
| L88: 4.18% | Unsupported, 1 | FY2026 operating income / total revenue = 29,825 / 713,163 x 100 = 4.1821%, rounded to 4.18%; K915-923 supplies USD-million inputs and period. The original report's L61 calculation received a Correct mark. | Label the denominator explicitly. Do not mix this with the company's operating-income/net-sales ratio at K564. |
| L107: 4; L108: 9; L109: 99.1 | Unsupported, 3 | Claim identifiers and an exhibit identifier were parsed as numerical facts. The warnings need separate assessment: revised research claim 4 matches K188; claim 9 mislabels revenue growth as net-sales growth; EX-99.1 is a valid filing exhibit source. | Omit stale or parser-generated audit claims from the reviewed narrative. Correct claim 9's financial label. Preserve missing-second-Manager-review limitations. |

Count reconciliation: original Wrong groups = `2 + 2 = 4`; original Unsupported groups = `2 + 1 + 1 + 1 + 2 + 6 + 1 + 3 = 17`. The table is an offline assessment of those entries, not a replacement scoring exercise. It does not make every associated interpretation correct.

## Additional wording corrections

- **Revenue versus net sales:** original final-report line 76 labels 5.2% as net-sales growth. E144 reports quarterly net-sales growth of **5.1%**, while E146 reports total-revenue growth of **5.2%**. The reviewed report separates them, including the constant-currency total-revenue figure at E10/E21.
- **Financial periods and units:** annual flows are FY2026/FY2025, ended January 31; balance-sheet values are point-in-time at those dates. The earnings table covers three and nine months ended October 31, 2026/2025. Sources use USD millions except per-share data. Ratios show their inputs and formulas.
- **Causal interpretations:** the original recommendation assigns margin pressure to AI, automation and remodels without isolating their effects. K567-568 identifies claims expense, PhonePe compensation and depreciation among the reported drivers. The reviewed report uses that narrower explanation. It does not claim investments alone explain the margin change.
- **Judgment versus disclosure:** the original Hold view is retained only as a historical, provisional advisor judgment. No new price-based recommendation is inferred. A selected long-term-debt ratio is not described as total debt or proof of balance-sheet safety; K978-988 also includes other borrowing/lease categories.
- **Not extracted versus not disclosed:** the original worksheet's lines 14-15 incorrectly imply that necessary data must first appear in a future filing. K932/K934, K1048/K1050/K1062 and K938-940 disclose income, depreciation, capital spending and annual weighted-average shares. These need reconciliation, not an assumption of nondisclosure. Original annual `facts.json` already includes attributable net income and property/equipment payments.
- **Shares and income definitions:** FY2026 diluted weighted-average shares are **8,022 million** (K938-940/K1217-1226). This is not a current outstanding count and was not substituted for one. Consolidated income at K932 differs from Walmart-attributable income at K934. The review does not select a valuation basis or combine incompatible definitions.
- **Price and volume:** no target or live reader path was supplied in original worksheet lines 76-82. Completion needs verified dated market-price/volume evidence, not a requirement that a future filing publish a share price. All original unavailable valuation, margin-of-safety, live-view and conviction results remain **not computed**.
- **Insider purchases:** source-manifest `form4_coverage.filing_count_checked` is **0**; its first/last filing dates are null. Purchases are **not assessed**, with no assessed date range. An empty purchases list does not mean no purchases occurred.
- **Generic gaps:** future AI returns, membership targets and future store/remodel schedules were not established from the reviewed evidence. The review avoids asserting their absence from all filings. K609-615 does disclose historical capital spending. E31 also contains debt-issuance information, so a generic worksheet debt gap cannot be treated as nondisclosure.
- **Filing list:** the original final-report opening includes filing references from the copied seeker registry. The reviewed report lists only the selected Walmart filings and earnings exhibit supported by saved filing metadata and local source text. It does not claim every registry citation was fetched or read.

## Arithmetic checks

All annual calculation inputs below are USD millions from K915-940, K982/K986/K997, and K1044-1062. Results are independently recomputed with decimal arithmetic, without a model.

| Check | Formula | Rounded result |
| --- | --- | --- |
| FY2026 revenue growth | `(713163 - 680985) / 680985 x 100` | 4.73% |
| FY2026 operating income / total revenue | `29825 / 713163 x 100` | 4.18% |
| FY2026 return on average Walmart equity | `21893 / ((99617 + 91013) / 2) x 100` | 22.97% |
| Selected long-term debt / Walmart equity | `(34624 + 3542) / 99617` | 0.3831x |
| FY2026 operating cash flow less capital spending | `41565 - 26642` | USD 14,923 million |
| Q3 FY2027 total-revenue growth | `(188835 - 179496) / 179496 x 100` | 5.2% |
| Nine-month FY2027 total-revenue growth | `(554523 - 522507) / 522507 x 100` | 6.1% |

Quarterly source: E140-146, USD millions for periods ended October 31. No owner-cash-flow valuation, per-share value, margin of safety, live view or conviction has been newly calculated.

## Remaining limitations

The optional Financial Datasets cross-check was unavailable. Revised Research, Financial and Advisor Insights did not receive a second Manager semantic review; see saved `insight_review_final.json`. The revised report has no new model verification or guard pass. The offline review is scoped to saved evidence and identified claims, not all possible errors. Valid citations and arithmetic do not prove an investment recommendation will outperform a benchmark.

The reviewed report depends on the preserved source files through relative links. It is not a self-contained source archive. Review the income/share basis and verified reader evidence before any future valuation; do not infer that an existing disclosure completes those tasks.

## Original preservation and submission files

The [SHA-256 integrity record](original_run_integrity.json) records all **53 original-run files** before and after creation of these review artifacts. Its final `unchanged` field and empty added/removed/changed lists establish the local before/after comparison. This is not an external authenticity certification or a comparison with an earlier date.

Proposed submission files, all outside the original run:

1. `one_desk_reviews/WMT_2026-11-19_21-11-20_008030_-0500/reviewed_report.md`
2. `one_desk_reviews/WMT_2026-11-19_21-11-20_008030_-0500/review_notes.md`
3. `one_desk_reviews/WMT_2026-11-19_21-11-20_008030_-0500/original_run_integrity.json`

No credentials, virtual environments, new licensed reader data, application-code changes or unrelated files are proposed. No network/model calls, desk reruns, hook enablement, commits or pushes are part of this review.

### Local commit evidence package

The submission package also includes the original Walmart reports and worksheet, Verifier input/output and follow-up records, revised research claims, financial facts/calculations, filing metadata, coverage/limitation records, and saved filing text needed to check this review offline. These files are included without changes. Full role-prompt histories and intermediate data-step captures are not required for these checks and are omitted. The integrity record inventories all 53 files preserved locally in the original run; it does not assert that all 53 are included in the commit.

The copied seeker registry is reused from the already tracked [shared registry](../../spinoff_runs/registry-2026-11-13_22-39-11_137090_-0500_ddc00b3d.json). Its bytes match the original run's copied registry, and Walmart's CIK is absent. The already tracked [worksheet rules](../../docs/lab07_worksheet_rules.md) are also reused. Historical JSON metadata retains this machine's absolute paths; when checking the package on another machine, resolve the Walmart run relative to the repository and use the linked shared registry instead of the omitted copied-registry path. No claim of portable automatic replay is made. The reviewed report's relative Markdown links resolve within the submitted and already tracked evidence.

[K]: ../../one_desk_runs/WMT_2026-11-19_21-11-20_008030_-0500/team/WMT_10-K_0000104169-26-000055.txt
[E]: ../../one_desk_runs/WMT_2026-11-19_21-11-20_008030_-0500/team/WMT_EX-99.1_0000104169-26-000168.txt
[V]: ../../one_desk_runs/WMT_2026-11-19_21-11-20_008030_-0500/team/verifier_output.json
