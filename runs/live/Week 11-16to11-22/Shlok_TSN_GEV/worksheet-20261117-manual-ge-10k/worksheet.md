<!-- lab07-worksheet-source
run="C:/Users/Shlok Bairagi/Desktop/Fin Master AI/FIN 671/one_desk_runs/GEV_Lab09_2026-11-17_16-11-12_3998/team"
live_run="C:/Users/Shlok Bairagi/Desktop/Fin Master AI/FIN 671/one_desk_runs/TSN_2026-11-16_20-24-01_032591_-0500/team"
rules="C:/Users/Shlok Bairagi/Desktop/Fin Master AI/FIN 671/docs/lab07_worksheet_rules.md"
reader="C:/Users/SHLOKB~1/AppData/Local/Temp/fin671-gev-bars-20261117.json"
live_reader="C:/Users/SHLOKB~1/AppData/Local/Temp/fin671-tsn-bars-live20-20261117.json"
-->
Filings read: GEV original Form 10 and amendment; final Information Statement filed 2024-03-08; GEV FY2025 Form 10-K filed 2026-01-29; TSN FY2026 Form 10-K and earnings-release Form 8-K accepted 2026-11-16T12:41:53Z.

# Worksheet: GEV | analysis date 2026-11-17

## Spinoff facts
- Parent: General Electric Company; the Information Statement says the continuing GE shares would trade under the name GE Aerospace [GEV Information Statement, cover and “The Spin-Off”](https://www.sec.gov/Archives/edgar/data/1996810/000119312524063739/d808872dex991.htm).
- Distribution ratio: one GEV share for every four GE shares [GEV Information Statement, cover, “distribution entitlement”](https://www.sec.gov/Archives/edgar/data/1996810/000119312524063739/d808872dex991.htm).
- Record date: March 19, 2024 [GEV Information Statement, cover](https://www.sec.gov/Archives/edgar/data/1996810/000119312524063739/d808872dex991.htm).
- Distribution date: April 2, 2024; effective at twelve ten a.m. New York City time [filing file="worksheet_sources_gev_spin_20261117/GEV_Information_Statement_0001193125-24-063739_d808872dex991.txt" line=85 section="Information Statement cover; distribution effective time" tag=historical period=2024].
- Dated market price: 779.91 USD per share on 2026-11-17 [price ticker=GEV date=2026-11-17 reader=target].
- Reader interpretation: LSEG unadjusted close-price and volume fields, using the user's stated field interpretation. An independent exchange comparison was not completed.

## GEV judgment
At the saved price, GEV trades above the worksheet's low-case value. This course calculation does not support calling the shares cheap. FY2025 net income includes a U.S. tax valuation-allowance benefit, so the reported year may not be a normalized earnings base [GEV Form 10-K, MD&A, “Income Taxes”](https://www.sec.gov/Archives/edgar/data/1996810/000199681026000015/gev-20251231.htm).

Evidence that would change the view: a sustained earnings base without the tax benefit, updated cash flow and capital-spending figures, and a dated price at or below the low-case value.

## Owner cash flow and value range — GEV
The course formula is after-tax earnings plus depreciation and amortization minus capital spending. The Form 10-K tables report USD in millions; these inputs are converted to whole USD before calculation.
- After-tax earnings: 4,884,000,000 USD, historical FY2025 net income attributable to GE Vernova [filing file="GEV_10-K_0001996810-26-000015.txt" line=2945 section="Consolidated and Combined Statements of Earnings" tag=historical period=FY2025 scale=1000000]
- PPE depreciation component: 615,000,000 USD, historical FY2025 [filing file="GEV_10-K_0001996810-26-000015.txt" line=3086 section="Consolidated and Combined Statements of Cash Flows" tag=historical period=FY2025 scale=1000000]
- Intangible amortization component: 238,000,000 USD, historical FY2025 [filing file="GEV_10-K_0001996810-26-000015.txt" line=3090 section="Consolidated and Combined Statements of Cash Flows" tag=historical period=FY2025 scale=1000000]
- Depreciation: 853,000,000 USD, historical FY2025; PPE depreciation plus intangible amortization [calc id=depreciation_and_amortization]
- Capital spending: 1,277,000,000 USD, historical FY2025 additions to property, plant, equipment, and internal-use software; filing presents this outflow in parentheses [filing file="GEV_10-K_0001996810-26-000015.txt" line=3143 section="Consolidated and Combined Statements of Cash Flows" tag=historical period=FY2025 sign=magnitude scale=1000000]
- Diluted shares: 276,000,000 shares, historical FY2025 diluted weighted-average shares [filing file="GEV_10-K_0001996810-26-000015.txt" line=2963 section="Consolidated and Combined Statements of Earnings" tag=historical period=FY2025 scale=1000000]
- Owner cash flow: 4460000000 USD; after-tax earnings + depreciation - capital spending [calc id=owner_cash_flow]
- Low case discount rate: 0.1 [rule id=low_discount_rate]
- Low case growth rate: 0.0 [rule id=low_growth_rate]
- Low case equity value: 44600000000 USD; owner cash flow divided by the low-case discount rate [calc id=low_equity_value]
- Mid case discount rate: 0.09 [rule id=mid_discount_rate]
- Mid case growth rate: 0.02 [rule id=mid_growth_rate]
- Mid case equity value: 64988571428.57142857142857143 USD [calc id=mid_equity_value]
- Low case value per share: 161.5942028985507246376811594 USD per share [calc id=low_value_per_share]
- Mid case value per share: 235.4658385093167701863354037 USD per share [calc id=mid_value_per_share]
- Margin of safety against the low case: -79.28040377754475200501581472% [calc id=margin_of_safety]

## Debt, cash, and obligations
- Spin-date capitalization: total debt was 129,000,000 USD on the historical December 31, 2023 basis [filing file="worksheet_sources_gev_spin_20261117/GEV_Information_Statement_0001193125-24-063739_d808872dex991.txt" line=3255 section="Capitalization" tag=historical period=2023 scale=1000000].
- Pro forma spin capitalization: total debt remained 129,000,000 USD on the December 31, 2023 pro forma basis [filing file="worksheet_sources_gev_spin_20261117/GEV_Information_Statement_0001193125-24-063739_d808872dex991.txt" line=3256 section="Capitalization" tag="pro forma" period=2023 scale=1000000].
- The Information Statement said GEV expected a cash balance of about 4,200,000,000 USD at the spin; this was an expectation, not the final recorded transfer [filing file="worksheet_sources_gev_spin_20261117/GEV_Information_Statement_0001193125-24-063739_d808872dex991.txt" line=3288 section="Capitalization, note (a)" tag="pro forma" period=2023 scale=1000000000].
- The Information Statement estimated a net cash contribution from GE of about 2,000,000,000 USD to reach that target; it said the amount would be finalized later [filing file="worksheet_sources_gev_spin_20261117/GEV_Information_Statement_0001193125-24-063739_d808872dex991.txt" line=3291 section="Capitalization, note (a)" tag="pro forma" period=2023 scale=1000000000].
- The Information Statement described a 3,000,000,000 USD revolving facility, not expected to be used at closing, for near-term working-capital needs [filing file="worksheet_sources_gev_spin_20261117/GEV_Information_Statement_0001193125-24-063739_d808872dex991.txt" line=3294 section="Capitalization, note (a)" tag="pro forma" period=2023 scale=1000000000].
- The Information Statement described a 3,000,000,000 USD trade-finance facility, not expected to be used and not intended to provide direct liquidity [filing file="worksheet_sources_gev_spin_20261117/GEV_Information_Statement_0001193125-24-063739_d808872dex991.txt" line=3296 section="Capitalization, note (a)" tag="pro forma" period=2023 scale=1000000000].
- Actual GE cash contribution recorded for future operations: 515,000,000 USD, reported after the spin in FY2025 [filing file="GEV_10-K_0001996810-26-000015.txt" line=3646 section="Note 1, Organization" tag="reported after the spin" period=FY2025 scale=1000000]
- Actual restricted cash transferred by GE: 325,000,000 USD, reported after the spin in FY2025 [filing file="GEV_10-K_0001996810-26-000015.txt" line=3647 section="Note 1, Organization" tag="reported after the spin" period=FY2025 scale=1000000]
- The Information Statement described 323,000,000 USD of restricted cash [filing file="worksheet_sources_gev_spin_20261117/GEV_Information_Statement_0001193125-24-063739_d808872dex991.txt" line=3797 section="Unaudited Pro Forma Condensed Combined Financial Statements, adjustment (b)" tag="pro forma" period=2023 scale=1000000].
- It also described a 32,000,000 USD deposit for legacy GE legal matters [filing file="worksheet_sources_gev_spin_20261117/GEV_Information_Statement_0001193125-24-063739_d808872dex991.txt" line=3797 section="Unaudited Pro Forma Condensed Combined Financial Statements, adjustment (b)" tag="pro forma" period=2023 scale=1000000].
- Related pro forma indemnification liability: 355,000,000 USD, to cover the obligations and return any remaining cash to GE when resolved [filing file="worksheet_sources_gev_spin_20261117/GEV_Information_Statement_0001193125-24-063739_d808872dex991.txt" line=3798 section="Unaudited Pro Forma Condensed Combined Financial Statements, adjustment (b)" tag="pro forma" period=2023 scale=1000000].
- Total debt excluding finance leases at December 31, 2025: less than 100,000,000 USD [filing file="GEV_10-K_0001996810-26-000015.txt" line=2184 section="Liquidity and Capital Resources" tag=historical period=FY2025 scale=1000000000].
- No borrowings were outstanding under the revolving credit facility at December 31, 2025 [GEV Form 10-K, “Liquidity and Capital Resources”](https://www.sec.gov/Archives/edgar/data/1996810/000199681026000015/gev-20251231.htm).
- Estimated GE credit-support RPO and other obligations at the spin: approximately 65,000,000,000 USD [filing file="worksheet_sources_gev_spin_20261117/GEV_Information_Statement_0001193125-24-063739_d808872dex991.txt" line=6432 section="Certain Relationships and Related Person Transactions — Credit Support" tag="pro forma" period=2024 scale=1000000000].
- Updated GE credit-support RPO and other obligations at December 31, 2025: approximately 8,000,000,000 USD [filing file="GEV_10-K_0001996810-26-000015.txt" line=2225 section="Parent Company Credit Support" tag=historical period=FY2025 scale=1000000000].
- Amount expected to mature by December 31, 2029: approximately 6,000,000,000 USD [filing file="GEV_10-K_0001996810-26-000015.txt" line=2226 section="Parent Company Credit Support" tag=historical period=FY2025 scale=1000000000].
- Indemnification commitments reported after the spin: 964,000,000 USD [filing file="GEV_10-K_0001996810-26-000015.txt" line=6812 section="Note 21, Guarantees" tag=historical period=FY2025 scale=1000000]
- Recorded indemnification liability: 628,000,000 USD [filing file="GEV_10-K_0001996810-26-000015.txt" line=6813 section="Note 21, Guarantees" tag=historical period=FY2025 scale=1000000]
- Liability for legacy GE legal matters tied to restricted cash: 347,000,000 USD [filing file="GEV_10-K_0001996810-26-000015.txt" line=6814 section="Note 21, Guarantees" tag=historical period=FY2025 scale=1000000]
- Indemnifications under GE agreements, including the Tax Matters Agreement: 186,000,000 USD [filing file="GEV_10-K_0001996810-26-000015.txt" line=6817 section="Note 21, Guarantees" tag=historical period=FY2025 scale=1000000]
- While GE support remains outstanding, GEV must use reasonable best efforts to replace it and obtain GE's release; GEV pays fees, faces restrictions, and may owe indemnification. The original statement says GE's maximum aggregate exposure cannot be reasonably estimated [GEV Information Statement, “Certain Relationships and Related Person Transactions — Credit Support”](https://www.sec.gov/Archives/edgar/data/1996810/000119312524063739/d808872dex991.htm).

## Parent after the spin
GE completed the spin and continued as the public company later named GE Aerospace. GEV became an independent public company, and its shares trade on the NYSE under ticker GEV [GEV Information Statement, “The Spin-Off”; GEV Form 10-K, Organization note](https://www.sec.gov/Archives/edgar/data/1996810/000199681026000015/gev-20251231.htm).

## Insider purchases
- Insider purchases: not known. The saved filing list does not establish a complete Form 4 review window, so this run cannot determine whether insiders made open-market purchases.

## Liquidity — GEV worksheet company
- Client purchase: 1000000 USD [rule id=purchase_size_usd]
- Lookback: 20 completed trading days [rule id=lookback_days]
- Maximum participation: 0.1 [rule id=max_volume_participation]
- Liquidity bar: 2026-10-20 | dollar_volume=392355076.05 [calc id=daily_dollar_volume ticker=GEV reader=target]
- Liquidity bar: 2026-10-21 | dollar_volume=643050514.08 [calc id=daily_dollar_volume ticker=GEV reader=target]
- Liquidity bar: 2026-10-22 | dollar_volume=786384932.52 [calc id=daily_dollar_volume ticker=GEV reader=target]
- Liquidity bar: 2026-10-23 | dollar_volume=512804520.0 [calc id=daily_dollar_volume ticker=GEV reader=target]
- Liquidity bar: 2026-10-26 | dollar_volume=464723515.20 [calc id=daily_dollar_volume ticker=GEV reader=target]
- Liquidity bar: 2026-10-27 | dollar_volume=606356729.64 [calc id=daily_dollar_volume ticker=GEV reader=target]
- Liquidity bar: 2026-10-28 | dollar_volume=840261539.55 [calc id=daily_dollar_volume ticker=GEV reader=target]
- Liquidity bar: 2026-10-29 | dollar_volume=506559266.10 [calc id=daily_dollar_volume ticker=GEV reader=target]
- Liquidity bar: 2026-10-30 | dollar_volume=597328875.91 [calc id=daily_dollar_volume ticker=GEV reader=target]
- Liquidity bar: 2026-11-02 | dollar_volume=447055068.75 [calc id=daily_dollar_volume ticker=GEV reader=target]
- Liquidity bar: 2026-11-03 | dollar_volume=468832001.8 [calc id=daily_dollar_volume ticker=GEV reader=target]
- Liquidity bar: 2026-11-04 | dollar_volume=995897281.17 [calc id=daily_dollar_volume ticker=GEV reader=target]
- Liquidity bar: 2026-11-05 | dollar_volume=1021250134.71 [calc id=daily_dollar_volume ticker=GEV reader=target]
- Liquidity bar: 2026-11-06 | dollar_volume=840824348.02 [calc id=daily_dollar_volume ticker=GEV reader=target]
- Liquidity bar: 2026-11-09 | dollar_volume=695426470.20 [calc id=daily_dollar_volume ticker=GEV reader=target]
- Liquidity bar: 2026-11-10 | dollar_volume=745858873.44 [calc id=daily_dollar_volume ticker=GEV reader=target]
- Liquidity bar: 2026-11-11 | dollar_volume=417271681.28 [calc id=daily_dollar_volume ticker=GEV reader=target]
- Liquidity bar: 2026-11-12 | dollar_volume=420127643.04 [calc id=daily_dollar_volume ticker=GEV reader=target]
- Liquidity bar: 2026-11-13 | dollar_volume=397640906.82 [calc id=daily_dollar_volume ticker=GEV reader=target]
- Liquidity bar: 2026-11-16 | dollar_volume=484627952.59 [calc id=daily_dollar_volume ticker=GEV reader=target]
- Median daily dollar volume: 555066697.955 USD [calc id=median_dollar_volume ticker=GEV reader=target as_of=2026-11-16]
- Liquidity result: supported for the client purchase under the course rule.
- Reader caveat: LSEG fields use the user's stated interpretation; no independent exchange comparison was completed. The 2026-11-17 zero-volume observation is excluded; the completed observations end on 2026-11-16.

## Not known
- The actual amount of debt, if any, drawn at the closing of the spin is not established by the Information Statement. It reports pro forma total debt and planned facilities, but the planned facilities were not expected to be used at closing.
- The final allocation of the general operating cash contribution is not itemized. The latest annual filing records cash contributed for future operations and restricted cash, and the original Information Statement explains the planned target and legal-matter cash.
- Insider open-market purchase activity and the complete Form 4 review period.
- Exact agreement-level exposure under all remaining GE credit-support contracts; the Information Statement says maximum aggregate exposure cannot be reasonably estimated.
- Price and volume have not been independently checked against an exchange source.

## Live release view — TSN
- Live company: TSN. Earnings Form 8-K accession 000010049326000077; accepted 2026-11-16T12:41:53+00:00. View recorded 2026-11-17T21:38:18.689502+00:00; it was outside the required response window and after the first post-filing close.
- FY2026 sales: 56,419,000,000 USD, historical FY2026 ended 2026-10-03 [filing file="TSN_EX-99.1_0000100493-26-000077.txt" line=13 section="FY2026 earnings release results table" tag=historical period="FY2026 ended 2026-10-03" source_run=live scale=1000000]
- Live Dated market price: 58.82 USD per share on 2026-11-13 [price ticker=TSN date=2026-11-13 reader=live]
- Live After-tax earnings: 453,000,000 USD, historical FY2026 net income attributable to Tyson [filing file="TSN_10-K_0000100493-26-000079.txt" line=1005 section="Consolidated Statements of Income" tag=historical period="FY2026 ended 2026-10-03" source_run=live scale=1000000]
- Live PPE depreciation component: 1,167,000,000 USD, historical FY2026 [filing file="TSN_10-K_0000100493-26-000079.txt" line=1116 section="Consolidated Statements of Cash Flows" tag=historical period="FY2026 ended 2026-10-03" source_run=live scale=1000000]
- Live intangible amortization component: 231,000,000 USD, historical FY2026 [filing file="TSN_10-K_0000100493-26-000079.txt" line=1117 section="Consolidated Statements of Cash Flows" tag=historical period="FY2026 ended 2026-10-03" source_run=live scale=1000000]
- Live Depreciation: 1,398,000,000 USD, historical FY2026; depreciation plus amortization [calc id=live_depreciation_and_amortization]
- Live Capital spending: 770,000,000 USD, historical FY2026 additions to property, plant and equipment; filing presents the outflow in parentheses [filing file="TSN_10-K_0000100493-26-000079.txt" line=1131 section="Consolidated Statements of Cash Flows" tag=historical period="FY2026 ended 2026-10-03" source_run=live sign=magnitude scale=1000000]
- Live Diluted shares: 354,000,000 shares, historical FY2026 diluted weighted-average shares [filing file="TSN_10-K_0000100493-26-000079.txt" line=1599 section="Note 11, Earnings Per Share" tag=historical period="FY2026 ended 2026-10-03" source_run=live scale=1000000]
- Live Owner cash flow: 1081000000 USD [calc id=live_owner_cash_flow]
- Live Low case equity value: 10810000000 USD [calc id=live_low_equity_value]
- Live Low case value per share: 30.53672316384180790960451977 USD per share [calc id=live_low_value_per_share]
- Live Mid case equity value: 15751714285.71428571428571429 USD [calc id=live_mid_equity_value]
- Live Mid case value per share: 44.49636803874092009685230025 USD per share [calc id=live_mid_value_per_share]
- Live margin of safety: -48.08445568881025516898245534% [calc id=live_margin_of_safety]
- View: less than price. The deciding number is the negative margin of safety against the low case.
- Conviction: low under the course price rule because the market price is above the low-case value.
- Evidence that would change the TSN view: a later filing that changes net income attributable to Tyson, depreciation and amortization, capital spending, diluted shares, or the low-case margin test.

## Liquidity — TSN live-release company
- Client purchase: 1000000 USD [rule id=purchase_size_usd]
- Lookback: 20 completed trading days before the release [rule id=lookback_days]
- Maximum participation: 0.1 [rule id=max_volume_participation]
- Liquidity bar: 2026-10-19 | dollar_volume=41706198.0 [calc id=daily_dollar_volume ticker=TSN reader=live]
- Liquidity bar: 2026-10-20 | dollar_volume=53265868.50 [calc id=daily_dollar_volume ticker=TSN reader=live]
- Liquidity bar: 2026-10-21 | dollar_volume=76537888.7 [calc id=daily_dollar_volume ticker=TSN reader=live]
- Liquidity bar: 2026-10-22 | dollar_volume=67405719.42 [calc id=daily_dollar_volume ticker=TSN reader=live]
- Liquidity bar: 2026-10-23 | dollar_volume=47976308.1 [calc id=daily_dollar_volume ticker=TSN reader=live]
- Liquidity bar: 2026-10-26 | dollar_volume=50028661.2 [calc id=daily_dollar_volume ticker=TSN reader=live]
- Liquidity bar: 2026-10-27 | dollar_volume=43668361.75 [calc id=daily_dollar_volume ticker=TSN reader=live]
- Liquidity bar: 2026-10-28 | dollar_volume=50550821.44 [calc id=daily_dollar_volume ticker=TSN reader=live]
- Liquidity bar: 2026-10-29 | dollar_volume=70835400.00 [calc id=daily_dollar_volume ticker=TSN reader=live]
- Liquidity bar: 2026-10-30 | dollar_volume=71631117.20 [calc id=daily_dollar_volume ticker=TSN reader=live]
- Liquidity bar: 2026-11-02 | dollar_volume=62572637.16 [calc id=daily_dollar_volume ticker=TSN reader=live]
- Liquidity bar: 2026-11-03 | dollar_volume=68706063.36 [calc id=daily_dollar_volume ticker=TSN reader=live]
- Liquidity bar: 2026-11-04 | dollar_volume=88205260.59 [calc id=daily_dollar_volume ticker=TSN reader=live]
- Liquidity bar: 2026-11-05 | dollar_volume=95094500.88 [calc id=daily_dollar_volume ticker=TSN reader=live]
- Liquidity bar: 2026-11-06 | dollar_volume=67824350.56 [calc id=daily_dollar_volume ticker=TSN reader=live]
- Liquidity bar: 2026-11-09 | dollar_volume=73878382.60 [calc id=daily_dollar_volume ticker=TSN reader=live]
- Liquidity bar: 2026-11-10 | dollar_volume=78571194.09 [calc id=daily_dollar_volume ticker=TSN reader=live]
- Liquidity bar: 2026-11-11 | dollar_volume=68073507.14 [calc id=daily_dollar_volume ticker=TSN reader=live]
- Liquidity bar: 2026-11-12 | dollar_volume=52782052.36 [calc id=daily_dollar_volume ticker=TSN reader=live]
- Liquidity bar: 2026-11-13 | dollar_volume=110276265.38 [calc id=daily_dollar_volume ticker=TSN reader=live]
- Median daily dollar volume: 67948928.85 USD [calc id=median_dollar_volume ticker=TSN reader=live as_of=2026-11-13]
- Liquidity result: supported for the client purchase under the course rule.
- Reader caveat: LSEG fields use the user's stated interpretation; no independent exchange comparison was completed.
