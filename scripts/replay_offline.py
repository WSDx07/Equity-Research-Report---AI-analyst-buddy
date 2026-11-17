"""Replay a saved One Desk run with socket and DNS access blocked."""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import socket
import sys
import time
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import one_desk  # noqa: E402


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/replay_offline.py RUN_FOLDER", file=sys.stderr)
        return 2
    run_dir = Path(sys.argv[1]).resolve()
    try:
        metadata = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
        report = Path(metadata["report"]).resolve()
        if not report.is_file() or not report.is_relative_to(run_dir):
            raise ValueError("Saved final report is missing or outside the run folder")
        expected_report = report.read_text(encoding="utf-8")
    except (OSError, KeyError, ValueError, json.JSONDecodeError) as exc:
        print(f"Offline replay setup failed: {exc}", file=sys.stderr)
        return 1

    network_attempts: list[str] = []

    def blocked(name: str):
        def reject(*args, **kwargs):
            network_attempts.append(name)
            raise OSError("Network is disabled for this replay")
        return reject

    output = io.StringIO()
    started = time.perf_counter()
    with (
        patch.object(socket.socket, "connect", blocked("socket.connect")),
        patch.object(socket.socket, "connect_ex", blocked("socket.connect_ex")),
        patch.object(socket, "create_connection", blocked("socket.create_connection")),
        patch.object(socket, "getaddrinfo", blocked("socket.getaddrinfo")),
        contextlib.redirect_stdout(output),
        contextlib.redirect_stderr(output),
    ):
        sys.argv = ["one_desk.py", "--replay", str(run_dir)]
        exit_code = one_desk.main()

    replay_output = output.getvalue()
    if exit_code != 0:
        sys.stdout.write(replay_output)
        print(f"Offline replay failed with exit code {exit_code}", file=sys.stderr)
        return exit_code
    if network_attempts:
        print(f"Offline replay attempted network access: {network_attempts}", file=sys.stderr)
        return 1
    if expected_report not in replay_output:
        print("Replay output did not contain the exact saved final report", file=sys.stderr)
        return 1

    proof = {
        "run_dir": str(run_dir),
        "network_blocked": True,
        "network_attempts": network_attempts,
        "exit_code": exit_code,
        "report_sha256": hashlib.sha256(expected_report.encode("utf-8")).hexdigest(),
        "output_contains_exact_saved_report": True,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
    }
    (run_dir / "replay-offline-proof.json").write_text(json.dumps(proof, indent=2) + "\n", encoding="utf-8")
    (run_dir / "replay-offline-output.txt").write_text(replay_output, encoding="utf-8")
    sys.stdout.write(replay_output)
    print("Offline replay proof: network blocked; no attempts; saved report matched.")
    print(f"Proof: {run_dir / 'replay-offline-proof.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
