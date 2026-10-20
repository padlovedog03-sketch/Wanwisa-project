#!/usr/bin/env python3
"""PreToolUse guard: no Write/Edit to the paths that define or enforce the
assistant's authority while autonomy is active (SPEC-delegated-autonomy B-AC6).

Under a mandate, an order or absence the assistant may approve some artifacts
itself. It must never be able to widen that authority: edit the mandate or
order, the always-human list, the decision log, or the hooks and scripts that
enforce them (R4). The list of protected paths lives in `scripts/autonomy.py`
(the core); this adapter adds only its own wiring paths, which the core may
not name.

Outside autonomy the same edits are allowed (R6, ADR-6): there they go through
the ordinary tier-2 gates, which is how this feature itself gets built.

Exit codes follow the hook contract: 0 allow, 2 block with the stderr text
shown to the model. Malformed input exits 0 — a guard that fails closed on its
own bug would wedge every write.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def _load_from_source(name: str, path: Path):  # noqa: ANN202 — returns a module
    """Load `path` as module `name` from its source text alone: never by name
    through `sys.path`, where a planted `scripts/<stdlib name>.py` or a
    `scripts/<name>/` package would win, and never through `__pycache__`,
    where a forged cache would stand in for the source. Registered before it
    runs, as `@dataclass` needs on Python 3.14."""
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    exec(compile(path.read_bytes(), str(path), "exec"), module.__dict__)  # noqa: S102 — our own file, by path
    return module


autonomy = _load_from_source("autonomy", Path(__file__).resolve().parents[2] / "scripts" / "autonomy.py")

#: This adapter's own wiring. `settings.local.json` is included because it can
#: switch every hook off.
ADAPTER_PROTECTED = (".claude/hooks/**", ".claude/settings.json", ".claude/settings.local.json")

_WRITE_TOOLS = frozenset({"Write", "Edit", "MultiEdit", "NotebookEdit"})


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)
    if not isinstance(payload, dict) or payload.get("tool_name") not in _WRITE_TOOLS:
        sys.exit(0)
    tool_input = payload.get("tool_input") or {}
    target = str(tool_input.get("file_path") or tool_input.get("notebook_path") or "")
    if not target:
        sys.exit(0)

    cwd = Path.cwd()
    root = autonomy.project_root(cwd)
    try:
        config = autonomy.load_config(root)
    except autonomy.ConfigError:
        config = {}  # framework paths stay protected whatever the project file says
    # As written AND through symlinks, case-folded: a link or a case variant
    # must not reach a protected file under a name the guard does not know.
    rel = next(
        (r for r in autonomy.repo_relatives(target, root, cwd) if autonomy.is_protected(r, config, ADAPTER_PROTECTED)),
        None,
    )
    if rel is None:
        sys.exit(0)
    state = autonomy.status(root)
    if state == "inactive":
        sys.exit(0)

    print(
        f"BLOCKED (.claude/hooks/guard_autonomy_paths.py): always-human item AH5 — "
        f"{rel} defines or enforces the assistant's authority, and autonomy is active "
        f"({state}).\n"
        f"Only the owner changes it. Ask the owner; they commit the change with an "
        f"`Owner-Approved: <registry key>` trailer.",
        file=sys.stderr,
    )
    sys.exit(2)


if __name__ == "__main__":
    main()
