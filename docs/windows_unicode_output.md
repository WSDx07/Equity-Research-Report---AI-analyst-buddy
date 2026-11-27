# Windows Unicode output fix

## Failure

Samuel Parfait's assisted MSFT ready-check attempt on November 26, 2026 used
commit `7586b901e28e5df1dd8043a60d2bcb923db8326f` and the README command:

```powershell
.\.venv\Scripts\python.exe one_desk.py MSFT
```

The command exited with code 1 during the agent-team stage. The saved traceback
points to `print(line, end="", flush=True)` in `one_desk.py`, through the Windows
CP1252 encoder:

```text
UnicodeEncodeError: 'charmap' codec can't encode characters in position 0-29: character maps to <undefined>
```

The parent already decoded captured child output as UTF-8, but its own output
stream could still use CP1252. Setting UTF-8 for the team child did not configure
the parent console. The failed attempt produced no completed Verifier result,
worksheet validation, or final report. Its original evidence is preserved in
the separate ready-check checkout and record; it is not replaced by these tests.

## Change

- At CLI startup, configure supported stdout and stderr streams for UTF-8.
  `backslashreplace` preserves otherwise unencodable surrogate diagnostics as
  visible escapes instead of dropping them or raising another encoding error.
  Capture streams such as `StringIO`, which have no `reconfigure`, remain usable.
- In `run_command`, copy the supplied environment, or inherit a copy when none
  is supplied, then set `PYTHONUTF8=1` and `PYTHONIOENCODING=utf-8` for each child.
  The caller's environment mapping is not mutated. Other supplied variables
  keep their values; an explicit environment remains explicit.
- Keep UTF-8 child decoding, its existing replacement policy for invalid bytes,
  streamed output, merged child stderr, return values and failure handling.
  Child failure diagnostics and the child's exit-code number remain visible;
  the existing CLI failure status remains 1.

The normal README command needs no extra encoding flags, shell setup, package,
or provider change. No system console code page, credential, global Python
setting, lifecycle-hook configuration, or pipeline order is changed. Console
configuration occurs in the CLI entry point; callers embedding imported
functions retain control of their own output streams.

## Offline validation

On November 26, 2026, Windows with official Python 3.12.10 passed **8 tests**:
6 new Unicode tests and the 2 existing directly relevant One Desk tests.
From the worktree root, use a Python 3.12 interpreter:

```powershell
python -B -m unittest discover -s tests -p "test_one_desk*.py" -v
```

The new cases cover CP1252-backed stdout and stderr, preserved Unicode and
escaped surrogate diagnostics, `StringIO` capture, inherited and explicitly
supplied child environments, and real synthetic child-output capture. CLI
probes start with `PYTHONUTF8=0` and `PYTHONIOENCODING=cp1252`. They replace the
live workflow before entering `main` and forbid network access in the probe.
A synthetic child failure exits with 7; its Unicode message survives and the
CLI still exits with 1. The existing tests cover empty-screen handling/replay
and refusal of an altered final-report worksheet section using synthetic
fixtures and mocked stages, not a live desk.

An additional synthetic CLI probe using the unchanged base commit reproduced
the expected CP1252 failure with exit 1. No production source was replaced for
that check: the base source was loaded into a temporary test directory.

No SEC or model-provider requests, live desk run, or ready-check rerun were
performed. No successful live execution, report-accuracy verification,
unassisted ready pass, or weekly-live-record eligibility is claimed. A future
live attempt requires separate authorization and must retain the prior setup
assistance in its record.
