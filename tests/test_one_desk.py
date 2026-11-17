import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import one_desk


class EmptyScreenTest(unittest.TestCase):
    def test_empty_screen_saves_report_marks_ticker_stages_na_and_replays(self):
        with tempfile.TemporaryDirectory() as tmp:
            runs = Path(tmp).resolve()

            def fake_run_command(label, command, **kwargs):
                output = Path(command[command.index("--output") + 1])
                report = output / "spinoff-screen-test.md"
                registry = output / "registry-test.json"
                report.write_text(
                    "Run date: 2026-11-16 | Price date: unavailable | Index date: 2026-11-14\n\n"
                    "## In window, ranked\nNone established.\n\n"
                    "## Watch list\nNone established.\n\n"
                    "screens, not recommendations\n",
                    encoding="utf-8",
                )
                registry.write_text("{}\n", encoding="utf-8")
                (output / "filing_reads.json").write_text('{"filings": []}\n', encoding="utf-8")
                return f"Screen report: {report}\nFact registry: {registry}\n", 0.25

            with patch.object(one_desk, "RUNS", runs), patch.object(one_desk, "run_command", side_effect=fake_run_command):
                report = one_desk.run("screen", None)

            run_dir = report.parent
            metadata = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
            self.assertTrue(metadata["empty_screen"])
            self.assertIsNone(metadata["ticker"])
            self.assertEqual(
                [(part["part"], part.get("status")) for part in metadata["parts"]],
                [
                    ("seeker", None),
                    ("pick", "not applicable"),
                    ("agent team", "not applicable"),
                    ("worksheet", "not applicable"),
                    ("hook", None),
                ],
            )
            self.assertTrue((run_dir / "pick.json").is_file())
            self.assertFalse((run_dir / "team").exists())
            report_text = report.read_text(encoding="utf-8")
            self.assertTrue(report_text.startswith("Filings read: none identified\n"))
            self.assertIn("## Worksheet\n\nNot applicable", report_text)
            with patch.object(one_desk, "RUNS", runs):
                replayed = one_desk.replay(run_dir)
            self.assertEqual(replayed.read_text(encoding="utf-8"), report_text)


if __name__ == "__main__":
    unittest.main()
