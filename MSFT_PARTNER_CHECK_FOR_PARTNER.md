# Lab 2 and Lab 3 peer-check notes — MSFT

**Report reviewed:** [MSFT run](https://github.com/WSDx07/Equity-Research-Report---AI-analyst-buddy/tree/main/equity_research_runs/MICROSOFT_CORP_2026-11-01_19-48-53_207067_-0500).

**Draft review:** prepared with AI support from the saved SEC filings. Confirm the cited lines before sending. The partner has not yet verified these marks.

**Lab 2 marks:** Step 5 right for the calculations, with the price-source caveat; Step 6 wrong/incomplete because the output omitted the revenue line.

**Lab 3 marks:** 0 wrong, 0 unsupported, 1 missing (Claim 9), and 1 correct (Claim 11).

## Lab 2: Two checklist marks

| Checklist mark | Result | Filing evidence |
| --- | --- | --- |
| Step 5: ratios are right, with a price caveat | **Right for the calculations reviewed.** Revenue growth, operating margin, return on average equity, debt/equity, free cash flow, and P/E arithmetic recalculate from the report's inputs. The `$521.91` price is an input. Its date and source are not identified, so the price itself is unverified. | MSFT FY2026 10-K, accession `0001193125-26-323660`: the source states values in millions (saved line 772). Revenue `$331,839m` / prior-year `$281,724m` (lines 779 and 781), operating income `$155,237m` (line 788), net income `$133,749m` (line 792), and diluted EPS `$17.95` (line 796). Balance sheet: current debt `$9,227m` (lines 1570-1571), noncurrent debt `$31,067m` (lines 1588-1589), and equity `$442,387m` / `$343,479m` (lines 1622-1624). Cash flow: operating cash `$182,935m` (lines 1719-1720) and additions to property and equipment `$115,948m` (lines 1773-1774). [SEC filing](https://www.sec.gov/Archives/edgar/data/789019/000119312526323660/msft-20260630.htm); [saved 10-K text in the partner's repo](https://github.com/WSDx07/Equity-Research-Report---AI-analyst-buddy/blob/main/equity_research_runs/MICROSOFT_CORP_2026-11-01_19-48-53_207067_-0500/MSFT_10-K_0001193125-26-323660.txt#L772). Calculations: `(331,839 / 281,724) - 1 = 17.79%`; `155,237 / 331,839 = 46.78%`; `133,749 / ((442,387 + 343,479) / 2) = 34.04%`; `(31,067 + 9,227) / 442,387 = 0.0911x`; `182,935 - 115,948 = $66,987m`; `$521.91 / $17.95 = 29.08x`. |
| Step 6: the release lines state quarter revenue and diluted EPS | **Wrong/incomplete as printed.** The report says it found no quarter-revenue line, although Exhibit 99.1 has one. The EPS line was found. Add the revenue line shown below to complete Step 6. | Microsoft Q1 FY2027 earnings release, Exhibit 99.1 to 8-K `0001193125-26-436122`: saved release line 11 says revenue was `$92.3 billion`, up 19%; line 17 says GAAP diluted EPS was `$4.92`, up 32%. [SEC Exhibit 99.1](https://www.sec.gov/Archives/edgar/data/789019/000119312526436122/msft-ex99_1.htm); [saved release text in the partner's repo](https://github.com/WSDx07/Equity-Research-Report---AI-analyst-buddy/blob/main/equity_research_runs/MICROSOFT_CORP_2026-11-01_19-48-53_207067_-0500/MSFT_EX-99.1_0001193125-26-436122.txt#L11). |

## Lab 3: Two MSFT report claims

| Claim | Report says | Filing says | Mark | Source |
| --- | --- | --- | --- | --- |
| 9. Latest-quarter total revenue | No explicit line found; inspect the saved release text | Revenue was `$92.3 billion`, up 19%, for the quarter ended 2026-09-30 | **Missing from the report output.** Add the release figure and cite Exhibit 99.1 line 11. | Exhibit 99.1, accession `0001193125-26-436122`: saved release line 11. [SEC Exhibit 99.1](https://www.sec.gov/Archives/edgar/data/789019/000119312526436122/msft-ex99_1.htm); [saved release text](https://github.com/WSDx07/Equity-Research-Report---AI-analyst-buddy/blob/main/equity_research_runs/MICROSOFT_CORP_2026-11-01_19-48-53_207067_-0500/MSFT_EX-99.1_0001193125-26-436122.txt#L11). |
| 11. Latest-quarter GAAP diluted EPS | `$4.92`, up 32% | `$4.92`, up 32% on a GAAP basis | **Correct.** | Exhibit 99.1, accession `0001193125-26-436122`: saved release line 17. [SEC Exhibit 99.1](https://www.sec.gov/Archives/edgar/data/789019/000119312526436122/msft-ex99_1.htm); [saved release text](https://github.com/WSDx07/Equity-Research-Report---AI-analyst-buddy/blob/main/equity_research_runs/MICROSOFT_CORP_2026-11-01_19-48-53_207067_-0500/MSFT_EX-99.1_0001193125-26-436122.txt#L17). |

**Separate report issue noticed:** the P/E arithmetic uses `$521.91`, but the report does not identify the price date or source. Add both before treating the multiple as source-verified.
