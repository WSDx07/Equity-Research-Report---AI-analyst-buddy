# LSEG official-price path (experimental)

The diagnostic CLI accepts `--lseg-evidence PATH` in the isolated LSEG Python environment. PATH is a JSON object keyed by CIK. Each entry needs `cik`, `ticker`, `ric`, `exchange`, `listing_url`, `regular_way` (true), `exchange_url`, `reference_date` (YYYY-MM-DD), and `reference_close`. Use a real issuer SEC filing that explicitly states regular-way trading, ticker, and exchange in one sentence, and a real independently observed listing-exchange close for the same instrument and date. Do not invent evidence. The exchange observation is supplied by the user or obtained from an authorized exchange source; the program does not fetch the exchange page.

The program reads the filing through the SEC client, checks the CIK and a narrow sentence match, and asks LSEG Search for a unique active quote matching the exact ticker, RIC, and exchange. It requests the dated `TR.OFFICIALCLOSEPRICE(Adjusted=0)` series and requires the reference value to match. It rejects missing observations and does not fall back to a field with different semantics. The first close can be marked verified only if a value exists on the first weekday strictly after distribution. This conservative rule leaves holidays, suspensions and other gaps unavailable rather than guessing. The latest eligible close retains its date. The score also requires the other enabled factors. This path is synthetic-tested but has not succeeded with a real spinoff and independently matched exchange observation.

For the Lab 07 liquidity worksheet, `WorkspaceOfficialReader.daily_bars(start, end)` returns one row per observed date with the raw official close and `TR.Volume` share volume. It requests these LSEG fields together:

```python
bars = reader.daily_bars('2026-10-01', '2026-11-13')
# Each row includes date, close, volume, basis='official_unadjusted',
# session='regular', when_issued=False, and the exchange spot-check source.
```

Use `daily_bars` for the 20-day dollar-volume calculation. The method rejects a missing close, date, or volume; a fractional or negative share volume; an invalid date; a duplicate date; and a value outside the requested range. It does not fill missing sessions. `WorkspaceCandidateReader.daily_bars` also returns volume but remains marked `unverified candidate` and is not valid worksheet evidence. A CSV/XLSX `WorkspaceExportReader` needs an explicit `volume` column mapping before `daily_bars` can return bars.

Do not put licensed raw series or credentials in evidence files or the repository. The normal seeker command remains guarded for the other unfinished work. The candidate `TR.CLOSEPRICE(Adjusted=0)` path stays diagnostic and cannot be used as a proven official source.
