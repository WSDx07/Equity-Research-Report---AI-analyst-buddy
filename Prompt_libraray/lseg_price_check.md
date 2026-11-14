# Check one LSEG closing price

This is a candidate field check. The output is not yet verified as an exchange-official, unadjusted, regular-way close. Do not use it in the spinoff screen until its meaning and the relevant instrument are verified.

1. Sign in to LSEG Workspace Desktop.
2. Put your App Key in the project `.env` file as `LSEG_APP_KEY=your_key`. Keep it private. Do not send the key to the chat.
3. In Workspace, identify the regular-way LSEG instrument identifier for the stock you want to check. Also choose a trading date and find the exchange's official closing price for that same stock and date through a permitted source.
4. Open PowerShell in the project folder. Replace `YOUR_INSTRUMENT` and `YYYY-MM-DD` in this command, then run it yourself:

```powershell
& "$env:USERPROFILE\.codex\venvs\us-spinoff-lseg\Scripts\python.exe" .\.agents\skills\us-spinoff-seeker\scripts\closes_reader.py --env .env --ticker "YOUR_INSTRUMENT" --date YYYY-MM-DD
```

5. Compare the output with the exchange's official close for the same security and date. The numbers should match exactly; do not assume a difference is rounding. Tell the agent whether they match and provide the exchange source link. Do not send the App Key or a list of closes.

If the output says `not available`, or the command returns an error, send the error text after checking that it contains no credentials. A single matching observation is a spot check: it does not establish that the entire historical series is official, unadjusted, regular-way, and complete. Further LSEG field and instrument verification is required.

The LSEG environment is separate from the desk's main environment because the libraries require incompatible versions of `httpx`. The candidate field and desktop session follow [LSEG's session guidance](https://developers.lseg.com/en/article-catalog/article/configuration-process) and [LSEG's unadjusted-price field example](https://community.developers.lseg.com/discussion/121346/query-prices-adjustes-and-unadjusted-for-time-series/p1); these do not by themselves verify the official-close definition.

## User-supplied comparison

The user reported that the [Nasdaq historical page](https://www.nasdaq.com/market-activity/stocks/spwr/historical?page=1&rows_per_page=100&timeline=m6) shows the SPWR close on September 2, 2026 as USD 0.2541. The LSEG candidate request matched that value. The agent did not fetch the exchange page. This single comparison does not verify all instruments or the complete series.

## RIC caution

The LSEG developer-community guidance cited in the handoff describes `.O` as consolidated and `.OQ` as Nasdaq-only for the examples discussed. A later `.OQ` test for the same date also matched the user-provided exchange close. For that example the metadata primary flag was true, but the MIC did not match XNAS. Neither a suffix nor one matching close proves a complete official, regular-way series; obtain instrument-specific confirmation.
