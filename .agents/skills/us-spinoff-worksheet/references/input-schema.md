# Worksheet input schema

`worksheet_math.py` accepts one JSON object with these fields. Put every amount in whole USD or shares. Keep each source on the same input as its value.

```json
{
  "as_of": "YYYY-MM-DD",
  "inputs": {
    "after_tax_earnings": {
      "value": "0",
      "tag": "historical",
      "period": "FY2026",
      "filing": "saved filing accession or URL",
      "section": "Consolidated Statements of Operations",
      "line": 1
    },
    "depreciation": {
      "value": "0",
      "tag": "historical",
      "period": "FY2026",
      "filing": "saved filing accession or URL",
      "section": "Consolidated Statements of Cash Flows",
      "line": 1
    },
    "capital_spending": {
      "value": "0",
      "tag": "historical",
      "period": "FY2026",
      "filing": "saved filing accession or URL",
      "section": "Consolidated Statements of Cash Flows",
      "line": 1
    },
    "diluted_shares": {
      "value": "0",
      "tag": "historical",
      "period": "as of YYYY-MM-DD",
      "filing": "saved filing accession or URL",
      "section": "Cover page or diluted shares note",
      "line": 1
    },
    "market_price": {
      "value": "0",
      "date": "YYYY-MM-DD",
      "reader_source": "reader bars file",
      "basis": "official_unadjusted"
    }
  },
  "bars_file": "C:/path/outside/the/repository/ticker-bars.json",
  "material_unknowns": []
}
```

The zeroes above are schema placeholders. They are not company data. Replace them with sourced amounts, or leave the input absent so the calculator prints `not known` or `not computed`. Do not submit this sample directly to the calculator.

For Q2 or Q3 Form 10-Q cash flow, enter the quarter amount after subtracting the prior cumulative year-to-date amount from the current cumulative amount. Keep both source lines in the worksheet and show that subtraction. The calculator receives the resulting quarter amount only after the worksheet agent has verified it from the filing.

`bars_file` points to the JSON output from `read_workspace_bars.py`. Keep it outside the repository. The calculator selects the latest `lookback_days` observations on or before `as_of`. It rejects missing volume, duplicate dates, when-issued bars, or a non-official basis. It does not infer trading days or fill gaps. The calculation output contains the dated daily dollar volumes and median, but not the raw close and volume series.
