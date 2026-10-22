#!/usr/bin/env python3
"""PreToolUse guard for Bash commands in the <PROJECT> repo.

Turns two rules that were previously prose-only — and were each violated at
least once during real work — into machine-enforced blocks:

* **A1'** destructive discard on a dirty tree. `git checkout -- <path>`,
  `git restore <path>`, `git reset --hard` and `git clean -f` silently delete
  uncommitted work. One `git checkout <config file>` destroyed a whole
  wave's config edits and took the suite from 1297 passed to 164 failed.
  Branch switches (`git checkout -b`, `git checkout <branch>`) and `git stash`
  are NOT blocked — they do not discard.
* **A3** starting the dev server by hand, when a launcher script exists.
  Ships DISABLED — see the configuration block below. Enable it once your
  project has a launcher, so the env file, import path and migrations can
  never be skipped independently of each other.

Matching is done on **command position**, not on substring presence. A naive
substring match blocked this guard's own test harness and any `grep` for the
banned token — a guard with that many false positives gets switched off, which
costs more than it saves. So heredoc bodies and quoted spans are stripped
first, then the command is split into pipeline/list segments, and a rule only
fires when the banned program is the segment's own executable.

Exit codes follow the hook contract: 0 allow, 2 block with the stderr text
shown to the model. Malformed input exits 0 — a guard that fails closed on its
own bug would be worse than the risk it covers.

Escape hatch: prefix the command with `ALLOW_DESTRUCTIVE=1` when the
discard is genuinely intended. Making the override explicit and visible in the
transcript is the point; a silent bypass would defeat the guard.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# RULE A3 — CONFIGURE THIS, IT SHIPS DISABLED
#
# A3 stops anyone starting the dev server by hand, forcing them through a launcher
# script instead. It is off by default because this template does not know your
# stack, and a rule that blocks a command nobody in your project runs is noise.
#
# TURN IT ON once you have a dev-server launcher, by filling in both settings:
#     _LAUNCHER       = "scripts/run-dev.sh"
#     _BANNED_SERVERS = frozenset({"uvicorn", "gunicorn"})   # or: next, vite, rails…
#
# WHY IT IS WORTH TURNING ON. In the project this framework came from, starting the
# server by hand broke three things at once — cross-origin requests, the database
# connection, and the schema — because the hand-rolled command skipped the env file,
# the import path, and the pending migrations. Each failure looked unrelated to the
# others, so the diagnosis cost far more than the mistake. The launcher exists to
# make that combination unrepeatable, and this rule makes the launcher unavoidable.
#
# _SUBCOMMAND_LAUNCHERS handles programs that only start a server with certain
# subcommands: `fastapi dev` starts one, `fastapi --help` does not. Leave it empty
# unless your stack has that shape.
_LAUNCHER = ""
_BANNED_SERVERS: frozenset[str] = frozenset()
_SUBCOMMAND_LAUNCHERS: dict[str, frozenset[str]] = {}
# ---------------------------------------------------------------------------

# Heredoc bodies are data, not commands — `<<'EOF' … EOF` and `<<EOF … EOF`.
_HEREDOC_PATTERN = re.compile(
    r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1.*?^\s*\2\s*$",
    re.DOTALL | re.MULTILINE,
)
_QUOTED_SPAN_PATTERN = re.compile(r"'[^']*'|\"[^\"]*\"", re.DOTALL)
# Shell separators that start a fresh command position.
_SEGMENT_SPLIT_PATTERN = re.compile(r"\|\||&&|[;|\n()`]")
_ENV_ASSIGNMENT_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
# Wrappers that pass their tail on to another program, so the real executable
# is further along the segment.
_TRANSPARENT_WRAPPERS = frozenset({"env", "exec", "nohup", "time", "sudo", "poetry", "uv"})


_OVERRIDE_ASSIGNMENT = "ALLOW_DESTRUCTIVE=1"


def _defuse_quoted_span(match: re.Match[str]) -> str:
    """Keep a quoted span's contents, minus any shell separator inside it.

    Inside quotes, `|`, `;`, `&&`, newline, parens and backticks are literal
    DATA — the shell never treats them as separators there. Feeding them to the
    segment splitter invents command positions that cannot exist, and the
    invented segment gets judged as if someone had run it.

    Measured 2026-08-12: `grep -rnE 'foo|git reset --hard' .` was BLOCKED as a
    destructive discard. The alternation inside the quotes was split on `|`, so
    the second half became a segment whose executable was `git`. A read-only
    search of the repo's own documentation could not be run — and this bit
    during this framework's own leakage audit, on a sibling repo carrying an
    older copy of this file, which is as close to a field report as it gets.
    """
    return " " + _SEGMENT_SPLIT_PATTERN.sub(" ", match.group(0)[1:-1]) + " "


def _executable_segments(command: str) -> list[list[str]]:
    """Split a shell command into segments, each as its executable + args.

    Heredoc bodies are dropped and quoted spans are defused first, so that
    *mentioning* a banned token in prose or in a test fixture is not treated as
    running it.
    """
    stripped = _HEREDOC_PATTERN.sub(" ", command)
    # Quotes are removed, their CONTENTS are not. Replacing a quoted span with a
    # space deleted the argument inside it, so `git checkout "config.yaml"` reached
    # the rules as a bare `git checkout` with no path — and a rule that needs a path
    # to decide saw nothing and allowed it. Quoting an argument must not be a way
    # through the gate. Prose and fixtures are still protected on both sides now:
    # the splitter only looks at the first token of each segment, and a separator
    # inside the quotes can no longer manufacture a segment of its own.
    stripped = _QUOTED_SPAN_PATTERN.sub(_defuse_quoted_span, stripped)

    segments: list[list[str]] = []
    for raw in _SEGMENT_SPLIT_PATTERN.split(stripped):
        tokens = raw.split()
        # Drop leading `VAR=value` assignments and transparent wrappers so the
        # executable ends up first.
        while tokens and (
            _ENV_ASSIGNMENT_PATTERN.match(tokens[0]) or tokens[0] in _TRANSPARENT_WRAPPERS
        ):
            tokens = tokens[1:]
        if tokens:
            segments.append(tokens)
    return segments


def _program_name(token: str) -> str:
    """`.venv/bin/python` -> `python`; `/usr/bin/git` -> `git`."""
    return token.rsplit("/", maxsplit=1)[-1]


def _module_target(tokens: list[str]) -> str | None:
    """The module named by `-m <module>`, if this segment runs an interpreter."""
    if not tokens or not _program_name(tokens[0]).startswith("python"):
        return None
    for index, token in enumerate(tokens[1:-1], start=1):
        if token == "-m":
            return tokens[index + 1]
    return None


def _git_discard_reason(tokens: list[str]) -> str | None:
    """Why this `git` segment would discard uncommitted work, or None."""
    if _program_name(tokens[0]) != "git":
        return None
    args = [token for token in tokens[1:] if not token.startswith("-") or token == "--"]
    flags = {token for token in tokens[1:] if token.startswith("-")}
    subcommand = args[0] if args else ""

    if subcommand == "checkout":
        rest = tokens[tokens.index("checkout") + 1 :]
        if "-b" in flags or "-B" in flags or "--orphan" in flags:
            return None  # creating a branch, not discarding
        if "--" in rest:
            return "git checkout -- <path> discards uncommitted changes to that path"
        # A bare `git checkout <ref>` switches branches. Treat an argument that
        # looks like a path (has a separator or an extension) as a discard.
        for token in rest:
            if token.startswith("-"):
                continue
            if "/" in token or "." in token:
                return "git checkout <path> discards uncommitted changes to that path"
        return None

    if subcommand == "restore":
        # `--staged` alone only rewrites the index and is safe; adding
        # `--worktree` makes it destructive again.
        if "--staged" in flags and "--worktree" not in flags and "-W" not in flags:
            return None
        return "git restore <path> discards uncommitted changes to that path"

    if subcommand == "reset" and ("--hard" in flags or "--merge" in flags):
        return "git reset --hard discards every uncommitted change in the tree"

    if subcommand == "clean" and any(
        flag.startswith("-") and "f" in flag.lstrip("-") for flag in flags
    ):
        return "git clean -f deletes untracked files, including new source files"

    return None


def _direct_server_launch(tokens: list[str]) -> bool:
    """True when this segment launches an ASGI server directly (rule A3)."""
    if not _BANNED_SERVERS and not _SUBCOMMAND_LAUNCHERS:
        return False  # rule A3 not configured for this project
    program = _program_name(tokens[0])
    if program in _BANNED_SERVERS:
        return True
    if program in _SUBCOMMAND_LAUNCHERS:
        return any(token in _SUBCOMMAND_LAUNCHERS[program] for token in tokens[1:])
    module = _module_target(tokens)
    return module in _BANNED_SERVERS


def _tree_is_dirty() -> bool:
    """True when `git status --porcelain` reports anything at all.

    Untracked files count: `git clean -f` destroys exactly those.
    """
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        # Cannot tell — assume dirty so the guard errs toward protecting work.
        return True
    return bool(result.stdout.strip())


def _block(message: str) -> None:
    print(message, file=sys.stderr)
    sys.exit(2)


def _has_head_override(command: str, assignment: str = _OVERRIDE_ASSIGNMENT) -> bool:
    """True only when `assignment` (default `ALLOW_DESTRUCTIVE=1`) is an env
    assignment on the first segment, the position a shell would actually apply it.

    Scoped deliberately: each override waives its own rule and nothing
    else. An escape hatch that silences every rule at once is not an escape hatch,
    it is an off switch.
    """
    first = _SEGMENT_SPLIT_PATTERN.split(command)[0]
    for token in first.split():
        if token == assignment:
            return True
        if not _ENV_ASSIGNMENT_PATTERN.match(token):
            return False
    return False


# ---------------------------------------------------------------------------
# RULE R26 — no hand-written polling loops (SPEC-verify-tiers-merge-gate, G)
#
# `until grep -q passed out.log; do sleep 10; done` spends the agent's time and a
# model turn per wake-up on work the harness will report when it ends. The rule
# fires on a `while`/`until`/`for` loop whose body (or condition) runs `sleep`.
# A loop inside `bash -c "…"`, a script file, a heredoc fed to a shell, or another
# language's sleep loop is NOT seen — declared limits in doc/framework/ADAPTERS.md.
_POLL_OVERRIDE = "ALLOW_POLL=1"
_LOOP_KEYWORDS = frozenset({"while", "until", "for"})
# Tokens that may precede a segment's real command word.
_LEAD_KEYWORDS = frozenset({"do", "then", "else", "elif", "if", "{", "!"})


def _command_index(tokens: list[str], start: int = 0) -> int:
    """Index of the first token from `start` past keywords, env assignments and wrappers."""
    for index in range(start, len(tokens)):
        token = tokens[index]
        if not (
            token in _LEAD_KEYWORDS
            or token in _TRANSPARENT_WRAPPERS
            or _ENV_ASSIGNMENT_PATTERN.match(token)
        ):
            return index
    return len(tokens)


def _polling_loop_reason(segments: list[list[str]]) -> str | None:
    """Why these segments are a hand-written polling loop, or None.

    Tracks loop depth so a `sleep` after a finished loop (`for …; done; sleep 2`)
    is not mistaken for one inside it.
    """
    depth = 0
    for tokens in segments:
        index = _command_index(tokens)
        while index < len(tokens) and tokens[index] in _LOOP_KEYWORDS:
            depth += 1
            index = _command_index(tokens, index + 1)
        word = _program_name(tokens[index]) if index < len(tokens) else ""
        if word == "done":
            depth = max(depth - 1, 0)
        elif word == "sleep" and depth > 0:
            return "a hand-written polling loop (loop + sleep)"
    return None
# ---------------------------------------------------------------------------


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)

    if payload.get("tool_name") != "Bash":
        sys.exit(0)

    command = str(payload.get("tool_input", {}).get("command", ""))
    if not command:
        sys.exit(0)

    # The override is a *prefix*, not a word that appears somewhere. Substring
    # matching let `echo ALLOW_DESTRUCTIVE=1 && git reset --hard` disable every rule
    # in the file: the token was never run, merely printed. It must sit in the env
    # assignment position of the first segment, exactly where a shell would apply it.
    override = _has_head_override(command)

    segments = _executable_segments(command)

    for tokens in segments:
        reason = _git_discard_reason(tokens)
        if reason and _tree_is_dirty() and not override:
            _block(
                f"BLOCKED (.claude/hooks/guard_bash.py, rule A1'): {reason}, and "
                f"the working tree has uncommitted changes.\n"
                f"This exact mistake once destroyed a wave of config edits "
                f"(suite went 1297 passed -> 164 failed).\n"
                f"Do one of these instead:\n"
                f"  1. `git stash` (reversible) or commit first, then discard;\n"
                f"  2. copy the file to a backup path if you only need its old "
                f"contents;\n"
                f"  3. if the discard is genuinely intended, re-run the command "
                f"prefixed with `ALLOW_DESTRUCTIVE=1 ` so the choice is on "
                f"the record."
            )

    # R26 has its own override; `ALLOW_DESTRUCTIVE=1` does not waive it.
    poll_reason = _polling_loop_reason(segments)
    if poll_reason and not _has_head_override(command, _POLL_OVERRIDE):
        _block(
            f"BLOCKED (.claude/hooks/guard_bash.py, rule R26): {poll_reason}. "
            f"Do not poll.\n"
            f"If you launched the work in the background, end your turn or do "
            f"independent work until the completion notification arrives. See "
            f".agents/skills/engineering-loop/SKILL.md, \"Waiting on background "
            f"work\".\n"
            f"If this loop is genuinely not a wait on background work, re-run it "
            f"as `ALLOW_POLL=1; <loop>` so the choice is on the record."
        )

    for tokens in segments:
        if _direct_server_launch(tokens) and _LAUNCHER not in command:
            _block(
                f"BLOCKED (.claude/hooks/guard_bash.py, rule A3): start the dev "
                f"server with `{_LAUNCHER}`, not a direct server command.\n"
                f"The launcher exists so that the environment file, the import path "
                f"and any pending migrations are always applied together. Starting "
                f"the server by hand has broken all three at once, and each failure "
                f"looked unrelated to the others."
            )

    _check_always_human(command)
    sys.exit(0)


def _check_always_human(command: str) -> None:
    """Owner-only commands (always) and always-human items (under autonomy).

    The list and the matching live in `scripts/autonomy.py`; this adapter only
    decides when to refuse. `ALLOW_DESTRUCTIVE=1` does not reach this rule.
    Imported here, after A1' and A3 have run, so a broken import cannot take
    the older rules down with it. If the core cannot load (missing, or broken
    by an edit), the owner rule still holds through a minimal inline matcher:
    an exit 1 here would be non-blocking, which is fail-open.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    try:
        _apply_core(command)
    except Exception as exc:  # noqa: BLE001 — a core that fails to load OR to run must not open the owner rule
        _owner_rule_without_core(command, exc)


def _apply_core(command: str) -> None:
    # The core comes through the adapter, which loads it from its source file.
    from guard_autonomy_paths import ADAPTER_PROTECTED, autonomy

    cwd = Path.cwd()
    root = autonomy.project_root(cwd)
    try:
        config, config_problem = autonomy.load_config(root), ""
    except autonomy.ConfigError as exc:
        # Framework items stay on; only the project's additions are lost.
        config, config_problem = {}, f"\n({exc} — the framework items still apply.)"
    segments = autonomy.segments(command)
    branch = autonomy.current_branch(cwd) if any(_program_name(s[0]) == "git" for s in segments) else None
    matches = autonomy.command_matches(
        command,
        config,
        root=root,
        cwd=cwd,
        current_branch=branch,
        extra_protected=ADAPTER_PROTECTED,
    )

    for match in matches:
        if match.scope == "always":
            _block(
                f"BLOCKED (.claude/hooks/guard_bash.py, rule AH5): owner-only command — "
                f"matched: {match.pattern}.\n"
                f"This writes the approval registry, which only a human writes "
                f"(AGENTS.md §6). An agent running it would approve its own work.\n"
                f"Ask the owner to run it themselves with the `!` prefix. Read-only "
                f"forms (`--list`, `--dry-run`) stay allowed."
            )

    on_protected = autonomy.protected_commit(command, config, cwd)
    if not matches and not on_protected:
        return
    state = autonomy.status(root)
    if state == "inactive":
        return
    if on_protected:
        _block(
            f"BLOCKED (.claude/hooks/guard_bash.py, rule F-AC1): git commit on protected "
            f"branch {on_protected} — work under autonomy happens on a branch or worktree.\n"
            f"Autonomy is active ({state}). Create or switch to a working branch "
            f"(`git switch -c <branch>`) or a worktree, and commit there.{config_problem}"
        )
    match = matches[0]
    _block(
        f"BLOCKED (.claude/hooks/guard_bash.py): always-human item {match.item} — "
        f"matched: {match.pattern}.\n"
        f"Autonomy is active ({state}), and no mandate, order or absence covers this "
        f"item. Stop and ask the owner.{config_problem}"
    )


#: The owner scripts, by name anywhere in the command, for when the core
#: (scripts/autonomy.py) cannot load. Deliberately cruder than the core: it
#: also refuses a mere mention, which is the safe direction while broken.
_OWNER_FALLBACK = re.compile(
    r"(?<![\w.-])(approve|delegate|revoke|override|away|evolve|release)\.(sh|py)(?![\w.-])"
)


def _owner_rule_without_core(command: str, exc: Exception) -> None:
    """No read-only exemption here: `-n` elsewhere in the command (`nice -n`)
    would open the rule. While the core is broken, `--list` is refused too."""
    match = _OWNER_FALLBACK.search(command)
    if match:
        _block(
            f"BLOCKED (.claude/hooks/guard_bash.py, rule AH5): owner-only command — "
            f"matched: {match.group(0)}.\n"
            f"scripts/autonomy.py failed to load or run ({type(exc).__name__}: {exc}), so "
            f"this guard refuses every owner script by name until it is repaired. Ask "
            f"the owner to run it themselves with the `!` prefix."
        )


if __name__ == "__main__":
    main()
