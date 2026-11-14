# Lab 07 Worksheet Rules

This file gives the worksheet skill the rules and inputs to use. It contains explicit rules and parameter choices for execution. Keep company facts out of this file; the worksheet skill retrieves company facts from SEC filings and the price/volume reader.

## Facts and sources

- Write one fact per line.
- Give each fact's amount or value, currency and unit, reporting period, source filing, and filing section.
- Mark each financial figure as `historical`, `pro forma`, or `reported after the spin`.
- Write `not known` when the filing does not establish a fact.
- Use `not applicable` for spinoff fields only when the selected ticker is not in the seeker's registry.
- Do not estimate facts or let the model calculate numbers.

## Required worksheet sections

1. Facts: parent, distribution ratio, record date, distribution date, and price with its date.
2. Why the company may be cheap, or why the spinoff explanation does not fit.
3. Owner cash flow and value range.
4. Debt raised and where the cash went; liabilities and restrictions left by the parent.
5. The parent after the spin.
6. Insider purchases. Count Form 4 transactions with transaction code `P` only.
7. Liquidity: median daily dollar volume compared with the client's purchase size.
8. Not known: each fact or input the filings and reader do not establish.
9. Live release view: more or less than the price, the one deciding number and its filing or line, and conviction under the rule below.

## 1. Owner cash flow period and units

Use the course formula:

`Owner cash flow = after-tax earnings + depreciation - capital spending`

- Reporting period: Trailing Twelve Months (TTM) or the most recent completed full fiscal year (FY) reported in Form 10, Form 10-K, or the trailing four quarters from Forms 10-Q.
- Currency and scale: USD in whole dollars. When filing tables report figures in thousands or millions, scale each figure to whole USD integers before arithmetic.
- Source statements: Consolidated Statements of Operations (for Net Income / After-Tax Earnings) and Consolidated Statements of Cash Flows (for Depreciation and Amortization under Operating Activities, and Capital Expenditures / Additions to Property, Plant, and Equipment under Investing Activities).
- Form 10-Q Year-to-Date rule: Cash flow statements in Form 10-Q filings report year-to-date (cumulative) amounts. For Q2 or Q3, subtract the prior period's cumulative cash flow figure from the current cumulative figure to determine the single quarter's cash flow:
  `Quarterly Amount = Current YTD Amount - Prior Period YTD Amount`
- Output requirement: Print every input with its exact line item, filing, section, and arithmetic. Label each figure `historical`, `pro forma`, or `reported after the spin`.

## 2. Valuation method

- Method: Capitalized Owner Cash Flow / Gordon Growth Model (Perpetuity DCF).
- Forecast period: Single-period terminal capitalization (0 explicit interim projection years; capitalizes normalized annual owner cash flow directly into perpetuity).
- Rates and definitions:
  - Discount rate ($r$): Required rate of return / cost of equity capital. Represents the return required for the business risk profile.
  - Perpetual growth rate ($g$): Constant annual growth rate of owner cash flow in perpetuity. Represents long-term volume and inflation growth. The discount rate must strictly exceed the perpetual growth rate ($r > g$).
- Value definitions and handling of debt, cash, and shares:
  - The course-defined owner cash flow starts with after-tax earnings. Capitalize it as an equity value using the cost of equity:
    `Equity Value = [Owner cash flow x (1 + g)] / (r - g)`
  - Do not label this result Firm Value or Enterprise Value.
  - Do not add cash or subtract debt from this equity value. Report cash and debt as separate sourced facts in the worksheet. This avoids a second capital-structure adjustment to a value based on after-tax earnings.
  - Per-Share Value: Divide Equity Value by Diluted Common Shares Outstanding from the latest filing statement or cover page to calculate Intrinsic Value Per Share in USD:
    `Value Per Share = Equity Value / Diluted Shares Outstanding`
  - Do not count shares twice. If diluted shares are unavailable, the per-share value is `not computed`.

## 3. Low and mid cases

- Low case (conservative floor):
  - Discount rate ($r$): 10.0% (0.10)
  - Perpetual growth rate ($g$): 0.0% (0.00) (zero growth assumption)
  - Formula: `Equity Value = Owner cash flow / 0.10`
  - Low-Case Value Per Share: `Equity Value / Diluted Shares Outstanding`
  - Result units: USD per share.
- Mid case (base case):
  - Discount rate ($r$): 9.0% (0.09)
  - Perpetual growth rate ($g$): 2.0% (0.02) (long-term inflation/GDP expansion rate)
  - Formula: `Equity Value = [Owner cash flow x (1 + 0.02)] / (0.09 - 0.02) = (Owner cash flow x 1.02) / 0.07`
  - Mid-Case Value Per Share: `Equity Value / Diluted Shares Outstanding`
  - Result units: USD per share.
- Case comparison: The low case is more cautious because it uses a 100-basis-point higher discount rate (10.0% vs. 9.0%) and assumes zero growth (0.0% vs. 2.0%), which yields a lower equity-value capitalization multiple (10.0x vs. 14.57x).
- Computation rule: Print rates, inputs, and arithmetic for both cases. Do not fill missing inputs with estimates. If an input is absent, print `not computed` and report the missing item.
- Comparison: Compare the dated market price with the low-case value per share.

## 4. Purchase size and liquidity period

- Client purchase size: $1,000,000 USD.
- Lookback period: 20 completed trading days.
- Daily dollar volume calculation: Calculate each day's dollar volume as `close x share volume`.
- Median daily dollar volume: Report the median daily dollar volume over the 20-day lookback period.
- Liquidity support condition:
  - Supported if: `$1,000,000 <= 0.10 x median daily dollar volume` (purchase size does not exceed 10.0% of median daily dollar volume).
  - Unsupported if: `$1,000,000 > 0.10 x median daily dollar volume` (purchase size exceeds 10.0% of median daily dollar volume, presenting market-impact risk).
- Missing data rule: If the reader does not return a required close or volume, write `not known` and explain why.

## 5. Conviction rule

- High conviction rule: High Conviction requires all three conditions:
  1. Dated market price <= 0.85 x Low-Case Value Per Share (at least a 15.0% margin of safety against the low-case value).
  2. Client purchase size <= 0.10 x 20-day median daily dollar volume (sufficient liquidity).
  3. Zero debt liabilities, debt covenants, or parent restrictions marked `not known`.
- Low conviction rule: Low Conviction occurs if any of these conditions hold:
  1. Dated market price > 0.85 x Low-Case Value Per Share (margin of safety is below 15.0%, or stock trades at a premium to low-case value).
  2. Client purchase size > 0.10 x 20-day median daily dollar volume (insufficient liquidity).
  3. Any material debt covenant, parent liability, or restriction is marked `not known`.
- One number that decides the live release view: Margin of Safety percentage against Low Case:
  `Margin of Safety = [(Low-Case Value Per Share - Dated Market Price) / Dated Market Price] x 100%`
  - Sourced from Section 3 (Value range) and Section 1 (Dated market price).
  - Decision:
    - If Margin of Safety > 0.0%: the live release view is `more than price`.
    - If Margin of Safety <= 0.0%: the live release view is `less than price`.
- Required missing-price rule: If the required close is unavailable from the reader, the price lines and the live release view must state `not computed`, and conviction must state `not computed`.

## 6. Persona path

- Persona file path: `personas/investment_advisor.md`
- Persona execution: The persona writes the qualitative judgment from sourced filing facts, the value range, and the comparison of market price against the low case. It does not calculate numbers or receive other reader data.
- View transition: The judgment must end with the exact evidence in the next filing that would change the view.

## 7. Missing-data labels (including SportsQuest rule)

- Registry-present companies (including SportsQuest):
  - If a company (such as SportsQuest) is in the seeker's registry, the skill reads its filings.
  - Facts that the filings do not establish (such as parent distribution, distribution date, or distribution ratio) must be labeled `not known`.
  - The skill must never guess or invent missing facts.
- Registry-absent companies:
  - If a ticker is absent from the seeker's registry, the skill labels spinoff-specific fields (parent, distribution ratio, record date, distribution date, parent debt/liabilities pushed down, parent after the spin) as `not applicable`.
  - The skill runs all remaining standard worksheet sections: owner cash flow, value range, debt and liquidity analysis, persona judgment, and live release view.
