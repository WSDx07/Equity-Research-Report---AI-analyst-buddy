"""Run the seeker, equity team, worksheet, and worksheet hook in fixed order."""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUNS = ROOT / "one_desk_runs"
SPINOFF_RUNS = ROOT / "spinoff_runs"
SEEKER = ROOT / ".agents" / "skills" / "us-spinoff-seeker" / "scripts" / "seeker.py"
WORKSHEET = ROOT / ".agents" / "skills" / "us-spinoff-worksheet" / "scripts" / "run_worksheet.py"
GUARD_DIR = ROOT / ".agents" / "skills" / "us-spinoff-worksheet" / "scripts"
TICKER = re.compile(r"^[A-Z0-9][A-Z0-9.\-]{0,14}$")
STAMP = "%Y-%m-%d_%H-%M-%S_%f_%z"


class PartFailure(RuntimeError):
    pass


def latest_registry() -> Path | None:
    matches = list(SPINOFF_RUNS.glob("registry-*.json")) if SPINOFF_RUNS.is_dir() else []
    if RUNS.is_dir():
        matches.extend(RUNS.glob("*/seeker/registry-*.json"))
    matches = sorted((path for path in matches if path.is_file()), key=lambda path: path.stat().st_mtime, reverse=True)
    return matches[0] if matches else None


def latest_report(folder: Path) -> Path | None:
    matches = sorted(folder.glob("spinoff-screen-*.md"), key=lambda path: path.stat().st_mtime, reverse=True) if folder.is_dir() else []
    return matches[0] if matches else None


def pick_screen_ticker(report: Path, cache_folder: Path) -> str | None:
    text = report.read_text(encoding="utf-8")
    match = re.search(r"^## In window, ranked\s*\n\s*1\. ([^|\n]+)\s*\|", text, re.M)
    if not match:
        section = re.search(r"^## In window, ranked\s*\n(.*?)(?=^## |\Z)", text, re.M | re.S)
        if section and section.group(1).strip().rstrip(".").strip() == "None established":
            return None
        raise ValueError("The seeker's latest report has no ranked top name and does not state that the screen is empty")
    name = " ".join(match.group(1).split())
    top_line = next(line for line in text.splitlines() if re.match(r"\s*1\. ", line))
    cik_match = re.search(r"\bCIK:\s*(\d{1,10})\b", top_line)
    import requests
    env_values = {}
    for line in (ROOT / ".env").read_text(encoding="utf-8-sig").splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1); env_values[key.strip()] = value.strip().strip("\"'")
    user_agent = env_values.get("SEC_USER_AGENT", "").strip()
    if not user_agent:
        raise ValueError("SEC_USER_AGENT is missing from .env")
    ticker_map = cache_folder / "company_tickers.json"
    response = requests.get("https://www.sec.gov/files/company_tickers.json", headers={"User-Agent": user_agent}, timeout=30)
    response.raise_for_status()
    ticker_map.write_text(json.dumps(response.json(), indent=2) + "\n", encoding="utf-8")
    records = json.loads(ticker_map.read_text(encoding="utf-8")).values()
    if cik_match:
        cik = cik_match.group(1).zfill(10)
        matches = [str(row.get("ticker", "")).upper() for row in records
                   if str(row.get("cik_str", "")).zfill(10) == cik]
    else:
        matches = [str(row.get("ticker", "")).upper() for row in records
                   if " ".join(str(row.get("title", "")).split()).casefold() == name.casefold()]
    matches = sorted(set(symbol for symbol in matches if TICKER.fullmatch(symbol)))
    if len(matches) != 1:
        raise ValueError(f"Could not map the top name {name!r} to exactly one SEC ticker")
    return matches[0]


def ticker_from_run(team: Path) -> str:
    facts = json.loads((team / "facts.json").read_text(encoding="utf-8"))
    ticker = str((facts.get("company") or {}).get("ticker", "")).upper()
    if not TICKER.fullmatch(ticker):
        raise ValueError("The saved team run does not contain a valid ticker")
    return ticker


def filing_names(run: Path, team: Path, source_dir: Path | None, seeker_registry: Path | None,
                 seeker_read_log: Path | None) -> list[str]:
    names: dict[str, str] = {}
    facts_path = team / "facts.json"
    if facts_path.is_file():
        facts = json.loads(facts_path.read_text(encoding="utf-8"))
        def fact_accessions(value):
            if isinstance(value, dict):
                for key, child in value.items():
                    if key.casefold() in {"accn", "accession", "accessionnumber", "preferred_10k_accession"}:
                        accession = re.sub(r"\D", "", str(child))
                        if re.fullmatch(r"\d{18,20}", accession):
                            names.setdefault(accession, f"XBRL filing {accession}")
                    fact_accessions(child)
            elif isinstance(value, list):
                for child in value:
                    fact_accessions(child)
        fact_accessions(facts)
    for path in (team.glob("*.txt") if team is not None and team.is_dir() else []):
        match = re.search(r"_(10-K|10-Q|8-K|EX-99\.1|Form 10)_([0-9-]{18,20})\.txt$", path.name, re.I)
        if match:
            accession = re.sub(r"\D", "", match.group(2))
            names[accession] = f"{match.group(1)} {accession}"
    manifest = source_dir / "sources.json" if source_dir else None
    if manifest and manifest.is_file():
        data = json.loads(manifest.read_text(encoding="utf-8"))
        for row in data.get("saved_source_documents", []):
            accession = str(row.get("accession", ""))
            if accession:
                compact = re.sub(r"\D", "", accession)
                names[compact] = f"{row.get('form', 'filing')} {compact}"
        release = data.get("live_release") or {}
        if release.get("accession"):
            compact = re.sub(r"\D", "", str(release["accession"]))
            names[compact] = f"{release.get('form', '8-K')} {compact}"
    if seeker_registry and seeker_registry.is_file():
        registry = json.loads(seeker_registry.read_text(encoding="utf-8"))
        def walk(value):
            if isinstance(value, dict):
                url = str(value.get("filing", ""))
                match = re.search(r"/Archives/edgar/data/\d+/(\d{18,20})(?:/|\.)", url)
                if match:
                    accession = match.group(1)
                    names.setdefault(accession, f"SEC filing {accession}")
                for child in value.values():
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)
        walk(registry)
    if seeker_read_log and seeker_read_log.is_file():
        reads = json.loads(seeker_read_log.read_text(encoding="utf-8"))
        for row in reads.get("filings", []):
            accession = re.sub(r"\D", "", str(row.get("accession", "")))
            if accession:
                names.setdefault(accession, f"SEC filing {accession}")
    return sorted(names.values(), key=str.casefold)


def worksheet_hook(report: Path, worksheet: Path, verified: Path, team: Path, rules: Path,
                   seeker_report: Path | None = None) -> None:
    sys.path.insert(0, str(GUARD_DIR))
    import worksheet_guard
    report_text = report.read_text(encoding="utf-8")
    worksheet_text = worksheet.read_text(encoding="utf-8")
    verified_text = verified.read_text(encoding="utf-8")
    marker = "## Worksheet view\n\n"
    if marker not in report_text or report_text.split(marker, 1)[1] != worksheet_text:
        raise ValueError("Final report does not contain the exact saved worksheet output")
    if verified_text not in report_text:
        raise ValueError("Final report does not contain the team's verified report")
    if not report_text.startswith("Filings read: "):
        raise ValueError("Final report first line must name the filings read")
    if seeker_report is not None:
        screen_text = seeker_report.read_text(encoding="utf-8")
        if screen_text.rstrip().splitlines()[-1:] != ["screens, not recommendations"]:
            raise ValueError("Seeker output failed its report-end check")
    issues = worksheet_guard.validate_worksheet(worksheet, run=team, rules_path=rules)
    if issues:
        raise ValueError("Worksheet hook: " + "; ".join(issues[:8]))
    # The final-report hook checks the copied worksheet section with the same
    # guard used for the standalone skill output.
    with (team / "final_report_worksheet_check.md").open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(report_text.split(marker, 1)[1])
    try:
        issues = worksheet_guard.validate_worksheet(team / "final_report_worksheet_check.md", run=team, rules_path=rules)
    finally:
        (team / "final_report_worksheet_check.md").unlink(missing_ok=True)
    if issues:
        raise ValueError("Final report hook: " + "; ".join(issues[:8]))


def empty_screen_hook(report: Path, seeker_report: Path, filings_read: list[str]) -> None:
    screen_text = seeker_report.read_text(encoding="utf-8")
    if screen_text.rstrip().splitlines()[-1:] != ["screens, not recommendations"]:
        raise ValueError("Seeker output failed its report-end check")
    report_text = report.read_text(encoding="utf-8")
    if not report_text.startswith("Filings read: " + (", ".join(filings_read) if filings_read else "none identified") + "\n"):
        raise ValueError("Empty-screen report does not list the filings read")
    marker = "## Seeker report\n\n"
    if marker not in report_text or report_text.split(marker, 1)[1] != screen_text:
        raise ValueError("Empty-screen report does not contain the exact saved seeker output")
    for stage in ("Pick", "Agent team", "Worksheet"):
        if f"## {stage}\n\nNot applicable" not in report_text:
            raise ValueError(f"Empty-screen report does not mark {stage} as not applicable")


def run_command(label: str, command: list[str], *, cwd: Path = ROOT, env: dict | None = None, announce: bool = True) -> tuple[str, float]:
    started = time.perf_counter()
    try:
        chunks: list[str] = []
        proc = subprocess.Popen(
            command,
            cwd=cwd,
            env=env,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            chunks.append(line)
            print(line, end="", flush=True)
        proc.stdout.close()
        return_code = proc.wait()
        output = "".join(chunks)
        if return_code:
            raise RuntimeError(f"exit code {proc.returncode}; {output.strip().splitlines()[-1] if output.strip() else 'no error output'}")
        elapsed = time.perf_counter() - started
        if announce:
            print(f"Part {label}: {elapsed:.2f} seconds", flush=True)
        return output, elapsed
    except Exception as exc:
        elapsed = time.perf_counter() - started
        print(f"FAILED part {label}: {type(exc).__name__}: {exc}", flush=True)
        print(f"Part {label}: {elapsed:.2f} seconds", flush=True)
        raise PartFailure(f"{label}: {type(exc).__name__}: {exc}") from exc


def run(ticker_arg: str, screen_start: str | None) -> Path:
    started_at = datetime.now().astimezone()
    stamp = started_at.strftime(STAMP)
    screen = ticker_arg.casefold() == "screen"
    folder_name = f"SCREEN_{stamp}" if screen else f"{ticker_arg.upper()}_{stamp}"
    run_dir = RUNS / folder_name
    run_dir.mkdir(parents=True, exist_ok=False)
    metadata = {"started_at": started_at.isoformat(), "input": ticker_arg, "parts": [], "run_dir": str(run_dir.resolve())}
    registry = None
    seeker_report = None
    seeker_read_log = None
    current_part = "seeker" if screen else "pick"
    part_started = time.perf_counter()
    try:
        if screen:
            seek_dir = run_dir / "seeker"
            seek_dir.mkdir()
            config = json.loads((ROOT / "spinoff_factors.json").read_text(encoding="utf-8"))
            start_date = date.fromisoformat(screen_start) if screen_start else date.today() - timedelta(days=int(config["window_days"]))
            python = Path.home() / ".codex" / "venvs" / "us-spinoff-lseg" / "Scripts" / "python.exe"
            seeker_python = str(python) if python.is_file() else sys.executable
            seek_output, elapsed = run_command("seeker", [seeker_python, "-u", str(SEEKER), "--start", start_date.isoformat(),
                "--config", str(ROOT / "spinoff_factors.json"), "--env", str(ROOT / ".env"), "--output", str(seek_dir)], announce=False)
            report_match = re.findall(r"^Screen report:\s*(.+?)\s*$", seek_output, re.M)
            registry_match = re.findall(r"^Fact registry:\s*(.+?)\s*$", seek_output, re.M)
            if len(report_match) != 1 or len(registry_match) != 1:
                print("FAILED part seeker: runner did not identify one report and one registry", flush=True)
                print(f"Part seeker: {elapsed:.2f} seconds", flush=True)
                raise PartFailure("seeker did not identify one report and one registry")
            report = Path(report_match[0]).resolve()
            seeker_report = report
            registry = Path(registry_match[0]).resolve()
            seeker_read_log = seek_dir / "filing_reads.json"
            if (not report.is_file() or not registry.is_file() or not seeker_read_log.is_file()
                    or not report.is_relative_to(seek_dir.resolve()) or not registry.is_relative_to(seek_dir.resolve())):
                print("FAILED part seeker: report, registry, or filing-read log is missing or outside the run folder", flush=True)
                print(f"Part seeker: {elapsed:.2f} seconds", flush=True)
                raise PartFailure("seeker report, registry, or filing-read log is invalid")
            try:
                json.loads(seeker_read_log.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                print(f"FAILED part seeker: invalid filing-read log: {exc}", flush=True)
                print(f"Part seeker: {elapsed:.2f} seconds", flush=True)
                raise PartFailure(f"seeker filing-read log is invalid: {exc}") from exc
            metadata["parts"].append({"part": "seeker", "seconds": round(elapsed, 2)})
            print(f"Part seeker: {elapsed:.2f} seconds", flush=True)
            current_part = "pick"
            part_started = time.perf_counter()
            try:
                picked = pick_screen_ticker(report, run_dir / "seeker")
                elapsed = time.perf_counter() - part_started
            except Exception as exc:
                elapsed = time.perf_counter() - part_started
                print(f"FAILED part pick: {type(exc).__name__}: {exc}", flush=True)
                print(f"Part pick: {elapsed:.2f} seconds", flush=True)
                raise PartFailure(f"pick: {type(exc).__name__}: {exc}") from exc
            if picked is None:
                metadata["parts"].append({"part": "pick", "seconds": round(elapsed, 2), "status": "not applicable"})
                (run_dir / "pick.json").write_text(json.dumps({
                    "status": "not applicable",
                    "reason": "The seeker's report has no ranked top name.",
                }, indent=2) + "\n", encoding="utf-8")
                print("Part pick: not applicable (screen has no ranked name)", flush=True)
                print(f"Part pick: {elapsed:.2f} seconds", flush=True)

                for label in ("agent team", "worksheet"):
                    skipped = 0.0
                    metadata["parts"].append({"part": label, "seconds": skipped, "status": "not applicable"})
                    print(f"Part {label}: not applicable (no ticker was selected)", flush=True)
                    print(f"Part {label}: {skipped:.2f} seconds", flush=True)

                filing_list = filing_names(run_dir, None, None, registry, seeker_read_log)
                report_path = run_dir / "final_report.md"
                final_text = (
                    "Filings read: " + (", ".join(filing_list) if filing_list else "none identified") +
                    "\n\n# One Desk report\n\n"
                    "The seeker completed, but its report has no ranked top name. "
                    "No ticker was available for the ticker-dependent stages.\n\n"
                    "## Pick\n\nNot applicable. The screen has no ranked top name.\n\n"
                    "## Agent team\n\nNot applicable. No ticker was selected.\n\n"
                    "## Worksheet\n\nNot applicable. No agent-team run exists without a selected ticker.\n\n"
                    "## Seeker report\n\n" + report.read_text(encoding="utf-8")
                )
                report_path.write_text(final_text, encoding="utf-8")

                current_part = "hook"
                hook_started = time.perf_counter()
                part_started = hook_started
                try:
                    empty_screen_hook(report_path, report, filing_list)
                except Exception as exc:
                    elapsed = time.perf_counter() - hook_started
                    print(f"FAILED part hook: {type(exc).__name__}: {exc}", flush=True)
                    print(f"Part hook: {elapsed:.2f} seconds", flush=True)
                    raise
                elapsed = time.perf_counter() - hook_started
                metadata["parts"].append({"part": "hook", "seconds": round(elapsed, 2)})
                metadata.update(
                    ticker=None,
                    empty_screen=True,
                    report=str(report_path.resolve()),
                    seeker_report=str(report.resolve()),
                    filings_read=filing_list,
                )
                (run_dir / "run.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
                print("Hook: passed on saved seeker output and final report", flush=True)
                print(f"Final report: {report_path.resolve()}", flush=True)
                print(f"Part hook: {elapsed:.2f} seconds", flush=True)
                return report_path
            metadata["parts"].append({"part": "pick", "seconds": round(elapsed, 2), "ticker": picked})
            final_dir = RUNS / f"{picked}_{stamp}"
            run_dir.rename(final_dir)
            run_dir = final_dir
            registry = run_dir / "seeker" / registry.name
            seeker_report = run_dir / "seeker" / report.name
            seeker_read_log = run_dir / "seeker" / "filing_reads.json"
            ticker = picked
            print(f"Part pick: {elapsed:.2f} seconds", flush=True)
        else:
            ticker = ticker_arg.upper()
            if not TICKER.fullmatch(ticker):
                raise ValueError("Enter a valid ticker or the word screen")
            latest = latest_registry()
            if latest:
                (run_dir / "seeker").mkdir()
                registry = run_dir / "seeker" / latest.name
                shutil.copyfile(latest, registry)
            else:
                registry = None
            started_pick = time.perf_counter()
            elapsed = time.perf_counter() - started_pick
            metadata["parts"].append({"part": "pick", "seconds": round(elapsed, 2), "ticker": ticker})
            print(f"Part seeker: not applicable", flush=True)
            print(f"Part seeker: 0.00 seconds", flush=True)
            print(f"Part pick: {elapsed:.2f} seconds", flush=True)

        team = run_dir / "team"
        current_part = "agent team"
        part_started = time.perf_counter()
        env = os.environ.copy(); env.update(PYTHONUTF8="1", PYTHONUNBUFFERED="1")
        team_args = [sys.executable, "-u", str(ROOT / "desk_flow.py"), ticker, "--run-dir", str(team)]
        team_output, elapsed = run_command("agent team", team_args, env=env)
        metadata["parts"].append({"part": "agent team", "seconds": round(elapsed, 2)})
        verified_matches = re.findall(r"^Verified report:\s*(.+?)\s*$", team_output, re.M)
        verified = Path(verified_matches[-1]).resolve() if verified_matches else team / "verified_report.md"
        if not verified.is_file() or not verified.resolve().is_relative_to(team.resolve()):
            raise RuntimeError("agent team did not save a verified report inside the run folder")
        ticker = ticker_from_run(team)

        if registry is None or not registry.is_file():
            registry = run_dir / "seeker_registry.json"
            registry.write_text("{}\n", encoding="utf-8")
        current_part = "worksheet"
        part_started = time.perf_counter()
        worksheet_out, elapsed = run_command("worksheet", [sys.executable, "-u", str(WORKSHEET), "--run", str(team),
            "--registry", str(registry), "--env", str(ROOT / ".env"),
            "--rules", str(ROOT / "lab07_worksheet_rules.md")])
        metadata["parts"].append({"part": "worksheet", "seconds": round(elapsed, 2)})
        worksheet_matches = re.findall(r"^Worksheet:\s*(.+?)\s*$", worksheet_out, re.M)
        if len(worksheet_matches) != 1:
            raise RuntimeError("worksheet runner did not identify exactly one saved worksheet")
        worksheet = Path(worksheet_matches[0]).resolve()
        if not worksheet.is_file() or not worksheet.resolve().is_relative_to(team.resolve()):
            raise RuntimeError("worksheet output is outside the saved team run")
        source_dirs = sorted(team.glob("worksheet_sources_*"), key=lambda path: path.stat().st_mtime, reverse=True)
        source_dir = source_dirs[0] if source_dirs else None

        cik = str((json.loads((team / "facts.json").read_text(encoding="utf-8")).get("company") or {}).get("cik", "")).zfill(10)
        registry_data = json.loads(registry.read_text(encoding="utf-8"))
        if cik not in registry_data:
            print("Spinoff parts: not applicable (ticker is not in the seeker's registry)", flush=True)
        filing_list = filing_names(run_dir, team, source_dir, registry if registry.is_file() else None,
                                   seeker_read_log)
        first_line = "Filings read: " + (", ".join(filing_list) if filing_list else "none identified")
        report_path = run_dir / "final_report.md"
        final_text = first_line + "\n\n# Verified agent-team report\n\n" + verified.read_text(encoding="utf-8").rstrip() + "\n\n## Worksheet view\n\n" + worksheet.read_text(encoding="utf-8")
        report_path.write_text(final_text, encoding="utf-8")
        current_part = "hook"
        hook_started = time.perf_counter()
        part_started = hook_started
        try:
            worksheet_hook(report_path, worksheet, verified, team, ROOT / "lab07_worksheet_rules.md", seeker_report)
        except Exception as exc:
            elapsed = time.perf_counter() - hook_started
            print(f"FAILED part hook: {type(exc).__name__}: {exc}", flush=True)
            print(f"Part hook: {elapsed:.2f} seconds", flush=True)
            raise
        elapsed = time.perf_counter() - hook_started
        metadata["parts"].append({"part": "hook", "seconds": round(elapsed, 2)})
        print(f"Final report: {report_path.resolve()}", flush=True)
        print("Hook: passed on worksheet output and final report", flush=True)
        print(f"Part hook: {elapsed:.2f} seconds", flush=True)
        metadata.update(ticker=ticker, report=str(report_path.resolve()), verified_report=str(verified), worksheet=str(worksheet),
                        seeker_report=str(seeker_report) if seeker_report else None, filings_read=filing_list)
        (run_dir / "run.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
        return report_path
    except Exception as exc:
        metadata["error"] = f"{type(exc).__name__}: {exc}"
        metadata["failed_part"] = current_part
        metadata["failed_part_seconds"] = round(time.perf_counter() - part_started, 2)
        metadata["run_dir"] = str(run_dir.resolve())
        (run_dir / "run.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
        if not isinstance(exc, PartFailure):
            elapsed = time.perf_counter() - part_started
            print(f"FAILED part {current_part}: {type(exc).__name__}: {exc}", flush=True)
            print(f"Part {current_part}: {elapsed:.2f} seconds", flush=True)
        raise


def replay(run_dir: Path) -> Path:
    run_dir = run_dir.resolve()
    if not run_dir.is_dir() or not run_dir.is_relative_to(RUNS.resolve()):
        raise ValueError("Replay folder must be a saved one_desk_runs folder")
    metadata = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    if metadata.get("empty_screen"):
        report = Path(metadata["report"]).resolve()
        seeker_report = Path(metadata["seeker_report"]).resolve()
        for label, path in (("report", report), ("seeker report", seeker_report)):
            if not path.is_file() or not path.is_relative_to(run_dir):
                raise ValueError(f"Saved {label} is missing or outside the replay folder")
        started = time.perf_counter()
        try:
            empty_screen_hook(report, seeker_report, metadata.get("filings_read", []))
        except Exception as exc:
            elapsed = time.perf_counter() - started
            print(f"FAILED part hook: {type(exc).__name__}: {exc}", flush=True)
            print(f"Part hook: {elapsed:.2f} seconds", flush=True)
            raise
        elapsed = time.perf_counter() - started
        print("Hook: passed on saved seeker output and final report", flush=True)
        print(f"Final report: {report}", flush=True)
        print(report.read_text(encoding="utf-8"), end="", flush=True)
        print(f"Part hook: {elapsed:.2f} seconds", flush=True)
        return report
    report = Path(metadata["report"])
    worksheet = Path(metadata["worksheet"])
    verified = Path(metadata["verified_report"])
    seeker_report = Path(metadata["seeker_report"]) if metadata.get("seeker_report") else None
    team = verified.parent
    for label, path in (("report", report), ("worksheet", worksheet), ("verified report", verified)):
        resolved = path.resolve()
        if not resolved.is_file() or not resolved.is_relative_to(run_dir):
            raise ValueError(f"Saved {label} is missing or outside the replay folder")
    if seeker_report is not None and (not seeker_report.is_file() or not seeker_report.resolve().is_relative_to(run_dir)):
        raise ValueError("Saved seeker report is missing or outside the replay folder")
    started = time.perf_counter()
    try:
        worksheet_hook(report, worksheet, verified, team, ROOT / "lab07_worksheet_rules.md", seeker_report)
    except Exception as exc:
        elapsed = time.perf_counter() - started
        print(f"FAILED part hook: {type(exc).__name__}: {exc}", flush=True)
        print(f"Part hook: {elapsed:.2f} seconds", flush=True)
        raise
    elapsed = time.perf_counter() - started
    print("Hook: passed on saved worksheet output and final report", flush=True)
    print(f"Final report: {report}", flush=True)
    print(report.read_text(encoding="utf-8"), end="", flush=True)
    print(f"Part hook: {elapsed:.2f} seconds", flush=True)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ticker", nargs="?", help="Ticker or screen")
    parser.add_argument("--screen-start", help="Start date for the screen; defaults to the configured window")
    parser.add_argument("--replay", type=Path, help="Replay hook checks for a saved run without fetching")
    args = parser.parse_args()
    try:
        if args.replay:
            if args.ticker or args.screen_start:
                parser.error("--replay cannot be combined with run options")
            replay(args.replay)
        else:
            if not args.ticker:
                parser.error("ticker or screen is required unless --replay is used")
            if args.ticker.casefold() != "screen" and not TICKER.fullmatch(args.ticker.upper()):
                parser.error("ticker must use letters, numbers, dots, or hyphens")
            run(args.ticker, args.screen_start)
    except Exception as exc:
        print(f"Error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
