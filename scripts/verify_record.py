#!/usr/bin/env python3
"""The verify tiers' recorder: bans, tree identity, JUnit counts, the run record.

Called by `scripts/verify-full.sh` and `scripts/verify-fast.sh`; never run by hand
in the normal loop. stdlib only, Python 3.9+.

  check-banned  refuse banned flags before any step runs (exit 2), and print every
                declared filter from VERIFY_ALLOWED_FILTERS
  tree-hash     hash the working tree exactly as it is (dirty and untracked
                files included) through a throwaway index; `null` outside git
  finalize      read the run directory, count the JUnit reports this run wrote,
                print the summary lines, write record.json, end with VERDICT=<v>
                (full tier) or the banner itself (fast tier)

Why it exists: a gate that prints GREEN over a run that executed nothing, or
executed a filtered subset, is the failure this framework was built to stop.
See doc/specs/SPEC-verify-tiers-merge-gate.md, increment A+C.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import shlex
import shutil
import socket
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from typing import List, NamedTuple, Optional, Tuple

KEEP_RUNS = 20
SLOWEST = 10

# --- bans (design §AC.3) -----------------------------------------------------

_SELECTS_NOTHING = "selects nothing after a green run"
_HIDES = "hides the other failures"
_RETRIES = "retries turn a failure into a pass"
_CACHED = "a cached result reported as a fresh run"
_LAST_RUN = "orders the run by the last run's failures"

#: Hard bans. A `--flag=value` form matches on the part before `=`.
#: None of these can ever be allow-listed (owner ruling 2026-10-20, ADR-14).
HARD_BANS = {
    "--lf": _SELECTS_NOTHING,
    "--last-failed": _SELECTS_NOTHING,
    "--ff": _LAST_RUN,
    "--failed-first": _LAST_RUN,
    "-x": _HIDES,
    "--exitfirst": _HIDES,
    "--maxfail": _HIDES,
    "--bail": _HIDES,
    "--sw": _HIDES,
    "--stepwise": _HIDES,
    "--sw-skip": _HIDES,
    "--stepwise-skip": _HIDES,
    "--reruns": _RETRIES,
    "--retries": _RETRIES,
    "--retry": _RETRIES,
    "--flake-finder": _RETRIES,
    # Amendment 2, AM2-ADR-3: the count check cannot see a retry.
    "--force-flaky": _RETRIES,
    "--max-runs": _RETRIES,
}
#: Matched as prefixes, so plugin variants count too (`--sw-reset`, `--lfnf=all`,
#: `--last-failed-no-failures`, `--reruns-delay`, `--cache_test_results=no`).
#: `--cache-clear` is not here: it makes a run fresher, not staler.
PREFIX_BANS = (
    ("--last-failed", _SELECTS_NOTHING), ("--lf", _SELECTS_NOTHING),
    ("--failed-first", _LAST_RUN), ("--ff", _LAST_RUN),
    ("--stepwise", _HIDES), ("--sw", _HIDES),
    ("--reruns", _RETRIES),
    ("--cache_test_results", _CACHED), ("--cache-test-results", _CACHED),
)

#: The filters a project may declare, with the reason printed when one is used
#: undeclared at runtime.
FILTER_REASONS = {
    "-k": "filter used to reach green",
    "-m": "marker deselection used to reach green",
    "--deselect": "deselection used to reach green",
    "--ignore": "path ignored to reach green",
    "--ignore-glob": "path ignored to reach green",
}
LONG_FILTERS = ("--deselect", "--ignore", "--ignore-glob")
UNDECLARED = "undeclared filter; declare it with a reason in VERIFY_ALLOWED_FILTERS"
DECLARABLE = "only -m, -k, --deselect, --ignore and --ignore-glob can be declared"

#: The built-in bans are pytest's (coordinator rulings D6 and D17, 2026-10-20), so
#: they apply to the argv of the pytest family only: `git commit -m`, `tar -x`,
#: `go test -timeout` are not pytest flags. It is always scanned, whatever a project
#: sets. Any other runner a project lists in VERIFY_TEST_RUNNERS is NOT scanned; it
#: is named on a `limit:` line, and its bans go in VERIFY_EXTRA_BANNED.
PYTEST_FAMILY = ("pytest", "py.test")
DEFAULT_RUNNERS = PYTEST_FAMILY
_PYTHON = re.compile(r"^python[0-9.]*$")
#: Shell grammar, not programs: the command position comes after these.
_RESERVED = ("!", "{", "if", "then", "elif", "else", "while", "until", "do")
LIMIT_TAIL = "its flags are not scanned — declare bans in VERIFY_EXTRA_BANNED"
#: Short options that take a value: the rest of a cluster is that value, so the
#: `x` in `-rxXs` or `-p no:x` is not `-x`.
_VALUE_SHORTS = set("cnoprW")
#: The environment variable pytest reads its options from (ruling D7).
_FLAG_ENV = "PYTEST_ADDOPTS"
_ASSIGN = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$", re.S)
_SHELLS = ("bash", "sh", "zsh", "dash", "ksh")


class Allowed(NamedTuple):
    flag: str
    value: str
    written: str
    reason: str


class Filter(NamedTuple):
    flag: str
    value: Optional[str]
    written: str


def _hard_ban(token: str) -> Optional[str]:
    for prefix, reason in PREFIX_BANS:
        if token.startswith(prefix):
            return reason
    key = token.split("=", 1)[0] if token.startswith("--") else token
    return HARD_BANS.get(key)


def _quote(value: str) -> str:
    return '"%s"' % value if re.search(r"[\s'\"]", value) else value


def _tokens(command: str) -> List[str]:
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    try:
        return list(lexer)
    except ValueError:  # unbalanced quotes: still scan the words
        return command.split()


def _short_cluster(tok: str) -> Tuple[bool, Optional[str], str]:
    """Walk `-qxk…`: (holds -x, the -k/-m it ends in, that filter's attached value).
    A value-taking option ends the walk: the rest of the token is its value."""
    if len(tok) < 3 or tok.startswith("--") or not tok.startswith("-"):
        return False, None, ""
    for idx, ch in enumerate(tok[1:], 1):
        if ch == "x":
            return True, None, ""
        if ch in "km":
            return False, "-" + ch, tok[idx + 1:]
        if ch in _VALUE_SHORTS:
            break
    return False, None, ""


def _filter_at(tokens: List[str], i: int) -> Tuple[Optional[Filter], int]:
    """The filter starting at tokens[i], if any, and how many tokens it spans."""
    tok = tokens[i]
    nxt = tokens[i + 1] if i + 1 < len(tokens) else None
    if tok in ("-k", "-m") + LONG_FILTERS:
        written = tok if nxt is None else "%s %s" % (tok, _quote(nxt))
        return Filter(tok, nxt, written), 1 if nxt is None else 2
    for flag in LONG_FILTERS:
        if tok.startswith(flag + "="):
            return Filter(flag, tok.split("=", 1)[1], tok), 1
    _, flag, attached = _short_cluster(tok)
    if flag is None:
        return None, 1
    if attached:
        head = tok[:len(tok) - len(attached)]
        return Filter(flag, attached, head + _quote(attached)), 1
    written = tok if nxt is None else "%s %s" % (tok, _quote(nxt))
    return Filter(flag, nxt, written), 1 if nxt is None else 2


def parse_allowlist(entries: List[str]) -> Tuple[List[Allowed], List[str]]:
    """`"<filter>|<reason>"` entries → (allowed, error lines)."""
    allowed: List[Allowed] = []
    errors: List[str] = []
    for entry in entries:
        left, sep, reason = entry.rpartition("|")
        if not sep:
            left, reason = entry, ""
        left = left.strip()
        toks = _tokens(left)
        if not toks:
            errors.append("BANNED: empty allow-list entry")
            continue
        if _hard_ban(toks[0]):
            errors.append("BANNED: %s can never be allow-listed" % toks[0])
            continue
        filt, span = _filter_at(toks, 0)
        if filt is None or filt.value is None or span != len(toks):
            errors.append("BANNED: %s — %s" % (left, DECLARABLE))
            continue
        if not reason.strip():
            errors.append("BANNED: allow-list entry without a reason: %s" % left)
            continue
        allowed.append(Allowed(filt.flag, filt.value, left, reason.strip()))
    return allowed, errors


def check_banned(tokens: List[str], allowed: List[Allowed], source: str) -> List[str]:
    """Violation lines for a runner's argv. `source` is `configured` (a project's
    own step command, where declared filters are waived) or `runtime` (arguments
    typed at the tier or set in its environment, where nothing is waived)."""
    out: List[str] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        reason = _hard_ban(tok) or (_HIDES if _short_cluster(tok)[0] else None)
        if reason:
            out.append("BANNED: %s — %s" % (tok, reason))
            i += 1
            continue
        filt, span = _filter_at(tokens, i)
        if filt is not None:
            if source == "runtime":
                out.append("BANNED: %s — %s" % (tok, FILTER_REASONS[filt.flag]))
                i += 1  # the value is an ordinary argument (a path) at runtime
                continue
            if not any(a.flag == filt.flag and a.value == filt.value for a in allowed):
                out.append("BANNED: %s — %s" % (filt.written, UNDECLARED))
            i += span
            continue
        i += 1
    return out


def _simple_commands(tokens: List[str]) -> List[List[str]]:
    """Split on shell operators. A redirection and its target are dropped, so
    `pytest >log -x` still scans `-x`."""
    commands: List[List[str]] = [[]]
    skip = False
    for tok in tokens:
        if skip:
            skip = False
        elif tok and all(c in "();<>|&" for c in tok):
            if "<" in tok or ">" in tok:
                skip = True
            elif commands[-1]:
                commands.append([])
        else:
            commands[-1].append(tok)
    return [c for c in commands if c]


def _matches(words: List[str], i: int, runner: List[str]) -> bool:
    return (os.path.basename(words[i]) == runner[0]
            and words[i + 1:i + len(runner)] == runner[1:])


def _program(words: List[str], runners: List[List[str]]) -> Tuple[Optional[str], List[str]]:
    """(runner, its argv) for the program a simple command runs, or (None, []).
    Only the command position counts (ruling D15), after leading assignments and
    the wrappers `env`, `uv run`, `coverage run` and `python[N] -m` / `-mX`; a
    path argument named like a runner (`make -C tools/jest`) is never a runner.
    The pytest family is matched before the wrappers and the project's own runners
    after them, so listing `python3` or `uv` as a runner cannot hide pytest."""
    i = 0
    while i < len(words):
        base = os.path.basename(words[i])
        if _ASSIGN.match(words[i]) or words[i] in _RESERVED:
            i += 1
        elif words[i] == "time":  # also shell grammar, with its one option
            i += 2 if words[i + 1:i + 2] == ["-p"] else 1
        elif base in PYTEST_FAMILY:
            return base, words[i + 1:]
        elif base == "env":
            i += 1
            while i < len(words) and (words[i].startswith("-") or _ASSIGN.match(words[i])):
                i += 2 if words[i] in ("-u", "-C") else 1
        elif base == "uv" and words[i + 1:i + 2] == ["run"]:
            i += 2
            while i < len(words) and words[i].startswith("-"):
                i += 1
        elif _PYTHON.match(base) or (base == "coverage" and words[i + 1:i + 2] == ["run"]):
            i += 1 if _PYTHON.match(base) else 2
            while i < len(words) and words[i].startswith("-"):
                opt = words[i]
                if opt == "-c":  # a program in a string: not scanned
                    return None, []
                if opt == "-m" or (opt.startswith("-m") and not opt.startswith("--")):
                    module = words[i + 1:i + 2] if opt == "-m" else [opt[2:]]
                    rest = words[i + 2:] if opt == "-m" else words[i + 1:]
                    words, i = module + rest, 0  # the module is the program now
                    break
                i += 2 if opt in ("-W", "-X") else 1
        else:
            for runner in runners:
                if _matches(words, i, runner):
                    return " ".join(runner), words[i + len(runner):]
            return None, []
    return None, []


def _env_bans(name: str, value: str, allowed: List[Allowed], source: str) -> List[str]:
    if name != _FLAG_ENV:
        return []
    return ["%s (in %s)" % (line, name)
            for line in check_banned(_tokens(value), allowed, source)]


class Scan(NamedTuple):
    lines: List[str]  # violations
    limited: bool  # uses eval or a shell's -c string
    others: List[str]  # runners found that are not the pytest family
    pytest: bool  # a pytest-family runner was found and scanned


def scan_command(command: str, allowed: List[Allowed], extra: List[str],
                 runners: List[List[str]]) -> Scan:
    """What one configured command runs, and its violations."""
    lines: List[str] = []
    limited = False
    others: List[str] = []
    found_pytest = False
    tokens = _tokens(command)
    for tok in tokens:  # a project's own additions apply to every program
        if any(tok == x or tok.startswith(x + "=") for x in extra):
            lines.append("BANNED: %s — project-declared" % tok)
    for words in _simple_commands(tokens):
        for word in words:
            m = _ASSIGN.match(word)
            if m:
                lines += _env_bans(m.group(1), m.group(2), allowed, "configured")
        program = next((w for w in words if not _ASSIGN.match(w)), "")
        base = os.path.basename(program)
        if base == "eval" or (base in _SHELLS and any(
                re.fullmatch(r"-[a-z]*c[a-z]*", w) for w in words[1:])):
            limited = True
        runner, argv = _program(words, runners)
        if runner in PYTEST_FAMILY:
            found_pytest = True
            lines += check_banned(argv, allowed, "configured")
        elif runner is not None and runner not in others:
            others.append(runner)
    return Scan(lines, limited, others, found_pytest)


def cmd_check_banned(args: argparse.Namespace) -> int:
    allowed, errors = parse_allowlist(args.allow)
    extra = (args.extra or "").split()
    runners = [shlex.split(r) for r in (args.runner or DEFAULT_RUNNERS) if r.strip()]
    test_steps = args.test_steps.split()
    lines: List[str] = list(errors)
    limits: List[str] = []
    # `--step=<label>|<command>` splits on the FIRST bar, as the tiers' `${entry%%|*}`.
    steps = [(c, c) for c in args.cmd] + [tuple(s.partition("|")[::2]) for s in args.step]
    for label, command in steps:
        scan = scan_command(command, allowed, extra, runners)
        lines += scan.lines
        if scan.limited:
            limits.append("limit: flags inside eval or a shell's -c string are not scanned: %s"
                          % command)
        elif scan.others or (label in test_steps and not scan.pytest):
            # Ruling D16: an unscanned test step is said, never silent.
            limits.append("limit: step %s runs %s; %s"
                          % (label, ", ".join(scan.others) or "no known runner", LIMIT_TAIL))
    for line in limits:
        print(line)
    if limits and os.environ.get("VERIFY_RUN_DIR"):
        Path(os.environ["VERIFY_RUN_DIR"], "limits.txt").write_text(
            "".join(line + "\n" for line in limits), encoding="utf-8")
    lines += check_banned(args.runtime, allowed, "runtime")
    lines += ["BANNED: %s — project-declared" % tok for tok in args.runtime
              if any(tok == x or tok.startswith(x + "=") for x in extra)]
    lines += _env_bans(_FLAG_ENV, os.environ.get(_FLAG_ENV, ""), allowed, "runtime")
    for a in allowed:
        print("declared filter: %s — %s" % (a.written, a.reason))
    seen = set()
    for line in lines:
        if line not in seen:
            seen.add(line)
            print(line)
    return 2 if lines else 0


# --- tree identity (design §AC.5) --------------------------------------------


def _git_env() -> dict:
    return {k: v for k, v in os.environ.items()
            if k not in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE")}


def _git(*args: str, env: Optional[dict] = None) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], capture_output=True, text=True,
                          env=env or _git_env(), check=False)


def tree_hash() -> str:
    """The tree as it is on disk, `null` outside a git work tree, `error` when
    git is there but the hash could not be taken (never silently `null`)."""
    if shutil.which("git") is None:
        return "null"
    probe = _git("rev-parse", "--is-inside-work-tree")
    if probe.returncode != 0 or probe.stdout.strip() != "true":
        return "null"
    index = Path(_git("rev-parse", "--git-path", "index").stdout.strip())
    with tempfile.TemporaryDirectory() as tmp:
        tmp_index = Path(tmp) / "index"
        if index.is_file():
            shutil.copyfile(index, tmp_index)
            # The copy's fresh mtime would make every entry stat-clean ("racy
            # git"), so an edit keeping size and mtime would be hashed as the old
            # content. An index older than every file makes git check each one.
            os.utime(tmp_index, (1, 1))
        env = _git_env()
        env["GIT_INDEX_FILE"] = str(tmp_index.resolve())
        add = _git("add", "-A", "--", ":/", env=env)
        # The run's own outputs never count as a change to the tree, whether or
        # not the project git-ignores .verify/ (an exclude pathspec fails when
        # it names an ignored path, so drop it from the index afterwards).
        drop = _git("rm", "-r", "-q", "--cached", "--ignore-unmatch", "--", ".verify", env=env)
        tree = _git("write-tree", env=env)
    failed = [r for r in (add, drop, tree) if r.returncode != 0]
    if failed:
        print("tree-hash: %s" % failed[0].stderr.strip(), file=sys.stderr)
        return "error"
    return tree.stdout.strip()


def _head() -> Tuple[Optional[str], Optional[str]]:
    head = _git("rev-parse", "HEAD")
    tree = _git("rev-parse", "HEAD^{tree}")
    if head.returncode != 0:
        return None, None
    return head.stdout.strip(), tree.stdout.strip()


# --- counts (design §AC.4) ---------------------------------------------------


class Counts(NamedTuple):
    passed: int
    failed: int
    skipped: int
    reported: int
    files: int
    failing_ids: List[str]
    durations: List[Tuple[str, float, str]]  # (id, seconds, file part for size rules)


def junit_counts(directory: Path) -> Counts:
    passed = failed = skipped = files = 0
    failing: List[str] = []
    durations: List[Tuple[str, float, str]] = []
    for xml in sorted(directory.rglob("*.xml")) if directory.is_dir() else []:
        files += 1
        for case in ET.parse(str(xml)).getroot().iter("testcase"):
            cls = case.get("classname", "")
            tid = "%s::%s" % (cls, case.get("name", ""))
            if case.find("failure") is not None or case.find("error") is not None:
                failed += 1
                failing.append(tid)
            elif case.find("skipped") is not None:
                skipped += 1
            else:
                passed += 1
            try:
                secs = float(case.get("time", "0") or 0)
            except ValueError:
                secs = 0.0
            durations.append((tid, secs, case.get("file") or cls.replace(".", "/")))
    return Counts(passed, failed, skipped, passed + failed + skipped, files, failing, durations)


def _parse_count(path: Path) -> Optional[int]:
    lines = [ln for ln in path.read_text(encoding="utf-8", errors="replace").splitlines()
             if ln.strip()]
    if not lines:
        return None
    m = re.search(r"\d+", lines[-1])
    return int(m.group()) if m else None


def _size(file_part: str, rules: str) -> str:
    for rule in rules.split():
        glob, _, size = rule.partition("=")
        if size and fnmatch.fnmatch(file_part, glob):
            return size
    return "small"


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    return int(raw) if raw else default


# --- finalize ----------------------------------------------------------------


def _read_steps(run_dir: Path) -> List[dict]:
    steps = []
    path = run_dir / "steps.tsv"
    for line in path.read_text(encoding="utf-8").splitlines() if path.is_file() else []:
        label, rc, secs, todo, junit = (line.split("\t") + [""] * 5)[:5]
        steps.append({"label": label, "exit": int(rc), "seconds": int(secs),
                      "todo": todo == "1", "junit": junit})
    return steps


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _prune(runs: Path, keep: Path) -> None:
    """Fast and full runs each keep their own KEEP_RUNS slots, so a day of
    inner-loop runs never evicts the full record a handoff points at."""
    dirs = sorted((p for p in runs.iterdir() if p.is_dir()), key=lambda p: p.name)
    for fast in (True, False):
        tier = [p for p in dirs if p.name.endswith("-fast") == fast]
        for old in tier[:-KEEP_RUNS]:
            if old != keep:
                shutil.rmtree(old, ignore_errors=True)


def _local_runner_id() -> str:
    """A stable id for this machine that never records its hostname, which is
    often a person's name (AGENTS.md §8; coordinator ruling D8)."""
    digest = hashlib.sha256(socket.gethostname().encode("utf-8")).hexdigest()
    return "local:%s" % digest[:12]


def cmd_finalize(args: argparse.Namespace) -> int:
    run_dir = Path(args.run_dir)
    steps = _read_steps(run_dir)
    out: List[str] = []
    red: List[str] = []
    warnings: List[str] = []
    allowed, _ = parse_allowlist(args.allow)

    # Counts are read only from this run's fresh directory: a report left by an
    # earlier run cannot be counted as this one.
    reported_total = 0
    failures: List[str] = []
    durations: List[Tuple[str, float, str, str]] = []
    any_junit = False
    for step in steps:
        junit = step.pop("junit")
        if not junit or step["todo"]:
            continue
        c = junit_counts(Path(junit))
        step["tests"] = {"passed": c.passed, "failed": c.failed, "skipped": c.skipped,
                         "reported": c.reported, "files": c.files}
        any_junit = any_junit or c.files > 0
        reported_total += c.reported
        failures += c.failing_ids
        durations += [(tid, secs, fp, step["label"]) for tid, secs, fp in c.durations]
        if args.tier == "full":
            if c.failed and step["exit"] == 0:
                red.append("step %s exited 0 but its JUnit records %d failed test(s)"
                           % (step["label"], c.failed))
            if c.files == 0:
                red.append("no JUnit report written by step %s" % step["label"])
            elif c.reported == 0:
                red.append("0 tests reported by step %s" % step["label"])

    collected: Optional[int] = None
    collect_broken = False
    collect_note = ""
    if args.collect_file:
        collected = _parse_count(Path(args.collect_file))
        if args.collect_rc != 0:
            collect_broken = True
            out.append("VERIFY_COLLECT_CMD failed (exit %d)" % args.collect_rc)
            collect_note = "collect failed (exit %d)" % args.collect_rc
            collected = None
        elif collected is None:
            collect_broken = True
            out.append("VERIFY_COLLECT_CMD printed no count")
            collect_note = "collect printed no count"

    test_steps = [s for s in steps if "tests" in s]
    if args.tier == "full":
        if not steps:
            red.append("no steps configured")
        # A misspelled label would match nothing and check nothing — silently.
        labels = {s["label"] for s in steps}
        for name in os.environ.get("VERIFY_TEST_STEPS", "").split():
            if name not in labels:
                red.append("VERIFY_TEST_STEPS names %s, which is not a step" % name)
        if collect_broken:
            count_check = "mismatch"
            red.append(out.pop())
        elif collected is None or not test_steps:
            count_check = "not-configured"
            out.append("counts: not configured — executed == collected NOT checked")
        elif reported_total != collected:
            count_check = "mismatch"
            red.append("reported %d of %d collected" % (reported_total, collected))
        else:
            count_check = "ok"
            out.append("counts: reported %d of %d collected" % (reported_total, collected))
    else:
        count_check = ("mismatch" if collect_broken
                       else "ok" if collected is not None and any_junit else "not-configured")
        if collect_broken:
            out.pop()  # the fast banner names it instead

    # Tree identity: enforced only where a project has opted into the conf (R12).
    before, after = args.tree_before, args.tree_after
    if "error" in (before, after):
        msg = "tree hash could not be taken"
        (red if args.conf_present else out).append(
            msg if args.conf_present else msg + " (not enforced: no scripts/verify.conf)")
    elif before != after:
        if args.conf_present:
            red.append("tree changed during the run — this run is evidence for neither tree")
        else:
            out.append("tree changed during the run (not enforced: no scripts/verify.conf)")

    # Budgets warn; they never change a verdict.
    step_budget = _env_int("VERIFY_STEP_BUDGET_S", 900)
    budgets = {"small": _env_int("VERIFY_TEST_BUDGET_SMALL_S", 1),
               "medium": _env_int("VERIFY_TEST_BUDGET_MEDIUM_S", 10),
               "large": _env_int("VERIFY_TEST_BUDGET_LARGE_S", 60)}
    rules = os.environ.get("VERIFY_TEST_SIZE_RULES", "")
    for step in steps:
        if not step["todo"] and step["seconds"] > step_budget:
            warnings.append("WARN step %s took %ds (step budget %ds)"
                            % (step["label"], step["seconds"], step_budget))
    sized = [(tid, secs, _size(fp, rules), label) for tid, secs, fp, label in durations]
    for tid, secs, size, label in sized:
        if secs > budgets.get(size, budgets["small"]):
            warnings.append("WARN step %s: test %s took %.2fs (%s budget %ds)"
                            % (label, tid, secs, size, budgets.get(size, budgets["small"])))
    slowest = sorted(sized, key=lambda d: d[1], reverse=True)[:SLOWEST]

    step_failed = any(s["exit"] != 0 for s in steps if not s["todo"])
    todo = any(s["todo"] for s in steps)
    if args.tier == "full":
        verdict = "RED" if (step_failed or red) else "INCOMPLETE" if todo else "GREEN"
    elif failures:
        verdict = "RED"
    elif any_junit and reported_total == 0:
        verdict = "EMPTY"
    else:
        verdict = "OK"

    head, head_tree = _head() if before not in ("null", "error") else (None, None)
    as_null = lambda h: None if h in ("null", "error") else h  # noqa: E731
    record = {
        "schema": 1, "tier": args.tier, "run_id": run_dir.name,
        "started_at": args.started_at, "ended_at": _now(),
        "tree": {"before": as_null(before), "after": as_null(after), "head": head,
                 "dirty": None if head_tree is None or as_null(before) is None
                 else as_null(before) != head_tree},
        "runner": ({"id": os.environ["VERIFY_RUNNER_ID"], "kind": "runner"}
                   if os.environ.get("VERIFY_RUNNER_ID")
                   else {"id": _local_runner_id(), "kind": "local"}),
        "steps": steps, "collected": collected, "count_check": count_check,
        "failures": failures,
        "declared_filters": [{"filter": a.written, "reason": a.reason} for a in allowed],
        "red": red, "warnings": warnings,
        "slowest": [{"id": t, "seconds": s, "size": z} for t, s, z, _ in slowest],
        "verdict": verdict,
    }
    limits = run_dir / "limits.txt"  # written by check-banned, already printed
    if limits.is_file():
        record["warnings"] = warnings + limits.read_text(encoding="utf-8").splitlines()
    (run_dir / "record.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    _prune(run_dir.parent, run_dir)

    for line in out + red + warnings:
        print(line)
    if args.tier == "full":
        if slowest:
            print("slowest tests:")
            for tid, secs, size, _ in slowest:
                print("- %.2fs  %s  (%s)" % (secs, tid, size))
        print("VERDICT=%s" % verdict)
        return 0

    n = str(reported_total) if any_junit else "?"
    m = str(collected) if collected is not None else "?"
    if verdict == "RED":
        print("FAST VERIFY RED — %d test(s) failed in the JUnit report" % len(failures))
        return 1
    if verdict == "EMPTY":
        print("FAST VERIFY EMPTY — ran 0 of %s; nothing was verified" % m)
        return 1
    suffix = (" — " + collect_note if collect_note
              else "" if "?" not in (n, m) else " (counts not configured)")
    print("FAST VERIFY OK — partial run: ran %s of %s%s" % (n, m, suffix))
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    ban = sub.add_parser("check-banned")
    ban.add_argument("--allow", action="append", default=[])
    ban.add_argument("--extra", default="")
    ban.add_argument("--cmd", action="append", default=[])
    ban.add_argument("--runtime", action="append", default=[])
    ban.add_argument("--runner", action="append", default=[])
    ban.add_argument("--step", action="append", default=[])
    ban.add_argument("--test-steps", default="")

    sub.add_parser("tree-hash")

    fin = sub.add_parser("finalize")
    fin.add_argument("--tier", choices=("full", "fast"), required=True)
    fin.add_argument("--run-dir", required=True)
    fin.add_argument("--started-at", default="")
    fin.add_argument("--tree-before", default="null")
    fin.add_argument("--tree-after", default="null")
    fin.add_argument("--collect-file")
    fin.add_argument("--collect-rc", type=int, default=0)
    fin.add_argument("--conf-present", action="store_true")
    fin.add_argument("--allow", action="append", default=[])

    args = parser.parse_args(argv)
    if args.command == "check-banned":
        return cmd_check_banned(args)
    if args.command == "tree-hash":
        print(tree_hash())
        return 0
    return cmd_finalize(args)


if __name__ == "__main__":
    sys.exit(main())
