# Walmart offline reviewed report

Company: Walmart Inc. (WMT). Analysis date: November 19, 2026. Review date: November 19, 2026.

This is a separate editorial and arithmetic review of the completed run. It uses saved evidence only. It has not received a new model verification, Manager semantic review, or worksheet guard run. The original report, worksheet, model outputs, and Verifier marks remain historical records. See [review notes](review_notes.md) and [integrity evidence](original_run_integrity.json).

## Evidence and scope

The selected filings were the 10-K accession **0000104169-26-000055**, filed March 13, 2026; 10-Q accession **0000104169-26-000154**, filed August 28, 2026; and earnings 8-K accession **0000104169-26-000168**, filed November 19, 2026. The earnings exhibit is Exhibit 99.1. These are recorded in the saved [filing metadata][F].

Source key **K** means the saved 10-K; **E** means the saved earnings exhibit. All cited line numbers are physical lines in those saved UTF-8 text files. Financial comparisons below identify their own periods; the annual figures are not the latest quarterly results. The 10-Q covers the quarter ended July 31, 2026 (saved [10-Q, line 12][Q]).

The reviewed filing list excludes unrelated filing references copied from the seeker registry. A registry reference alone does not prove that this run downloaded or read that filing. The original first-line filing list is preserved in the original report but is not adopted here.

## Business and reported developments

Walmart describes an omnichannel model that combines stores, eCommerce and other services. Price leadership, convenience and operating discipline are parts of its strategy. The FY2026 10-K reports **4,611 Walmart U.S. stores**, including locations in **all 50 states, Washington D.C. and Puerto Rico**. [K, lines 175-188][K]

Walmart competes with physical, eCommerce and omnichannel retailers and with providers of related services. The correct competition citation is **K223**, not K222. Walmart reports using AI tools and investing in supply-chain automation and fulfillment. Those statements establish activity; they do not establish the return on a particular investment or prove that accelerating it will reduce risk. [K, lines 182, 223 and 233][K]

For **Q3 FY2027, the three months ended October 31, 2026**, the earnings exhibit reports:

| Reported measure | Result | Saved evidence |
| --- | --- | --- |
| Total-revenue growth versus the prior-year quarter | 5.2%; 4.5% in constant currency | E10 and E21 |
| Net-sales growth versus the prior-year quarter | 5.1% | E140-144 |
| Global eCommerce sales growth | 17%, led by store-fulfilled pickup and delivery | E22 |
| Walmart U.S. eCommerce sales growth | 23% | E62 |
| Global advertising business growth | 25% | E23 |
| Walmart U.S. advertising growth | 37% | E23 and E63 |
| Global membership-fee revenue growth | 17% | E24 |

These are reported growth rates, not review estimates. Advertising is not identified here as a separate reporting segment; the exhibit says advertising arrangements can be recorded in net sales or as a reduction to cost of sales. The U.S. membership bundle is separately supported at E25. [E, lines 20-34 and 53-65][E]

### Revenue periods and units

The saved income statement is unaudited and uses **USD millions**. [E, lines 138-146][E]

| Total revenue | 2026 | 2025 | Reported year-over-year growth |
| --- | ---: | ---: | ---: |
| Three months ended October 31 | 188,835 | 179,496 | 5.2% |
| Nine months ended October 31 | 554,523 | 522,507 | 6.1% |

Arithmetic checks: `(188,835 - 179,496) / 179,496 x 100 = 5.2029%`, rounded to **5.2%**; `(554,523 - 522,507) / 522,507 x 100 = 6.1274%`, rounded to **6.1%**. These are checks of total revenue, not net sales. E144 separately reports quarterly net sales of **USD 186,757 million versus USD 177,769 million**, up **5.1%**. [E, lines 140-146][E]

## Annual financial evidence and calculations

The income and cash-flow figures below cover **FY2026 ended January 31, 2026** and **FY2025 ended January 31, 2025**. Balance-sheet figures are as of those dates. Amounts are **USD millions**, except EPS, which is **USD per diluted share**. [K, lines 913-940, 960-997 and 1044-1062][K]

| Reported input | FY2026 or January 31, 2026 | FY2025 or January 31, 2025 | K source line |
| --- | ---: | ---: | --- |
| Total revenue | 713,163 | 680,985 | 919 |
| Operating income | 29,825 | 29,348 | 923 |
| Net income attributable to Walmart | 21,893 | 19,436 | 934 |
| Diluted EPS attributable to Walmart | 2.73 | 2.41 | 937 |
| Walmart shareholders' equity | 99,617 | 91,013 | 997 |
| Noncurrent long-term debt | 34,624 | 33,401 | 986 |
| Long-term debt due within one year | 3,542 | 2,598 | 982 |
| Cash provided by operating activities | 41,565 | 36,443 | 1060 |
| Payments for property and equipment, outflow magnitude | 26,642 | 23,783 | 1062 |

The following are calculations, not separate reported amounts. The inputs use the same USD-million scale, so scale cancels in ratios.

| Calculation | Inputs and formula | Result |
| --- | --- | --- |
| FY2026 total-revenue growth | `(713,163 - 680,985) / 680,985 x 100` | 4.73% |
| FY2026 operating income / total revenue | `29,825 / 713,163 x 100` | 4.18% |
| FY2026 return on average Walmart equity | `21,893 / ((99,617 + 91,013) / 2) x 100` | 22.97% |
| Selected long-term debt / Walmart equity at January 31, 2026 | `(34,624 + 3,542) / 99,617` | 0.3831x |
| FY2026 operating cash flow less property/equipment payments | `41,565 - 26,642` | USD 14,923 million |

The **4.18%** calculation uses total revenue. Walmart's separate ratio of operating income to **net sales** is reported as **4.2% for FY2026 versus 4.4% for FY2025**. These denominators must not be mixed. [K, lines 557-568 and 917-923][K]

The debt ratio above includes only the stated long-term-debt components. It excludes short-term borrowings and lease obligations, so it is not a total-debt measure or sufficient proof of a low-risk balance sheet. [K, lines 978-988][K]

For FY2026, management identifies claims expense, a PhonePe compensation charge and depreciation among the operating-expense drivers. The report should not replace that explanation with an unsupported claim that AI, automation or remodel spending alone caused margin pressure. Investment costs and execution remain risks, not proof that a specific investment caused the reported change. [K, lines 567-568 and 283-285][K]

## Risks and original advisor judgment

The saved 10-K discusses omnichannel execution and investment-cost risks (K283-285), pandemic risks (K307-309), natural-disaster and other disruption risks (K310-312), and information-system continuity risks (K327). The pandemic and competition citations have been corrected from the preceding section headings. [K][K]

The original advisor recorded **Hold**. That remains a historical, provisional judgment; it is not a new recommendation from this review. No price-based valuation supports it in the saved worksheet. Claims that under-investment will harm market position or that faster automation will necessarily mitigate risk are not adopted as reported facts. The saved source establishes investments and risks, not their incremental return. [Original final report, investment recommendation][O]

## Reviewed worksheet status

Walmart was absent from the selected seeker registry, so spinoff-specific parent and distribution fields remain **not applicable** for this workflow. That registry result is not an independent finding about every part of Walmart's corporate history. [Saved worksheet source manifest][S]

Replace the original statement that the filing lacks earnings, cash-flow and share data with the following:

> The automatic worksheet reader did not establish all required inputs for this run. This does not mean the filing omits them. Existing disclosures must be reconciled before a valuation can be completed; a verified dated market-price and volume reader is also required for price comparison and liquidity analysis.

The FY2026 10-K discloses net income attributable to Walmart at K934, consolidated net income at K932 and K1048, depreciation and amortization at K1050, and capital spending at K1062. It also discloses **8,022 million annual diluted weighted-average shares** at K938-940 and K1217-1226. That annual weighted average is **not a current shares-outstanding count and has not been substituted for one**. No new owner-cash-flow or valuation result is calculated here. [K][K]

The distinction between consolidated income and income attributable to Walmart must be resolved consistently with the selected equity valuation basis. Periods, units, depreciation scope, capital-spending treatment and share-count definition also need reconciliation. The existence of disclosed figures alone does not complete those checks. The original worksheet's extraction gaps remain extraction gaps, not claims of nondisclosure. [K, lines 932-940 and 1044-1062][K]

| Output | Reviewed status |
| --- | --- |
| Owner cash flow | not computed |
| Low and mid equity valuations | not computed |
| Low and mid values per share | not computed |
| Dated market-price comparison and margin of safety | not computed |
| Live release view | not computed |
| Conviction | not computed |
| Median daily dollar volume | not known; no verified reader series was supplied |

The original worksheet has no target or live reader path. A missing stock-price or volume input is a reader-evidence gap, not a missing financial disclosure. P/E and peer valuation remain **not computed** because price and peer inputs were not supplied. [Original worksheet, lines 10, 48, 53, 65 and 76-82][W]; [original report, evidence gaps][O]

**Insider purchases: not assessed. Zero Form 4 filings were checked.** Zero purchases in the saved result must not be interpreted as no insider purchases. The source manifest records zero checked filings and no assessed date range. [Source manifest, `form4_coverage` and `form4_purchase_transactions`][S]

Debt covenants and other incompletely extracted items remain **not established by this review**. The earnings exhibit does contain debt-issuance information, so a generic “debt raised: not known” must be read as a worksheet extraction limitation, not nondisclosure. No conclusion about all covenants or restrictions is made. [E31][E]; [original worksheet, lines 35-39][W]

### Conditions for completing valuation later

1. Extract and reconcile the existing income, depreciation and capital-spending disclosures using one compatible period and the chosen equity basis. Do not require a new filing merely to obtain figures already disclosed.
2. Establish the required shares-outstanding definition and dated count. Do not use annual diluted weighted-average shares as a substitute for current outstanding shares.
3. Obtain a verified dated market close and verified regular-way close/volume observations for the required 20 completed trading days. Preserve any instrument, adjustment, session or exchange-comparison limitations.
4. Apply the worksheet rules only after those checks; document formulas and units. Review material debt and restriction gaps before assigning conviction.

These are completion conditions, not authorization to fetch data or rerun a model. All unavailable results above remain **not computed**. [Worksheet rules][R]

## Limits of the review

The review corrects identified wording, periods, units, citations and arithmetic against local evidence. It does not establish that every source statement or original model claim is correct. The original Verifier recorded **29 Correct, 17 Unsupported and 4 Wrong** marks; the separate offline findings are in the notes. No revised mark totals are asserted. Revised Insights did not receive a second Manager semantic review. The optional Financial Datasets cross-check was unavailable. [Original marks][V]; [saved Insight review][I]; [cross-check record][D]

Forward-looking AI returns, membership targets and future store-opening/remodel schedules were **not established from the evidence reviewed for this report**. That is narrower than asserting that no filing discloses them. The 10-K does include historical remodel and new-store capital spending at K609-615. [K][K]

[K]: ../../one_desk_runs/WMT_2026-11-19_21-11-20_008030_-0500/team/WMT_10-K_0000104169-26-000055.txt
[Q]: ../../one_desk_runs/WMT_2026-11-19_21-11-20_008030_-0500/team/WMT_10-Q_0000104169-26-000154.txt
[E]: ../../one_desk_runs/WMT_2026-11-19_21-11-20_008030_-0500/team/WMT_EX-99.1_0000104169-26-000168.txt
[F]: ../../one_desk_runs/WMT_2026-11-19_21-11-20_008030_-0500/team/filings.json
[O]: ../../one_desk_runs/WMT_2026-11-19_21-11-20_008030_-0500/final_report.md
[W]: ../../one_desk_runs/WMT_2026-11-19_21-11-20_008030_-0500/team/worksheet-20261119-211507-452129.md
[S]: ../../one_desk_runs/WMT_2026-11-19_21-11-20_008030_-0500/team/worksheet_sources_20261119_211504/sources.json
[V]: ../../one_desk_runs/WMT_2026-11-19_21-11-20_008030_-0500/team/verifier_output.json
[I]: ../../one_desk_runs/WMT_2026-11-19_21-11-20_008030_-0500/team/insight_review_final.json
[D]: ../../one_desk_runs/WMT_2026-11-19_21-11-20_008030_-0500/team/financialdatasets_comparison.json
[R]: ../../docs/lab07_worksheet_rules.md
