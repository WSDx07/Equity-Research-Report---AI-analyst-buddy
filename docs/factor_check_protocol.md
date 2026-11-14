# Spinoff factor check: initial protocol

This file records the first proposed check before this implementation reads any historical return data. The team chose the factor check as its Lab 07 ownership project. This is a starting protocol, not proof that the team has never seen relevant historical returns or that an external preregistration occurred.

## Question and fixed comparison

Do spinoffs that satisfy all three active screen thresholds have a higher average benchmark-adjusted return than spinoffs that satisfy none of them?

The single primary comparison is the average benchmark-adjusted return of the 75-point group minus that of the zero-point group. The 25- and 50-point groups are reported as counts but are excluded from this comparison. Each eligible spinoff receives equal weight. The direction hypothesized in advance is a positive difference. This is one comparison, not three separate tests of the individual factors.

The active thresholds are copied from `spinoff_factors.json` as it stood on 2026-11-14: market capitalization at or below USD 2 billion; price decline from the first regular-way close strictly after distribution at or above 15%; and insider ownership at or above 5%. Each passing factor contributes 25 points. Analyst coverage has zero weight and is not a tested factor. All three inputs must be known; do not score a missing input as a failure.

## Proposed historical design

- Universe: U.S.-listed corporate spinoffs with completed distribution dates from 2016-01-01 through 2023-12-31, inclusive. Identify the universe and delistings with WRDS data and filing evidence. WRDS access and adequate field coverage are not yet established.
- First close: the first regular-way close strictly after the distribution date. Exclude when-issued observations.
- Signal: calculate the factors at the close of the twentieth trading session after distribution. The first close above is session one. Use only share counts, insider ownership and other facts publicly available by that signal close. If a point-in-time fact cannot be established, exclude the case from scoring and record why.
- Entry: the close of the next trading session after the signal. Exit: the close 63 trading sessions after entry. Account for dividends, splits, other distributions and delistings using a documented total-return series; do not assume a missing delisting return is zero.
- Benchmark: SPY total return over each stock's same entry and exit dates. Benchmark-adjusted return is the stock total return minus the SPY total return over that interval. Identify the licensed source and dates for both series.
- Eligibility: require confirmed distribution, regular-way identity, point-in-time factors, entry and exit or documented delisting treatment, and benchmark data. Print all exclusions by reason. Do not silently drop bankruptcies or delistings.
- Report: sample dates, source and retrieval date, eligible and excluded counts, counts in each score group, group means, the one primary difference, and the actual number of comparisons. Report insufficient data if either primary group is empty. No significance test, performance claim, or trading recommendation is specified in this first version.

The current demo does **not** implement historical discovery, point-in-time verification, trading calendars, corporate actions, delistings, WRDS, or the benchmark. It uses synthetic inputs only. The entry, holding-period, universe and benchmark choices above are initial design choices, not findings or course-mandated numbers. Freeze and date a final protocol before accessing the selected historical return data; record every later change and any additional comparisons.

## Synthetic demonstration

Run from the project root:

```powershell
.\.venv\Scripts\python.exe scripts\factor_check_demo.py
```

This command has no historical-data input and makes no network requests. Its output is a software demonstration, not investment evidence.
