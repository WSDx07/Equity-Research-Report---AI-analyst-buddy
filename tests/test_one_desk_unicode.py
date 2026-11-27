import io
import os
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from unittest.mock import Mock, patch

import one_desk


class UnicodeOutputTest(unittest.TestCase):
    def test_cp1252_console_streams_preserve_unicode_and_escape_surrogates(self):
        stdout_bytes = io.BytesIO()
        stderr_bytes = io.BytesIO()
        stdout = io.TextIOWrapper(stdout_bytes, encoding="cp1252", newline="\n")
        stderr = io.TextIOWrapper(stderr_bytes, encoding="cp1252", newline="\n")
        self.addCleanup(stdout.close)
        self.addCleanup(stderr.close)

        with patch.object(sys, "stdout", stdout), patch.object(sys, "stderr", stderr):
            one_desk.configure_console_output()
            print("SYNTHETIC \u2705 \u2014 \u03b1")
            print("SYNTHETIC error \u5931\u6557 \udcff", file=sys.stderr)
            stdout.flush()
            stderr.flush()

        self.assertEqual(stdout_bytes.getvalue().decode("utf-8"), "SYNTHETIC \u2705 \u2014 \u03b1\n")
        self.assertEqual(stderr_bytes.getvalue().decode("utf-8"), "SYNTHETIC error \u5931\u6557 \\udcff\n")

    def test_console_configuration_accepts_stringio_capture(self):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with patch.object(sys, "stdout", stdout), patch.object(sys, "stderr", stderr):
            one_desk.configure_console_output()
            print("SYNTHETIC \u2705")
            print("SYNTHETIC \u03b1", file=sys.stderr)
        self.assertEqual(stdout.getvalue(), "SYNTHETIC \u2705\n")
        self.assertEqual(stderr.getvalue(), "SYNTHETIC \u03b1\n")

    def test_child_encoding_preserves_supplied_environment_without_mutating_it(self):
        supplied = {"SYNTHETIC_SETTING": "kept", "PYTHONIOENCODING": "cp1252", "PYTHONUTF8": "0"}
        original = supplied.copy()
        process = Mock(stdout=io.StringIO("SYNTHETIC output\n"))
        process.wait.return_value = 0
        with patch.object(one_desk.subprocess, "Popen", return_value=process) as popen, redirect_stdout(io.StringIO()):
            output, _ = one_desk.run_command("synthetic", ["synthetic-child"], env=supplied)
        self.assertEqual(supplied, original)
        self.assertEqual(popen.call_args.kwargs["env"], {
            "SYNTHETIC_SETTING": "kept", "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1",
        })
        self.assertEqual(popen.call_args.kwargs["encoding"], "utf-8")
        self.assertEqual(output, "SYNTHETIC output\n")

    def test_child_encoding_inherits_environment_when_none_is_supplied(self):
        process = Mock(stdout=io.StringIO(""))
        process.wait.return_value = 0
        with patch.dict(os.environ, {"SYNTHETIC_SETTING": "inherited"}, clear=True):
            with patch.object(one_desk.subprocess, "Popen", return_value=process) as popen, redirect_stdout(io.StringIO()):
                one_desk.run_command("synthetic", ["synthetic-child"])
            self.assertEqual(dict(os.environ), {"SYNTHETIC_SETTING": "inherited"})
        self.assertEqual(popen.call_args.kwargs["env"], {
            "SYNTHETIC_SETTING": "inherited", "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8",
        })

    def run_synthetic_cli(self, child_exit):
        # Replace the live workflow before invoking main: no SEC/provider calls.
        child = (
            "import sys; "
            "print('SYNTHETIC \\u2705 \\u2014 \\u03b1', flush=True); "
            "sys.stderr.write('SYNTHETIC diagnostic \\u5931\\u6557\\n'); "
            f"sys.exit({child_exit})"
        )
        probe = (
            "import sys\n"
            "def offline(event, args):\n"
            "    if event in {'socket.connect', 'socket.getaddrinfo'}:\n"
            "        raise AssertionError('Network forbidden in synthetic test')\n"
            "sys.addaudithook(offline)\n"
            "import one_desk\n"
            "def synthetic_run(ticker, screen_start):\n"
            f"    output, _ = one_desk.run_command('synthetic', [sys.executable, '-c', {child!r}])\n"
            "    assert 'SYNTHETIC \\u2705 \\u2014 \\u03b1' in output\n"
            "    assert 'SYNTHETIC diagnostic \\u5931\\u6557' in output\n"
            "one_desk.run = synthetic_run\n"
            "sys.argv = ['one_desk.py', 'SYNTHETIC']\n"
            "raise SystemExit(one_desk.main())\n"
        )
        env = os.environ.copy()
        env.update(PYTHONUTF8="0", PYTHONIOENCODING="cp1252", PYTHONDONTWRITEBYTECODE="1")
        return subprocess.run(
            [sys.executable, "-B", "-c", probe], cwd=one_desk.ROOT, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20,
        )

    def test_cli_captures_unicode_child_output_from_cp1252_parent(self):
        result = self.run_synthetic_cli(0)
        self.assertEqual(result.returncode, 0, result.stderr.decode("utf-8"))
        self.assertIn("SYNTHETIC \u2705 \u2014 \u03b1", result.stdout.decode("utf-8"))
        self.assertIn("SYNTHETIC diagnostic \u5931\u6557", result.stdout.decode("utf-8"))

    def test_cli_retains_unicode_failure_diagnostic_and_nonzero_exit(self):
        result = self.run_synthetic_cli(7)
        self.assertEqual(result.returncode, 1)
        self.assertIn("FAILED part synthetic", result.stdout.decode("utf-8"))
        self.assertIn("exit code 7", result.stderr.decode("utf-8"))
        self.assertIn("SYNTHETIC diagnostic \u5931\u6557", result.stderr.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
