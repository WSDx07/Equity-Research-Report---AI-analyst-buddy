# Microsoft report audit — November 1, 2026 run

**Errors: 0** 

**Missing: 3**



Peer: Shashank

&nbsp;

## Eleven core claims


| #   | Report said                                                                   | Filing says / arithmetic                                                                            | Mark    | Where                                                                                                                                             |
| ---: | ----------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | FY2026 revenue **$331,839 million**                                           | **$331,839 million**.                                                                               | Correct | 10-K income statement, saved text line 1381; `RevenueFromContractWithCustomerExcludingAssessedTax`; 2026-06-30.                                   |
| 2   | Revenue growth **17.79%**                                                     | `(331,839 − 281,724) ÷ 281,724 × 100 = 17.7887%`.                                                   | Correct | Same 10-K, lines 1381–1382; years ended 2026-06-30 and 2025-06-30.                                                                                |
| 3   | Operating income **$155,237 million**; margin **46.78%**                      | `155,237 ÷ 331,839 × 100 = 46.7808%`. Denominator is total revenue.                                 | Correct | 10-K lines 1381 and 1414; tags `OperatingIncomeLoss` and revenue; FY2026.                                                                         |
| 4   | Net income **$133,749 million**                                               | **$133,749 million**.                                                                               | Correct | 10-K line 1433; `NetIncomeLoss`; FY2026.                                                                                                          |
| 5   | GAAP diluted EPS **$17.95/share**                                             | **$17.95/share**.                                                                                   | Correct | 10-K line 1448; `EarningsPerShareDiluted`; FY2026.                                                                                                |
| 6   | Return on average equity **34.04%**                                           | `133,749 ÷ ((442,387 + 343,479) ÷ 2) × 100 = 34.0386%`.                                             | Correct | 10-K net income and balance sheet, saved lines 1433 and 1623–1624; `NetIncomeLoss`, `StockholdersEquity`.                                         |
| 7   | Long-term debt including current **$40,294 million**; debt/equity **0.0911×** | `(31,067 + 9,227) ÷ 442,387 = 0.091083...`.                                                         | Correct | 10-K balance sheet lines 1571, 1589, 1623; `LongTermDebtCurrent`, `LongTermDebtNoncurrent`, `StockholdersEquity`; 2026-06-30.                     |
| 8   | Free cash flow **$66,987 million**                                            | `182,935 − 115,948 = 66,987`. This is the checklist's calculation.                                  | Correct | 10-K cash-flow statement lines 1720 and 1774; `NetCashProvidedByUsedInOperatingActivities`, `PaymentsToAcquirePropertyPlantAndEquipment`; FY2026. |
| 9   | Report says **“no explicit line found”** for quarter revenue.                 | Release reports **$92.3 billion**, approximately $92,300 million, for the quarter ended 2026-09-30. | Missing | 8-K release saved text line 11.                                                                                                                   |
| 10  | No quarterly revenue growth rate stated.                                      | Release reports **19%** year-over-year growth.                                                      | Missing | 8-K release line 11; current versus the comparable 2025 quarter.                                                                                  |
| 11  | GAAP diluted EPS **$4.92/share**                                              | **$4.92/share**, up 32% on a GAAP basis.                                                            | Correct | 8-K release line 17. The separately stated $4.89 is non-GAAP.                                                                                     |




&nbsp;

## Other numbers in the Financial Analyst's part


| Report said                                                                                                  | Filing says / arithmetic                                                                              | Mark    | Where                                                                                                                                                                                                                                |
| ------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------- | ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| FY2025 operating income **$128,528 million**                                                                 | **$128,528 million**.                                                                                 | Correct | 10-K `OperatingIncomeLoss`, saved line 1415.                                                                                                                                                                                         |
| FY2025 net income **$101,832 million**                                                                       | **$101,832 million**.                                                                                 | Correct | 10-K `NetIncomeLoss`, line 1435.                                                                                                                                                                                                     |
| FY2025 diluted EPS **$13.64/share**                                                                          | **$13.64/share**.                                                                                     | Correct | 10-K `EarningsPerShareDiluted`, line 1450.                                                                                                                                                                                           |
| FY2025 noncurrent long-term debt **$40,152 million**                                                         | **$40,152 million**.                                                                                  | Correct | 10-K balance sheet, `LongTermDebtNoncurrent`, line 1590.                                                                                                                                                                             |
| FY2025 current long-term debt **$2,999 million**                                                             | **$2,999 million**.                                                                                   | Correct | 10-K balance sheet, `LongTermDebtCurrent`, line 1572.                                                                                                                                                                                |
| FY2025 cash from operations **$136,162 million**                                                             | **$136,162 million**.                                                                                 | Correct | 10-K cash-flow statement, line 1721.                                                                                                                                                                                                 |
| FY2025 additions to property and equipment **$64,551 million**                                               | Outflow **($64,551 million)**; report uses its positive magnitude.                                    | Correct | 10-K cash-flow statement, line 1776.                                                                                                                                                                                                 |
| Quarter GAAP diluted EPS growth **32%**; non-GAAP EPS **$4.89**, up **18%**, or **19%** in constant currency | Release states all four figures, identifying the latter three as non-GAAP/constant-currency measures. | Correct | October 28, 2026 8-K release line 17. These do not replace claim 11's GAAP EPS.                                                                                                                                                      |
| GOOGL operating margin **32.032638...%**                                                                     | `$129,039m ÷ $402,836m × 100 = 32.0326%`.                                                             | Correct | [Alphabet FY2025 10-K](https://www.sec.gov/Archives/edgar/data/1652044/000165204426000018/goog-20251231.htm), accession 0001652044-26-000018, filed February 5, 2026; year ended 2025-12-31; tags `OperatingIncomeLoss`, `Revenues`. |
| AMZN operating margin **11.155296...%**                                                                      | `$79,975m ÷ $716,924m × 100 = 11.1553%`; denominator is total net sales.                              | Correct | [Amazon FY2025 10-K](https://www.sec.gov/Archives/edgar/data/1018724/000101872426000004/amzn-20251231.htm), accession 0001018724-26-000004, filed February 6, 2026; year ended 2025-12-31.                                           |
| ORCL operating margin **30.592217...%**                                                                      | `$20,606m ÷ $67,357m × 100 = 30.5922%`.                                                               | Correct | [Oracle FY2026 10-K](https://www.sec.gov/Archives/edgar/data/1341439/000119312526277521/orcl-20260531.htm), accession 0001193125-26-277521, filed June 22, 2026; year ended 2026-05-31.                                              |
| Price input **$521.91/share**, date/source unspecified in report                                             | **$521.91** as Friday, **October 30, 2026** close.                                                    | Correct | User-supplied input                                                                                                                                                                                                                  |
| P/E **29.0758×**                                                                                             | `$521.91 ÷ $17.95 = 29.0758×`, using Friday's close and FY2026 diluted EPS.                           | Correct | 10-K EPS and price source above.                                                                                                                                                                                                     |




&nbsp;

## Report rows


| #              | Report said                                                              | Checklist requirement                                                          | Mark    | Where                                                                                            |
| -------------- | ------------------------------------------------------------------------ | ------------------------------------------------------------------------------ | ------- | ------------------------------------------------------------------------------------------------ |
| Template       | All five headings present.                                               | Five named sections present.                                                   | Correct | Report headings.                                                                                 |
| Recommendation | **Insufficient evidence**; no Buy, Hold, or Sell and no deciding number. | Buy, Hold, or Sell names a stated number, and the thesis uses correct numbers. | Missing | Investment Recommendation section. An abstention is honest but does not meet this checklist row. |


