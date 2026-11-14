"""Entry point for the staged Codex lifecycle hook."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from worksheet_guard import hook_main  # noqa: E402

hook_main()
