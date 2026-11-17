"""Calculate close-to-close reactions for timestamped earnings releases with WRDS CRSP.

The CRSP pull stays in memory. This script does not save raw prices or event data.
Release timestamps are interpreted as America/New_York local time, as shown by EDGAR.

Access note (checked 2026-11-16): the CRSP daily-stock libraries available to the
current WRDS account end on 2025-12-31. This is an observed account/data-access limit,
not a claim that all WRDS CRSP data ends on that date. The March and May 2026 Costco
events therefore have no post-event closes in this account's current extract.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path
from statistics import median
from zoneinfo import ZoneInfo

import pandas as pd


EASTERN = ZoneInfo("America/New_York")


def read_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$", line)
        if match and not match.group(1).startswith("#"):
            values[match.group(1)] = match.group(2).strip("\"'")
    return values


def pgpass_username() -> str | None:
    """Use only the username from a standard WRDS pgpass entry, never its password."""
    appdata = os.environ.get("APPDATA")
    if not appdata:
        return None
    path = Path(appdata) / "postgresql" / "pgpass.conf"
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        # WRDS credentials are host:port:database:username:password. The first four
        # fields are enough; do not parse, print, or retain the password.
        fields = line.split(":", 4)
        if (
            len(fields) == 5
            and fields[0] in {"wrds-pgdata.wharton.upenn.edu", "*"}
            and fields[1] in {"9737", "*"}
            and fields[2] in {"wrds", "*"}
            and fields[3]
        ):
            return fields[3]
    return None


def parse_event(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Invalid event time {value!r}; use YYYY-MM-DDTHH:MM:SS"
        ) from exc
    if parsed.tzinfo is not None:
        return parsed.astimezone(EASTERN)
    return parsed.replace(tzinfo=EASTERN)


def column_names(db, library: str, table: str) -> set[str]:
    description = db.describe_table(library=library, table=table)
    name_column = next((col for col in description.columns if col.lower() == "name"), None)
    if name_column is None:
        raise RuntimeError(f"Could not inspect columns for {library}.{table}")
    return {str(value).lower() for value in description[name_column].dropna()}


def choose_table(db, library: str, candidates: list[str]) -> tuple[str, set[str]]:
    available = set(db.list_tables(library=library))
    for table in candidates:
        if table in available:
            return table, column_names(db, library, table)
    raise RuntimeError(
        f"None of the expected CRSP tables exist in {library}: {', '.join(candidates)}"
    )


def choose_crsp_library(db) -> str:
    libraries = set(db.list_libraries())
    # Prefer quarterly stock data when the user's WRDS account exposes it.
    for library in ("crsp_q_stock", "crsp", "crsp_a_stock"):
        if library not in libraries:
            continue
        tables = set(db.list_tables(library=library))
        if {"dsf_v2", "stksecurityinfohist"}.issubset(tables) or {
            "dsf",
            "stocknames",
        }.issubset(tables):
            return library
    raise RuntimeError(
        "No CRSP daily-stock library with security history is available to this WRDS account. "
        "Check access to the quarterly CRSP Stock product."
    )


def resolve_permno(
    db, library: str, ticker: str, events: list[datetime], override: int | None
) -> int:
    if override is not None:
        return override

    table, cols = choose_table(db, library, ["stksecurityinfohist", "stocknames"])
    if table == "stksecurityinfohist":
        ticker_col, permno_col = "ticker", "permno"
        start_col, end_col = "secinfostartdt", "secinfoenddt"
    else:
        ticker_col, permno_col = "ticker", "permno"
        start_col, end_col = "namedt", "nameendt"
    required = {ticker_col, permno_col, start_col, end_col}
    if not required.issubset(cols):
        raise RuntimeError(f"Unexpected columns in {library}.{table}; expected {sorted(required)}")

    start = min(event.date() for event in events).isoformat()
    end = max(event.date() for event in events).isoformat()
    query = f"""
        select distinct {permno_col} as permno
        from {library}.{table}
        where upper({ticker_col}) = '{ticker}'
          and {start_col}::date <= '{end}'::date
          and coalesce({end_col}::date, '9999-12-31'::date) >= '{start}'::date
    """
    result = db.raw_sql(query)
    permnos = sorted({int(value) for value in result["permno"].dropna().tolist()})
    if len(permnos) != 1:
        raise RuntimeError(
            f"Ticker {ticker} maps to {len(permnos)} CRSP PERMNOs in the event window: "
            f"{permnos}. Supply --permno after confirming the primary common stock."
        )
    return permnos[0]


def load_daily_closes(
    db, library: str, permno: int, events: list[datetime]
) -> dict[date, float]:
    table, cols = choose_table(db, library, ["dsf_v2", "dsf"])
    if table == "dsf_v2":
        day_col, price_col = "dlycaldt", "dlyprc"
    else:
        day_col, price_col = "date", "prc"
    required = {"permno", day_col, price_col}
    if not required.issubset(cols):
        raise RuntimeError(f"Unexpected columns in {library}.{table}; expected {sorted(required)}")

    first = min(event.date() for event in events) - timedelta(days=10)
    last = max(event.date() for event in events) + timedelta(days=10)
    query = f"""
        select {day_col}::date as close_date, {price_col} as crsp_price
        from {library}.{table}
        where permno = {int(permno)}
          and {day_col}::date between '{first.isoformat()}'::date and '{last.isoformat()}'::date
        order by {day_col}
    """
    rows = db.raw_sql(query)
    closes: dict[date, float] = {}
    for _, row in rows.iterrows():
        if pd.isna(row["crsp_price"]):
            continue
        close_date = pd.Timestamp(row["close_date"]).date()
        # CRSP's legacy PRC can be negative when it represents a bid/ask midpoint.
        closes[close_date] = abs(float(row["crsp_price"]))
    if not closes:
        raise RuntimeError(f"No CRSP daily prices returned for PERMNO {permno}")
    return closes


def calculate_rows(events: list[datetime], closes: dict[date, float]) -> list[dict[str, object]]:
    dated_closes = sorted(closes.items())
    output: list[dict[str, object]] = []
    for event in events:
        # CRSP daily data has a date, not a close timestamp. For these regular-session
        # release observations, use the standard 4:00 p.m. Eastern close timestamp.
        before = [
            (day, price)
            for day, price in dated_closes
            if datetime.combine(day, time(16, 0), tzinfo=EASTERN) < event
        ]
        after = [
            (day, price)
            for day, price in dated_closes
            if datetime.combine(day, time(16, 0), tzinfo=EASTERN) > event
        ]
        if not before or not after:
            if not dated_closes:
                reason = "no CRSP daily closes were returned"
            elif not after and max(day for day, _ in dated_closes) < event.date():
                reason = f"no post-event close; CRSP coverage ends {dated_closes[-1][0]}"
            else:
                side = "pre-event" if not before else "post-event"
                reason = f"missing {side} close in the returned CRSP data"
            output.append(
                {
                    "accepted": event,
                    # Do not present an old, non-paired close as the event's pre-close.
                    "pre_date": None,
                    "pre_close": None,
                    "post_date": None,
                    "post_close": None,
                    "reaction_pct": None,
                    "reason": reason,
                }
            )
            continue
        pre_date, pre_price = before[-1]
        post_date, post_price = after[0]
        reaction = (post_price / pre_price - 1.0) * 100.0
        output.append(
            {
                "accepted": event,
                "pre_date": pre_date,
                "pre_close": pre_price,
                "post_date": post_date,
                "post_close": post_price,
                "reaction_pct": reaction,
                "reason": None,
            }
        )
    return output


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Calculate release reactions from EDGAR Accepted times and WRDS CRSP closes."
    )
    parser.add_argument("--ticker", required=True, help="CRSP ticker, for example COST")
    parser.add_argument(
        "--event",
        action="append",
        required=True,
        type=parse_event,
        help="EDGAR Accepted timestamp in Eastern time: YYYY-MM-DDTHH:MM:SS; repeat per event",
    )
    parser.add_argument("--permno", type=int, help="Optional confirmed CRSP PERMNO override")
    parser.add_argument(
        "--env",
        type=Path,
        default=Path(".env"),
        help="Optional project env file; reads WRDS_USERNAME only, never a password",
    )
    args = parser.parse_args()

    ticker = args.ticker.upper()
    if not re.fullmatch(r"[A-Z0-9.-]+", ticker):
        parser.error("Ticker must contain only letters, digits, dots, or hyphens")
    events = sorted(args.event)
    if len(events) != len(set(events)):
        parser.error("Duplicate event timestamps were supplied")

    try:
        import wrds
    except ImportError:
        print(
            "The wrds package is missing. Install it with: "
            ".\\.venv\\Scripts\\python.exe -m pip install wrds",
            file=sys.stderr,
        )
        return 2

    username = (
        read_dotenv(args.env).get("WRDS_USERNAME")
        or os.environ.get("WRDS_USERNAME")
        or pgpass_username()
    )
    try:
        db = wrds.Connection(wrds_username=username) if username else wrds.Connection()
    except Exception as exc:
        print(f"WRDS connection failed: {exc}", file=sys.stderr)
        return 2

    try:
        library = choose_crsp_library(db)
        permno = resolve_permno(db, library, ticker, events, args.permno)
        closes = load_daily_closes(db, library, permno, events)
        rows = calculate_rows(events, closes)
    except Exception as exc:
        print(f"Could not calculate the event rows: {exc}", file=sys.stderr)
        return 2
    finally:
        db.close()

    try:
        print(
            f"Ticker: {ticker}; CRSP PERMNO: {permno}; "
            f"source: WRDS {library} daily closes"
        )
        if closes:
            print(f"CRSP daily-close coverage returned: {min(closes)} to {max(closes)}")
        print("Accepted (Eastern) | Pre close date | Pre close USD | Post close date | Post close USD | Reaction %")
        for row in rows:
            accepted = row["accepted"].strftime("%Y-%m-%d %H:%M:%S")
            if row["reaction_pct"] is None:
                pre_date = row["pre_date"] or "NA"
                pre_close = f"{row['pre_close']:.2f}" if row["pre_close"] is not None else "NA"
                print(
                    f"{accepted} | {pre_date} | {pre_close} | NA | NA | NA "
                    f"({row['reason']})"
                )
            else:
                print(
                    f"{accepted} | {row['pre_date']} | {row['pre_close']:.2f} | "
                    f"{row['post_date']} | {row['post_close']:.2f} | {row['reaction_pct']:+.2f}"
                )
        complete = [row for row in rows if row["reaction_pct"] is not None]
        if len(complete) != len(events):
            print(
                f"Median absolute reaction: NOT CALCULATED "
                f"({len(complete)} of {len(events)} events have both closes)."
            )
            if closes and max(closes) == date(2025, 12, 31):
                print(
                    "This WRDS account's observed CRSP daily data ends on 2025-12-31. "
                    "Current-quarter CRSP access is needed for the missing 2026 closes."
                )
            elif closes:
                print(
                    f"The returned CRSP daily data ends on {max(closes)}; "
                    "check access or coverage for the missing closes."
                )
            else:
                print("No CRSP daily-close dates were returned; check the account's data access.")
            print("Run completed with a coverage gap; this is not an eight-event base rate.")
            return 0
        absolute_reactions = [abs(float(row["reaction_pct"])) for row in complete]
        print(f"Median absolute reaction: {median(absolute_reactions):.2f}% (n={len(rows)})")
        return 0
    except BrokenPipeError:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
