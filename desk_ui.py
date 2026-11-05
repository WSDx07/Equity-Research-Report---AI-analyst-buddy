"""Local browser interface for the equity research desk."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import uuid
import webbrowser
from decimal import Decimal, InvalidOperation
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parent
RUNS = (ROOT / "equity_research_runs").resolve()
PAGE = ROOT / "desk_ui" / "index.html"
TICKER = re.compile(r"^[A-Z0-9][A-Z0-9.\-]{0,14}$")
ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
NODES = re.compile(r"^(?:Step \d+ started|Research Analyst|Financial Analyst|Investment Advisor|Strategy Manager|Verifier|Financial Datasets cross-check)")
renderer = MarkdownIt("commonmark", {"html": False}).enable("table")
jobs: dict[str, dict] = {}
lock = threading.Lock()


def validate(payload: dict) -> tuple[str, list[str], str | None]:
    if not isinstance(payload, dict):
        raise ValueError("Enter a ticker.")
    ticker = str(payload.get("ticker", "")).strip().upper()
    if not TICKER.fullmatch(ticker):
        raise ValueError("Enter a valid ticker using letters, numbers, dots or hyphens.")
    raw_peers = str(payload.get("peers", "")).upper().strip()
    peers = [p for p in re.split(r"[\s,]+", raw_peers) if p]
    if len(peers) > 10 or any(not TICKER.fullmatch(p) for p in peers):
        raise ValueError("Enter up to 10 valid peer tickers, separated by commas or spaces.")
    raw_price = str(payload.get("price", "")).strip()
    if raw_price:
        try:
            price = Decimal(raw_price)
            if not price.is_finite() or price <= 0:
                raise ValueError
        except (InvalidOperation, ValueError):
            raise ValueError("Enter a price greater than zero.") from None
    return ticker, peers, raw_price or None


def execute(job_id: str, ticker: str, peers: list[str], price: str | None) -> None:
    command = [sys.executable, "-u", str(ROOT / "desk_flow.py"), ticker]
    if peers:
        command.extend(["--peers", *peers])
    if price:
        command.extend(["--price", price])
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    env["PYTHONUNBUFFERED"] = "1"
    report_path = None
    last_lines = []
    try:
        process = subprocess.Popen(command, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", bufsize=1)
        assert process.stdout is not None
        for line in process.stdout:
            clean = ANSI.sub("", line).strip()
            if not clean:
                continue
            last_lines.append(clean)
            last_lines = last_lines[-16:]
            if NODES.match(clean):
                with lock:
                    jobs[job_id]["events"].append(clean)
            if clean.startswith("Verified report:"):
                report_path = clean.removeprefix("Verified report:").strip()
        code = process.wait()
        if code != 0:
            raise RuntimeError("The desk stopped before the report was ready. " + " ".join(last_lines[-4:])[:800])
        if not report_path or report_path == "None":
            raise RuntimeError("The desk did not return a verified report. " + " ".join(last_lines[-4:])[:800])
        path = Path(report_path).resolve()
        if not path.is_relative_to(RUNS) or path.name != "verified_report.md" or not path.is_file():
            raise RuntimeError("The reported output file is missing or outside the run folder.")
        report = path.read_text(encoding="utf-8")
        with lock:
            jobs[job_id].update(status="complete", report_html=renderer.render(report), report_path=str(path))
    except (OSError, RuntimeError, UnicodeError) as exc:
        with lock:
            jobs[job_id].update(status="error", error=str(exc))


class Handler(BaseHTTPRequestHandler):
    def send_json(self, status: int, value: dict) -> None:
        data = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/":
            data = PAGE.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)
        elif path.startswith("/api/jobs/"):
            job_id = path.removeprefix("/api/jobs/")
            with lock:
                job = dict(jobs[job_id]) if job_id in jobs else None
            self.send_json(200 if job else 404, job or {"error": "Run not found."})
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path != "/api/jobs":
            self.send_error(404)
            return
        origin = self.headers.get("Origin", "")
        host = self.headers.get("Host", "")
        if origin != "http://" + host or host not in {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}:
            self.send_json(403, {"error": "Open the page on this computer to start a run."})
            return
        if self.headers.get_content_type() != "application/json":
            self.send_json(415, {"error": "Expected JSON."})
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if size <= 0 or size > 4096:
                raise ValueError("Invalid request size.")
            ticker, peers, price = validate(json.loads(self.rfile.read(size)))
        except (ValueError, UnicodeError, json.JSONDecodeError) as exc:
            self.send_json(400, {"error": str(exc)})
            return
        job_id = uuid.uuid4().hex
        with lock:
            if any(job["status"] == "running" for job in jobs.values()):
                self.send_json(409, {"error": "A run is already in progress. Wait for it to finish."})
                return
            jobs[job_id] = {"status": "running", "events": []}
        threading.Thread(target=execute, args=(job_id, ticker, peers, price), daemon=True).start()
        self.send_json(202, {"job_id": job_id})


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 8765), Handler)
    url = "http://127.0.0.1:8765/"
    print(f"Desk page: {url}", flush=True)
    threading.Timer(0.7, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
