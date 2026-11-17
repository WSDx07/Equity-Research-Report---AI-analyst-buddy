import json
import sys
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

    def test_changed_amount_in_final_report_copy_is_refused_by_report_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            team = Path(tmp) / "team"
            team.mkdir()
            worksheet = team / "worksheet.md"
            worksheet.write_text(
                '- After-tax earnings: 575 USD millions [filing file="VYLR_Form 10.txt" line=12 '
                'section="Combined Statements of Operations" tag=historical period=FY2025 source_run=target]\n',
                encoding="utf-8",
            )
            verified = team / "verified_report.md"
            verified.write_text("Verified team report.\n", encoding="utf-8")
            report = team / "seeded-copy-final-report.md"
            report.write_text(
                "Filings read: Form 10\n\n# Verified agent-team report\n\n"
                "Verified team report.\n\n## Worksheet view\n\n"
                '- After-tax earnings: 576 USD millions [filing file="VYLR_Form 10.txt" line=12 '
                'section="Combined Statements of Operations" tag=historical period=FY2025 source_run=target]\n',
                encoding="utf-8",
            )
            sys_path = str(one_desk.GUARD_DIR)
            if sys_path not in sys.path:
                sys.path.insert(0, sys_path)
            import worksheet_guard

            calls = 0

            def validate(path, **kwargs):
                nonlocal calls
                calls += 1
                if calls == 1:
                    return []
                return [
                    'line 1: filing line 12 does not contain 576 | '
                    '- After-tax earnings: 576 USD millions [filing file="VYLR_Form 10.txt" '
                    'line=12 section="Combined Statements of Operations"]'
                ]

            with patch.object(worksheet_guard, "validate_worksheet", side_effect=validate):
                with self.assertRaises(one_desk.RefusalError) as caught:
                    one_desk.worksheet_hook(report, worksheet, verified, team, Path("rules.md"))

            self.assertEqual(
                str(caught.exception),
                "refused: line 9, 576 is not in VYLR_Form 10.txt, Combined Statements of Operations",
            )


if __name__ == "__main__":
    unittest.main()
