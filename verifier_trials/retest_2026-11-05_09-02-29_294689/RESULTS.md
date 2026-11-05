# Costco verifier retest

Analysis date: 2026-11-05. The source is the saved November 5 Costco run. Each test uses its own copy; the source run was not modified. Each output below was produced with `desk_flow.py --verify-only`. The files `verifier_input.json`, `verifier_model_output.json`, `verifier_output.json`, and `verified_report.md` in each verification folder preserve the inputs, model response, marks, and report. Where a model retry occurs, its instruction and output are saved separately.

## Seeded diluted EPS

In `seeded_eps/equity_research_report.md`, the FY2026 XBRL row and a separate purported filing quote state USD 21.76 per diluted share. The saved 10-K itself remains unchanged. The verifier marked both instances wrong. It corrected the XBRL row to USD 20.76 per diluted share, fiscal year ended 2026-08-30, tag `us-gaap:EarningsPerShareDiluted`, and included saved 10-K line 637 beside the correction:

`Diluted | $ | 20.76 | | | $ | 18.21 | | | $ | 16.56`

Output: `seeded_eps/verification_2026-11-05_09-02-45_479250_-0500/verified_report.md`. The other claims in that original report are not all verified; consult its complete marks table.

## Invented revenue growth

In `invented_growth/equity_research_report.md`, the inserted annual total-revenue growth is 14.14%. The verifier marked it wrong and displayed the result from the quoted inputs, in USD millions:

`(303,154 - 275,235) / 275,235 × 100 = 10.1437%, rounded to 10.14%`

The inputs are the FY2026 and FY2025 total-revenue columns at saved 10-K line 624. Output: `invented_growth/verification_2026-11-05_09-02-45_479250_-0500/verified_report.md`.

## Eleven clean core claims

`clean_eleven_v2` is a reconstructed numerical audit fixture made from a copy of the saved run, not a full replacement for its narrative report. It contains the eleven core claims with explicit source, period, column, units, and calculation metadata. It includes the missing fourth-quarter total-revenue growth calculation. Code independently checks the source rows, dates, columns, units, annual XBRL facts where available, and arithmetic; a model separately assesses the period and definition. The latest output marked **11 of 11 correct**:

`clean_eleven_v2/verification_2026-11-05_09-12-39_162508_-0500/verified_report.md`

| Claim | Value | Saved source |
|---|---|---|
| FY2026 total revenue | USD 303,154 million | 10-K line 624 |
| FY2026 total-revenue growth | 10.14% = (303,154 − 275,235) / 275,235 × 100 | 10-K line 624 |
| FY2026 operating margin | 3.85% = 11,685 / 303,154 × 100 | 10-K lines 628 and 624 |
| FY2026 net income | USD 9,226 million | 10-K line 634 |
| FY2026 diluted EPS | USD 20.76 per share | 10-K line 637 |
| FY2026 return on average equity | 28.40% = 9,226 / ((35,803 + 29,164) / 2) × 100 | 10-K lines 634 and 698 |
| FY2026 debt to equity | 0.1721 = (3,914 + 2,248) / 35,803 | 10-K lines 687, 683, and 698 |
| FY2026 free cash flow | USD 9,382 million = 15,817 − 6,435 | 10-K lines 760 and 762; capital spending is the magnitude of the reported cash outflow |
| FY2026 fourth-quarter total revenue | USD 95,723 million | EX-99.1 line 45, first column; 16 weeks ended 2026-08-30 |
| FY2026 fourth-quarter total-revenue growth | 11.10% = (95,723 − 86,156) / 86,156 × 100 | EX-99.1 line 45, first and second columns; comparable 16-week periods |
| FY2026 fourth-quarter diluted EPS | USD 6.75 per share | EX-99.1 line 58, first column; 16 weeks ended 2026-08-30 |

Earlier clean runs remain in the folders: one marked all eleven correct, while later runs marked some unsupported because the model omitted a mark or included units in a format the matcher did not accept. The matcher was corrected and one targeted retry was added for omitted structured claims. Missing or conflicting model checks are still marked unsupported; the system does not assume success. The latest 11-of-11 result is evidence for these specific cases, not a guarantee of repeatability or of correct verification of every report.

## Boundaries

The graph order was not changed. The verifier remains incomplete for arbitrary prose and calculations that do not use the supported formats. A model can misread definitions or periods, and a correct presentation is not evidence that an investment recommendation will outperform a benchmark. The eleven-claim fixture is not a review of the original narrative or its investment recommendation.
