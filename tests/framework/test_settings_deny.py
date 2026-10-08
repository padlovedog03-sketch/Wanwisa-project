"""The irreversible commands stay denied — risk ranking, item 3.

WHY THIS FILE EXISTS. An allow rule like `Bash(git *)` lets a force-push or a
cloud-resource delete run with no prompt. A deny rule outranks every allow
rule, so these are the only line between a mistaken command and work nobody
can get back. Deleting one from settings.json must turn this file red.

Run: `python3 -m pytest tests/framework/ -q`   (stdlib only)
"""

from __future__ import annotations

import json
from pathlib import Path

_SETTINGS = Path(__file__).resolve().parents[2] / ".claude" / "settings.json"
REQUIRED_DENY = (
    "Bash(git push --force*)",
    "Bash(git push -f*)",
    "Bash(git push * --force*)",
    "Bash(git push * -f)",
    "Bash(git push * -f *)",
    "Bash(git -C * push --force*)",
    "Bash(git -C * push -f*)",
    "Bash(git -C * push * --force*)",
    "Bash(az * delete*)",
)


def test_irreversible_commands_are_denied() -> None:
    deny = json.loads(_SETTINGS.read_text(encoding="utf-8"))["permissions"]["deny"]
    missing = [rule for rule in REQUIRED_DENY if rule not in deny]
    assert not missing, f"deny rules removed: {missing}"


def test_correction_rate_prints_at_session_start() -> None:
    hooks = json.loads(_SETTINGS.read_text(encoding="utf-8"))["hooks"]["SessionStart"]
    commands = [h["command"] for entry in hooks for h in entry["hooks"]]
    assert any("correction_rate.py" in c for c in commands)
