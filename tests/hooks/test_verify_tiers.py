"""Increment A+C — no fake green, and a measurable `verify-full`.

Spec: doc/specs/SPEC-verify-tiers-merge-gate.md (AC-AC1 … AC-AC19).
Design: doc/architecture/DESIGN-verify-tiers-merge-gate.md §AC.

Every case runs a COPY of the scripts inside `tmp_path`, built by the `_copy`
helper of `test_verify_scripts.py` — the real `verify-full.sh` runs
`pytest tests/hooks/`, which collects this file: running the real script from
here would recurse without bound. Stub test commands write synthetic JUnit XML
into `$VERIFY_JUNIT_DIR`, so the counting, the bans and the verdict logic under
test are the real ones.

Run: `python3 -m pytest tests/hooks/test_verify_tiers.py -q`
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

import pytest

from test_verify_scripts import (
    _FAST,
    _FULL,
    _PLACEHOLDER_STEPS,
    _REAL_CI_NESTED_SUITE,
    _REAL_CI_STEP,
    _REAL_COORD_NESTED_SUITE,
    _REAL_COORD_STEP,
    _REAL_FRAMEWORK_STEP,
    _REAL_HOOK_STEP,
    _REAL_NESTED_SUITE,
    _REAL_SCAR_NESTED_SUITE,
    _REAL_SCAR_STEP,
    _copy,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_EXAMPLE_CONF = _REPO_ROOT / "scripts" / "verify.conf.example"

#: The five permanent steps, stubbed exactly as `test_verify_scripts.py` does.
_STUB_PERMANENT = (
    (_REAL_HOOK_STEP, '"hooks|echo hooks ran"'),
    (_REAL_CI_STEP, '"ci-examples|echo ci-examples ran"'),
    (_REAL_SCAR_STEP, '"scar-forge|echo scar-forge ran"'),
    (_REAL_COORD_STEP, '"coordinator|echo coordinator ran"'),
    (_REAL_FRAMEWORK_STEP, '"framework|echo framework ran"'),
)
#: The four nested suites the fast tier's routing blocks run.
_STUB_FAST_NESTED = (
    (_REAL_NESTED_SUITE, "echo NESTED-HOOK-SUITE-WOULD-RUN"),
    (_REAL_CI_NESTED_SUITE, "echo NESTED-CI-SUITE-WOULD-RUN"),
    (_REAL_SCAR_NESTED_SUITE, "echo NESTED-SCAR-SUITE-WOULD-RUN"),
    (_REAL_COORD_NESTED_SUITE, "echo NESTED-COORD-SUITE-WOULD-RUN"),
)

#: Writes a synthetic JUnit report into $VERIFY_JUNIT_DIR.
#: usage: stub_junit.py PASSED FAILED SKIPPED [--file=NAME] [--slow=SECONDS] [--cls=CLASSNAME]
#: Extra positional arguments (the fast tier appends the touched paths) are ignored.
_STUB_JUNIT = r'''
import os, sys
from pathlib import Path
pos = [a for a in sys.argv[1:] if not a.startswith("--")]
opts = dict(a[2:].split("=", 1) for a in sys.argv[1:] if a.startswith("--"))
passed, failed, skipped = (int(x) for x in pos[:3])
target = os.environ.get("VERIFY_JUNIT_DIR")
if not target:
    print("stub: VERIFY_JUNIT_DIR is not set", file=sys.stderr)
    sys.exit(3)
cls = opts.get("cls", "tests.test_stub")
cases = []
for i in range(passed):
    t = opts.get("slow", "0.01") if i == 0 else "0.01"
    cases.append('<testcase classname="%s" name="test_pass_%d" time="%s"/>' % (cls, i, t))
for i in range(failed):
    cases.append('<testcase classname="%s" name="test_fail_%d" time="0.01"><failure message="boom"/></testcase>' % (cls, i))
for i in range(skipped):
    cases.append('<testcase classname="%s" name="test_skip_%d" time="0"><skipped/></testcase>' % (cls, i))
Path(target).mkdir(parents=True, exist_ok=True)
body = '<?xml version="1.0"?><testsuites><testsuite name="stub">%s</testsuite></testsuites>' % "".join(cases)
(Path(target) / opts.get("file", "report.xml")).write_text(body)
print("%d passed, %d failed, %d skipped" % (passed, failed, skipped))
sys.exit(1 if failed else 0)
'''


def _env() -> dict[str, str]:
    """The caller's env minus anything that would leak into the copy: a git
    hook's GIT_DIR would point every git call at the real repo, and a CI
    runner's VERIFY_* would change the record."""
    return {
        k: v for k, v in os.environ.items() if not k.startswith(("GIT_", "VERIFY_"))
    }


def _run(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(script), *args],
        capture_output=True, text=True, timeout=120, check=False, env=_env(),
    )


def _git(root: Path, *args: str) -> str:
    out = subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
        cwd=root, capture_output=True, text=True, check=True, env=_env(),
    )
    return out.stdout.strip()


def _init_repo(root: Path) -> None:
    """A git work tree with everything committed. No .gitignore on purpose:
    the recorder must keep its own `.verify/` out of the tree hash."""
    _git(root, "init", "-q")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "init")


def _write_stub(root: Path) -> None:
    (root / "scripts").mkdir(exist_ok=True)
    (root / "scripts" / "stub_junit.py").write_text(_STUB_JUNIT, encoding="utf-8")


def _write_conf(root: Path, text: str) -> None:
    (root / "scripts").mkdir(exist_ok=True)
    (root / "scripts" / "verify.conf").write_text(text, encoding="utf-8")


def _full(tmp_path: Path, conf: str | None = None, *, git: bool = True) -> Path:
    """A stubbed copy of verify-full.sh, optionally with a conf, in a git repo."""
    probe = _copy(tmp_path, _FULL, *_STUB_PERMANENT)
    _write_stub(tmp_path)
    if conf is not None:
        _write_conf(tmp_path, conf)
    if git:
        _init_repo(tmp_path)
    return probe


def _fast(tmp_path: Path, conf: str | None = None, *extra: tuple[str, str]) -> Path:
    probe = _copy(tmp_path, _FAST, *_STUB_FAST_NESTED, *extra)
    _write_stub(tmp_path)
    if conf is not None:
        _write_conf(tmp_path, conf)
    return probe


def _record(tmp_path: Path, result: subprocess.CompletedProcess[str]) -> dict:
    last = result.stdout.rstrip("\n").splitlines()[-1]
    assert last.startswith("record: "), result.stdout
    return json.loads((tmp_path / last[len("record: "):]).read_text(encoding="utf-8"))


def _conf(steps: list[str], *, test_steps: str = "tests", collect: str | None = None,
          extra: str = "") -> str:
    lines = ["STEPS=("] + ["  '%s'" % s for s in steps] + [")"]
    lines.append('VERIFY_TEST_STEPS="%s"' % test_steps)
    if collect is not None:
        lines.append("VERIFY_COLLECT_CMD='%s'" % collect)
    return "\n".join(lines) + "\n" + extra


def _last(result: subprocess.CompletedProcess[str]) -> str:
    return result.stdout.rstrip("\n").splitlines()[-1]


# ---------------------------------------------------------------------------
# AC-AC1 / AC-AC2 — timing, record, counts
# ---------------------------------------------------------------------------


def test_ac1_every_step_row_is_timed_and_a_record_is_written(tmp_path: Path) -> None:
    probe = _full(tmp_path, _conf(
        ["lint|echo lint ran", "tests|python3 scripts/stub_junit.py 3 0 0"], collect="echo 3"))

    result = _run(probe)

    assert result.returncode == 0, result.stdout + result.stderr
    rows = [ln for ln in result.stdout.splitlines() if ln.startswith("  ")]
    assert len(rows) == 2, result.stdout
    for row in rows:
        assert re.match(r"^  OK   \S+\s+\(\d+s\) ", row), row
    lines = result.stdout.rstrip("\n").splitlines()
    assert lines[-2].startswith("EXIT GATE GREEN"), result.stdout
    assert re.fullmatch(r"record: \.verify/runs/[^/]+/record\.json", lines[-1]), lines[-1]
    rec = _record(tmp_path, result)
    for key in ("run_id", "started_at", "ended_at"):
        assert rec[key], key
    assert set(rec["tree"]) >= {"before", "after"}
    assert rec["tree"]["before"] and rec["tree"]["before"] == rec["tree"]["after"]
    assert rec["runner"]["id"].startswith("local:") and rec["runner"]["kind"] == "local"
    assert [s["label"] for s in rec["steps"]] == ["lint", "tests"]
    for step in rec["steps"]:
        assert step["exit"] == 0 and isinstance(step["seconds"], int)
    assert rec["verdict"] == "GREEN"
    assert rec["tier"] == "full"


def test_ac2_junit_counts_and_failing_ids_reach_the_record(tmp_path: Path) -> None:
    probe = _full(tmp_path, _conf(["tests|python3 scripts/stub_junit.py 3 1 1"], collect="echo 5"))

    result = _run(probe)

    assert result.returncode == 1, result.stdout
    rec = _record(tmp_path, result)
    tests = rec["steps"][0]["tests"]
    assert (tests["passed"], tests["failed"], tests["skipped"], tests["reported"]) == (3, 1, 1, 5)
    assert rec["failures"] == ["tests.test_stub::test_fail_0"]
    assert rec["count_check"] == "ok"


def test_the_runner_id_comes_from_the_environment_when_set(tmp_path: Path) -> None:
    probe = _full(tmp_path, _conf(["tests|python3 scripts/stub_junit.py 1 0 0"], collect="echo 1"))
    env = _env()
    env["VERIFY_RUNNER_ID"] = "ci-job-42"

    result = subprocess.run(["bash", str(probe)], capture_output=True, text=True,
                            timeout=120, check=False, env=env)

    rec = _record(tmp_path, result)
    assert rec["runner"] == {"id": "ci-job-42", "kind": "runner"}


# ---------------------------------------------------------------------------
# AC-AC3 / AC-AC4 / AC-AC14 — executed == collected
# ---------------------------------------------------------------------------


def test_ac3_a_dropped_test_turns_the_gate_red_and_the_revert_turns_it_green(
    tmp_path: Path,
) -> None:
    """RED-FIRST: the stub drops one of five collected tests on purpose."""
    probe = _full(tmp_path, _conf(["tests|python3 scripts/stub_junit.py 4 0 0"], collect="echo 5"))

    result = _run(probe)

    assert result.returncode == 1, result.stdout
    assert "EXIT GATE RED" in result.stdout
    assert "EXIT GATE GREEN" not in result.stdout
    assert "reported 4 of 5 collected" in result.stdout

    # The revert: the stub reports all five.
    _write_conf(tmp_path, _conf(["tests|python3 scripts/stub_junit.py 5 0 0"], collect="echo 5"))
    result = _run(probe)

    assert result.returncode == 0, result.stdout
    assert "EXIT GATE GREEN" in result.stdout


def test_ac4_shards_in_one_step_directory_are_summed(tmp_path: Path) -> None:
    probe = _full(tmp_path, _conf(
        ["tests|python3 scripts/stub_junit.py 3 0 0 --file=a.xml"
         " && python3 scripts/stub_junit.py 2 0 0 --file=b.xml"],
        collect="echo 5"))

    result = _run(probe)

    assert result.returncode == 0, result.stdout
    assert "EXIT GATE GREEN" in result.stdout
    tests = _record(tmp_path, result)["steps"][0]["tests"]
    assert tests["reported"] == 5 and tests["files"] == 2


def test_ac14_unconfigured_counts_keep_green_and_say_so(tmp_path: Path) -> None:
    probe = _full(tmp_path, _conf(["tests|python3 scripts/stub_junit.py 2 0 0"]))

    result = _run(probe)

    assert result.returncode == 0, result.stdout
    assert "EXIT GATE GREEN" in result.stdout
    assert "counts: not configured — executed == collected NOT checked" in result.stdout.splitlines()
    assert _record(tmp_path, result)["count_check"] == "not-configured"


def test_a_collect_command_that_prints_no_count_is_red(tmp_path: Path) -> None:
    """A configured count that cannot be read must not pass as 'not configured'."""
    probe = _full(tmp_path, _conf(["tests|python3 scripts/stub_junit.py 2 0 0"],
                                  collect="echo no tests here"))

    result = _run(probe)

    assert result.returncode == 1, result.stdout
    assert "EXIT GATE RED" in result.stdout
    assert "VERIFY_COLLECT_CMD printed no count" in result.stdout


def test_a_collect_command_that_fails_is_red(tmp_path: Path) -> None:
    """`eval` runs in the gate's own shell, so the stub fails with `false`, not `exit`."""
    probe = _full(tmp_path, _conf(["tests|python3 scripts/stub_junit.py 5 0 0"],
                                  collect="echo 5; false"))

    result = _run(probe)

    assert result.returncode == 1, result.stdout
    assert "EXIT GATE RED" in result.stdout
    assert "VERIFY_COLLECT_CMD failed (exit 1)" in result.stdout.splitlines()


def test_a_test_step_label_that_names_no_step_is_red(tmp_path: Path) -> None:
    """A typo in VERIFY_TEST_STEPS would otherwise match nothing, check nothing,
    and leave the gate GREEN with only the generic 'not configured' line."""
    probe = _full(tmp_path, _conf(["tests|echo 5 passed"], test_steps="test", collect="echo 5"))

    result = _run(probe)

    assert result.returncode == 1, result.stdout
    assert "EXIT GATE RED" in result.stdout
    assert "VERIFY_TEST_STEPS names test, which is not a step" in result.stdout.splitlines()


# ---------------------------------------------------------------------------
# AC-AC5 / AC-AC9 — an empty step is a failure; a cached report is not fresh
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("python3 scripts/stub_junit.py 0 0 0", "0 tests reported by step tests"),
        ("echo ran nothing", "no JUnit report written by step tests"),
    ],
)
def test_ac5_an_empty_or_unreported_test_step_is_red(
    tmp_path: Path, command: str, expected: str
) -> None:
    probe = _full(tmp_path, _conf(["tests|" + command]))

    result = _run(probe)

    assert result.returncode == 1, result.stdout
    assert "EXIT GATE RED" in result.stdout
    assert expected in result.stdout.splitlines()


def test_ac9_a_report_left_by_an_earlier_run_is_not_counted(tmp_path: Path) -> None:
    probe = _full(tmp_path, _conf(["tests|echo ran nothing"], collect="echo 5"))
    old = tmp_path / ".verify" / "runs" / "20200101T000000Z-1" / "junit" / "tests"
    old.mkdir(parents=True)
    env = _env()
    env["VERIFY_JUNIT_DIR"] = str(old)
    subprocess.run(["python3", str(tmp_path / "scripts" / "stub_junit.py"), "5", "0", "0"],
                   check=True, env=env, capture_output=True)

    result = _run(probe)

    assert result.returncode == 1, result.stdout
    assert "no JUnit report written by step tests" in result.stdout
    assert "EXIT GATE GREEN" not in result.stdout


# ---------------------------------------------------------------------------
# AC-AC10 / AC-AC15 — tree identity
# ---------------------------------------------------------------------------


def _expected_dirty_hash(root: Path) -> str:
    """Independent of the recorder: a throwaway index, filled with `add -A`."""
    tmp_index = root.parent / (root.name + "-index")
    env = _env()
    env["GIT_INDEX_FILE"] = str(tmp_index)
    subprocess.run(["git", "add", "-A", "--", ".", ":(exclude).verify"], cwd=root, env=env,
                   check=True, capture_output=True)
    out = subprocess.run(["git", "write-tree"], cwd=root, env=env, check=True,
                         capture_output=True, text=True).stdout.strip()
    tmp_index.unlink()
    return out


def test_ac10_a_dirty_tree_is_hashed_as_it_is_not_as_head(tmp_path: Path) -> None:
    probe = _full(tmp_path, _conf(["tests|python3 scripts/stub_junit.py 1 0 0"], collect="echo 1"))
    (tmp_path / "scripts" / "stub_junit.py").write_text(_STUB_JUNIT + "\n# edited\n", encoding="utf-8")
    (tmp_path / "untracked.txt").write_text("new\n", encoding="utf-8")

    result = _run(probe)

    assert result.returncode == 0, result.stdout
    rec = _record(tmp_path, result)
    assert rec["tree"]["before"] == _expected_dirty_hash(tmp_path)
    assert rec["tree"]["before"] != _git(tmp_path, "rev-parse", "HEAD^{tree}")
    assert rec["tree"]["dirty"] is True
    assert rec["tree"]["head"] == _git(tmp_path, "rev-parse", "HEAD")
    # The real index is untouched: nothing is staged.
    assert _git(tmp_path, "diff", "--cached", "--name-only") == ""


def test_the_tree_is_hashed_when_verify_is_git_ignored_too(tmp_path: Path) -> None:
    """The shipped configuration: `.verify/` in .gitignore. Found by the real
    exit gate on 2026-10-20 — an exclude pathspec naming an ignored path made
    `git add` fail, so the hash could never be taken in the real repo."""
    (tmp_path / ".gitignore").write_text(".verify/\n", encoding="utf-8")
    probe = _full(tmp_path, _conf(["tests|python3 scripts/stub_junit.py 1 0 0"], collect="echo 1"))

    result = _run(probe)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "could not be taken" not in result.stdout
    rec = _record(tmp_path, result)
    assert rec["tree"]["before"] == _git(tmp_path, "rev-parse", "HEAD^{tree}")
    assert rec["tree"]["dirty"] is False


def test_ac10_a_step_that_edits_a_tracked_file_turns_a_configured_gate_red(
    tmp_path: Path,
) -> None:
    probe = _full(tmp_path, _conf(
        ["tests|python3 scripts/stub_junit.py 1 0 0 && echo x >> scripts/stub_junit.py"],
        collect="echo 1"))

    result = _run(probe)

    assert result.returncode == 1, result.stdout
    assert "EXIT GATE RED" in result.stdout
    assert "tree changed during the run — this run is evidence for neither tree" in result.stdout
    rec = _record(tmp_path, result)
    assert rec["tree"]["before"] != rec["tree"]["after"]


def _fill_in_script_steps(*overrides: tuple[str, str]) -> list[tuple[str, str]]:
    """Every in-script STEPS entry replaced with a real (stub) command."""
    fills = {}
    for placeholder in _PLACEHOLDER_STEPS:
        label = placeholder.split("|", 1)[0].strip('"')
        fills[placeholder] = '"%s|echo %s ran"' % (label, label)
    fills.update(dict(overrides))
    return list(fills.items())


def test_ac10_without_a_conf_a_changed_tree_is_informational_only(tmp_path: Path) -> None:
    probe = _copy(
        tmp_path, _FULL, *_STUB_PERMANENT,
        *_fill_in_script_steps(
            (_PLACEHOLDER_STEPS[2], '"tests|echo x >> tracked.txt"')),
    )
    (tmp_path / "tracked.txt").write_text("a\n", encoding="utf-8")
    _init_repo(tmp_path)

    result = _run(probe)

    assert result.returncode == 0, result.stdout
    assert "EXIT GATE GREEN" in result.stdout
    assert ("tree changed during the run (not enforced: no scripts/verify.conf)"
            in result.stdout.splitlines())


def test_ac15_a_project_as_filled_in_today_stays_green(tmp_path: Path) -> None:
    """The R12 proof: real (stub) commands, no conf, no JUnit, and a step that
    leaves an untracked, non-ignored file behind."""
    probe = _copy(
        tmp_path, _FULL, *_STUB_PERMANENT,
        *_fill_in_script_steps(
            (_PLACEHOLDER_STEPS[2], '"tests|echo 12 passed && echo out > artifact.log"')),
    )
    _init_repo(tmp_path)

    result = _run(probe)

    assert result.returncode == 0, result.stdout + result.stderr
    lines = result.stdout.rstrip("\n").splitlines()
    assert lines[-2].startswith("EXIT GATE GREEN"), result.stdout
    assert lines[-1].startswith("record: ")
    assert "TODO" not in result.stdout and "INCOMPLETE" not in result.stdout
    assert "BANNED" not in result.stdout and "RED" not in result.stdout


def test_outside_a_git_work_tree_the_tree_is_null_and_green_is_kept(tmp_path: Path) -> None:
    probe = _full(tmp_path, _conf(["tests|python3 scripts/stub_junit.py 1 0 0"], collect="echo 1"),
                  git=False)

    result = _run(probe)

    assert result.returncode == 0, result.stdout
    assert "EXIT GATE GREEN" in result.stdout
    rec = _record(tmp_path, result)
    assert rec["tree"]["before"] is None and rec["tree"]["after"] is None


def test_a_missing_recorder_is_red_not_a_silent_skip(tmp_path: Path) -> None:
    probe = _full(tmp_path, _conf(["tests|echo STEP-RAN"]))
    (tmp_path / "scripts" / "verify_record.py").unlink()

    result = _run(probe)

    assert result.returncode == 1, result.stdout
    assert "EXIT GATE RED — recorder missing (scripts/verify_record.py)" in result.stdout
    assert "STEP-RAN" not in result.stdout


def test_a_failing_step_still_shows_its_time_and_the_gate_is_red(tmp_path: Path) -> None:
    probe = _full(tmp_path, _conf(["lint|false"], test_steps=""))

    result = _run(probe)

    assert result.returncode == 1, result.stdout
    assert re.search(r"^  FAIL lint\s+\(\d+s\) \(exit 1\)$", result.stdout, re.M), result.stdout
    assert _record(tmp_path, result)["steps"][0]["exit"] == 1


def test_records_are_pruned_to_the_twenty_newest(tmp_path: Path) -> None:
    probe = _full(tmp_path, _conf(["lint|echo lint"], test_steps=""))
    runs = tmp_path / ".verify" / "runs"
    for i in range(25):
        (runs / ("20200101T0000%02dZ-1" % i)).mkdir(parents=True)

    result = _run(probe)

    assert result.returncode == 0, result.stdout
    kept = sorted(p.name for p in runs.iterdir())
    assert len(kept) == 20
    assert _last(result).split("/")[2] in kept


# ---------------------------------------------------------------------------
# AC-AC11 / AC-AC12 — budgets warn, never fail
# ---------------------------------------------------------------------------


def test_ac11_budgets_warn_and_list_the_slowest_without_changing_the_verdict(
    tmp_path: Path,
) -> None:
    probe = _full(tmp_path, _conf(
        ["tests|python3 scripts/stub_junit.py 3 0 0 --slow=2.5"],
        collect="echo 3", extra="VERIFY_STEP_BUDGET_S=0\n"))

    result = _run(probe)

    assert result.returncode == 0, result.stdout
    assert "EXIT GATE GREEN" in result.stdout
    warns = [ln for ln in result.stdout.splitlines() if ln.startswith("WARN")]
    assert any("tests" in w and "tests.test_stub::test_pass_0" in w and "small" in w
               for w in warns), result.stdout
    lines = result.stdout.splitlines()
    start = lines.index("slowest tests:")
    listed = [ln for ln in lines[start + 1:] if ln.startswith("- ")]
    assert 1 <= len(listed) <= 10
    assert "tests.test_stub::test_pass_0" in listed[0]
    rec = _record(tmp_path, result)
    assert rec["slowest"][0]["id"] == "tests.test_stub::test_pass_0"
    assert rec["warnings"]


def test_a_size_rule_raises_the_budget_for_matching_tests(tmp_path: Path) -> None:
    probe = _full(tmp_path, _conf(
        ["tests|python3 scripts/stub_junit.py 3 0 0 --slow=5 --cls=tests.integration.test_db"],
        collect="echo 3", extra="VERIFY_TEST_SIZE_RULES='tests/integration/*=large'\n"))

    result = _run(probe)

    assert result.returncode == 0, result.stdout
    assert not [ln for ln in result.stdout.splitlines() if ln.startswith("WARN")], result.stdout
    assert _record(tmp_path, result)["slowest"][0]["size"] == "large"


def test_ac12_the_example_conf_states_the_size_class_budgets() -> None:
    """Spec names tests/framework/test_doc_contracts.py for this row; it lives
    here because that file is owned by a parallel increment (see handoff)."""
    text = _EXAMPLE_CONF.read_text(encoding="utf-8")
    for line in ("VERIFY_TEST_BUDGET_SMALL_S=1", "VERIFY_TEST_BUDGET_MEDIUM_S=10",
                 "VERIFY_TEST_BUDGET_LARGE_S=60"):
        assert re.search(r"^#?\s*" + re.escape(line) + r"\s*$", text, re.M), line
    assert "VERIFY_TEST_SIZE_RULES" in text
    assert "VERIFY_ALLOWED_FILTERS" in text
    assert ".claude" not in text


def test_the_example_conf_copied_verbatim_keeps_a_gate_green(tmp_path: Path) -> None:
    """A project that copies the example and changes nothing must not go red."""
    probe = _copy(tmp_path, _FULL, *_STUB_PERMANENT, *_fill_in_script_steps())
    _write_conf(tmp_path, _EXAMPLE_CONF.read_text(encoding="utf-8"))
    _init_repo(tmp_path)

    result = _run(probe)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "EXIT GATE GREEN" in result.stdout


# ---------------------------------------------------------------------------
# AC-AC6 / AC-AC7 — the fast tier never says more than it ran
# ---------------------------------------------------------------------------


def test_ac6_the_fast_tier_states_a_partial_run_with_counts(tmp_path: Path) -> None:
    probe = _fast(tmp_path, "LINT=(echo lint ran)\n"
                            "TEST=(python3 scripts/stub_junit.py 3 0 0)\n"
                            "VERIFY_COLLECT_CMD='echo 10'\n")

    result = _run(probe, "x.py")

    assert result.returncode == 0, result.stdout + result.stderr
    assert _last(result) == "FAST VERIFY OK — partial run: ran 3 of 10"
    assert "GREEN" not in result.stdout and "suite passes" not in result.stdout


def test_ac6_the_fast_tier_without_counts_says_so(tmp_path: Path) -> None:
    probe = _fast(
        tmp_path, None,
        ('LINT=(echo "TODO: set LINT in scripts/verify-fast.sh — e.g. ruff check")',
         'LINT=(echo "lint ran")'),
        ('TEST=(echo "TODO: set TEST in scripts/verify-fast.sh — e.g. pytest -q")',
         'TEST=(echo "tests ran")'),
    )

    result = _run(probe, "x.py")

    assert result.returncode == 0, result.stdout + result.stderr
    assert _last(result) == "FAST VERIFY OK — partial run: ran ? of ? (counts not configured)"
    assert "GREEN" not in result.stdout


def test_ac7_a_fast_run_of_zero_tests_is_empty_and_exits_1(tmp_path: Path) -> None:
    probe = _fast(tmp_path, "LINT=(echo lint ran)\n"
                            "TEST=(python3 scripts/stub_junit.py 0 0 0)\n"
                            "VERIFY_COLLECT_CMD='echo 10'\n")

    result = _run(probe, "x.py")

    assert result.returncode == 1, result.stdout
    assert _last(result) == "FAST VERIFY EMPTY — ran 0 of 10; nothing was verified"
    assert "FAST VERIFY OK" not in result.stdout


# ---------------------------------------------------------------------------
# AC-AC8 / AC-AC16 … AC-AC19 — bans and the declared allow-list
# ---------------------------------------------------------------------------

#: (form as written in a command, token the BANNED line names)
_BANNED_FORMS = [
    ("--lf", "--lf"),
    ("--last-failed", "--last-failed"),
    ("-x", "-x"),
    ("--exitfirst", "--exitfirst"),
    ("--maxfail", "--maxfail"),
    ("--maxfail=1", "--maxfail=1"),
    ("--bail", "--bail"),
    ("--bail=1", "--bail=1"),
    ("-k smoke", "-k"),
    ("-ksmoke", "-ksmoke"),
    ("-m smoke", "-m"),
    ("--deselect t::x", "--deselect"),
    ("--reruns 2", "--reruns"),
    ("--reruns=2", "--reruns=2"),
    ("--retries 2", "--retries"),
    ("--retries=2", "--retries=2"),
    ("--retry 2", "--retry"),
    ("--retry=2", "--retry=2"),
    ("--flake-finder", "--flake-finder"),
    ("--cache_test_results=yes", "--cache_test_results=yes"),
    ("--cache-test-results", "--cache-test-results"),
]


@pytest.mark.parametrize(("form", "token"), _BANNED_FORMS)
def test_ac8_a_banned_form_in_a_configured_full_step_is_refused_before_any_step_runs(
    tmp_path: Path, form: str, token: str
) -> None:
    probe = _full(tmp_path, _conf(["lint|echo STEP-RAN", "tests|pytest %s" % form]))

    result = _run(probe)

    assert result.returncode == 2, result.stdout + result.stderr
    assert any(ln.startswith("BANNED: " + token) for ln in result.stdout.splitlines()), result.stdout
    assert "STEP-RAN" not in result.stdout
    assert "EXIT GATE" not in result.stdout


@pytest.mark.parametrize(("form", "token"), _BANNED_FORMS)
def test_ac8_a_banned_form_in_the_fast_tier_config_is_refused(
    tmp_path: Path, form: str, token: str
) -> None:
    probe = _fast(tmp_path, "LINT=(echo STEP-RAN)\nTEST=(pytest %s)\n" % form)

    result = _run(probe, "x.py")

    assert result.returncode == 2, result.stdout + result.stderr
    assert any(ln.startswith("BANNED: " + token) for ln in result.stdout.splitlines()), result.stdout
    assert "STEP-RAN" not in result.stdout


@pytest.mark.parametrize(("form", "token"), _BANNED_FORMS)
def test_ac8_a_banned_form_passed_to_the_fast_tier_is_refused(
    tmp_path: Path, form: str, token: str
) -> None:
    probe = _fast(tmp_path, "LINT=(echo STEP-RAN)\nTEST=(echo STEP-RAN)\n")

    result = _run(probe, "x.py", *form.split())

    assert result.returncode == 2, result.stdout + result.stderr
    assert any(ln.startswith("BANNED: " + token + " — ") for ln in result.stdout.splitlines()), (
        result.stdout)
    assert "STEP-RAN" not in result.stdout


def test_ac8_the_interpreter_m_flag_is_not_refused(tmp_path: Path) -> None:
    probe = _full(tmp_path, _conf(
        ["tests|python3 -m pytest --version >/dev/null && python3 scripts/stub_junit.py 1 0 0"],
        collect="echo 1"))

    result = _run(probe)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "BANNED" not in result.stdout


def test_ac8_the_shipped_default_steps_pass_the_ban_check(tmp_path: Path) -> None:
    """The real STEPS (stubbed only where they would recurse) must not trip the
    ban — `python3 -m pytest` is the interpreter's `-m`."""
    probe = _copy(tmp_path, _FULL, *_STUB_PERMANENT)
    body = _FULL.read_text(encoding="utf-8")
    assert "python3 -m pytest" in body

    result = _run(probe)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "BANNED" not in result.stdout


def test_ac8_a_project_can_add_a_banned_token(tmp_path: Path) -> None:
    probe = _full(tmp_path, _conf(["tests|mytool --only-changed"],
                                  extra="VERIFY_EXTRA_BANNED='--only-changed'\n"))

    result = _run(probe)

    assert result.returncode == 2, result.stdout
    assert "BANNED: --only-changed — project-declared" in result.stdout.splitlines()


_ALLOW = "VERIFY_ALLOWED_FILTERS=('-m \"not real_sleep\"|real-sleep tests run in the nightly job')\n"


def test_ac16_a_declared_filter_runs_and_is_printed_every_time(tmp_path: Path) -> None:
    probe = _full(tmp_path, _conf(
        ['tests|echo -m "not real_sleep" && python3 scripts/stub_junit.py 2 0 0'],
        collect="echo 2", extra=_ALLOW))

    result = _run(probe)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "EXIT GATE GREEN" in result.stdout
    expected = 'declared filter: -m "not real_sleep" — real-sleep tests run in the nightly job'
    assert expected in result.stdout.splitlines()
    assert _record(tmp_path, result)["declared_filters"] == [
        {"filter": '-m "not real_sleep"', "reason": "real-sleep tests run in the nightly job"}
    ]


def test_ac16_the_fast_tier_prints_the_declared_filter_too(tmp_path: Path) -> None:
    probe = _fast(tmp_path, "LINT=(echo lint)\nTEST=(echo -m 'not real_sleep')\n" + _ALLOW)

    result = _run(probe, "x.py")

    assert result.returncode == 0, result.stdout + result.stderr
    assert ('declared filter: -m "not real_sleep" — real-sleep tests run in the nightly job'
            in result.stdout.splitlines())


def test_ac17_an_undeclared_filter_is_refused(tmp_path: Path) -> None:
    probe = _full(tmp_path, _conf(['lint|echo STEP-RAN', 'tests|pytest -m "not slow"'],
                                  extra=_ALLOW))

    result = _run(probe)

    assert result.returncode == 2, result.stdout
    assert ('BANNED: -m "not slow" — undeclared filter; declare it with a reason in '
            "VERIFY_ALLOWED_FILTERS") in result.stdout.splitlines()
    assert "STEP-RAN" not in result.stdout


@pytest.mark.parametrize("entry", ["'-m \"not real_sleep\"'", "'-m \"not real_sleep\"|'",
                                   "'-m \"not real_sleep\"|   '"])
def test_ac18_an_allow_list_entry_without_a_reason_is_refused(tmp_path: Path, entry: str) -> None:
    """RED-FIRST: planted against a parser that accepts reasonless entries."""
    probe = _full(tmp_path, _conf(['lint|echo STEP-RAN', 'tests|pytest -m "not real_sleep"'],
                                  extra="VERIFY_ALLOWED_FILTERS=(%s)\n" % entry))

    result = _run(probe)

    assert result.returncode == 2, result.stdout
    assert ('BANNED: allow-list entry without a reason: -m "not real_sleep"'
            in result.stdout.splitlines()), result.stdout
    assert "STEP-RAN" not in result.stdout


@pytest.mark.parametrize("flag", ["--lf", "--last-failed", "-x", "--exitfirst", "--maxfail=3",
                                  "--maxfail", "--bail", "--reruns=2", "--retries=1", "--retry",
                                  "--flake-finder", "--cache_test_results=yes",
                                  "--cache-test-results"])
def test_ac19_a_hard_ban_can_never_be_allow_listed(tmp_path: Path, flag: str) -> None:
    probe = _full(tmp_path, _conf(["lint|echo STEP-RAN", "tests|pytest %s" % flag],
                                  extra="VERIFY_ALLOWED_FILTERS=('%s|we really need it')\n" % flag))

    result = _run(probe)

    assert result.returncode == 2, result.stdout
    assert "BANNED: %s can never be allow-listed" % flag in result.stdout.splitlines(), result.stdout
    assert "STEP-RAN" not in result.stdout


def test_ac19_only_marker_and_deselect_filters_can_be_declared(tmp_path: Path) -> None:
    probe = _full(tmp_path, _conf(["lint|echo STEP-RAN"],
                                  extra="VERIFY_ALLOWED_FILTERS=('--verbose|why not')\n"))

    result = _run(probe)

    assert result.returncode == 2, result.stdout
    assert ("BANNED: --verbose — only -m, -k, --deselect, --ignore and --ignore-glob can be declared"
            in result.stdout.splitlines()), result.stdout


def test_ac19_an_allow_listed_filter_passed_at_runtime_is_still_refused(tmp_path: Path) -> None:
    probe = _fast(tmp_path, "LINT=(echo STEP-RAN)\nTEST=(echo STEP-RAN)\n" + _ALLOW)

    result = _run(probe, "x.py", "-m", "not real_sleep")

    assert result.returncode == 2, result.stdout
    assert "BANNED: -m — marker deselection used to reach green" in result.stdout.splitlines()
    assert "STEP-RAN" not in result.stdout


# ---------------------------------------------------------------------------
# Rework after doc/qa/QA-verify-tiers-AC.md — coordinator rulings D6 to D11,
# and the tier-level halves of D1, D2 and D5 that QA's pins do not reach.
# ---------------------------------------------------------------------------

_RECORDER = _REPO_ROOT / "scripts" / "verify_record.py"


def _check_banned(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    run_env = _env() if env is None else env
    run_env.pop("PYTEST_ADDOPTS", None) if env is None else None
    return subprocess.run(
        ["python3", str(_RECORDER), "check-banned", *args],
        capture_output=True, text=True, timeout=60, check=False, env=run_env,
    )


#: D6. Ordinary commands whose flags only LOOK like a ban. None runs a test runner
#: with a ban, so none may be refused, conf or no conf.
_NOT_A_RUNNER_FLAG = [
    "git commit -m msg",
    "tar -x -f a.tar",
    "sort -k 2 registry.txt | wc -l",
    "make -k test",
    "mypy -m pkg",
    "python3 -u -m pytest -q",
    "python -W error -m pytest -q",
    "coverage run -m pytest -q",
    "pytest -rxXs -p no:cacheprovider -n 4 -W error::DeprecationWarning",
]


@pytest.mark.parametrize("command", _NOT_A_RUNNER_FLAG)
def test_d6_a_flag_outside_a_test_runner_is_not_refused(command: str) -> None:
    result = _check_banned("--cmd=" + command)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "BANNED" not in result.stdout


def test_d6_a_project_as_filled_in_today_with_realistic_commands_stays_green(
    tmp_path: Path,
) -> None:
    """AC-AC15 with commands that really run and exit 0, not `echo` stubs."""
    steps = ("python3 -u -m pytest --version && python3 -W error -m pytest --version"
             " && printf 'b 2\\\\na 1\\\\n' | sort -k 2 >/dev/null"
             " && tar -c -f - scripts/stub_junit.py | tar -x -O -f - >/dev/null"
             " && git log -1 -m --oneline >/dev/null")
    probe = _copy(tmp_path, _FULL, *_STUB_PERMANENT,
                  *_fill_in_script_steps((_PLACEHOLDER_STEPS[2], '"tests|%s"' % steps)))
    _write_stub(tmp_path)
    _init_repo(tmp_path)

    result = _run(probe)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "EXIT GATE GREEN" in result.stdout
    assert "BANNED" not in result.stdout


def test_d6_a_project_runner_is_named_on_a_limit_line_and_banned_through_extra_banned(
    tmp_path: Path,
) -> None:
    """Ruling D17 (2026-10-20): only the pytest family has built-in bans. A runner
    the project lists is named on a `limit:` line; its bans are the project's own."""
    listed = _check_banned("--runner=pytest", "--runner=mytester", "--step=tests|mytester --lf")
    banned = _check_banned("--runner=pytest", "--runner=mytester", "--extra=--lf",
                           "--step=tests|mytester --lf")

    assert listed.returncode == 0, listed.stdout + listed.stderr
    assert "BANNED:" not in listed.stdout
    assert any(ln.startswith("limit: step tests runs mytester;")
               for ln in listed.stdout.splitlines()), listed.stdout
    assert banned.returncode == 2, banned.stdout
    assert "BANNED: --lf — project-declared" in banned.stdout.splitlines()


#: D7. (command, the BANNED line's start)
_HIDDEN_BANS = [
    ("pytest -xq", "BANNED: -xq — "),
    ("pytest -qx", "BANNED: -qx — "),
    ("pytest -vvx tests", "BANNED: -vvx — "),
    ("pytest -qk smoke", "BANNED: -qk smoke — undeclared filter"),
    ('pytest -m"not slow"', 'BANNED: -m"not slow" — undeclared filter'),
    ("pytest -mslow", "BANNED: -mslow — undeclared filter"),
    ("pytest -kfoo", "BANNED: -kfoo — undeclared filter"),
    ("pytest --sw", "BANNED: --sw — "),
    ("pytest --stepwise", "BANNED: --stepwise — "),
    ("pytest --ignore=tests/e2e", "BANNED: --ignore=tests/e2e — undeclared filter"),
    ("pytest --ignore tests/e2e", "BANNED: --ignore tests/e2e — undeclared filter"),
    ("pytest --ignore-glob='*e2e*'", "BANNED: --ignore-glob=*e2e* — undeclared filter"),
    ("pytest --ff", "BANNED: --ff — "),
    ("pytest --failed-first", "BANNED: --failed-first — "),
    ("PYTEST_ADDOPTS=-x pytest", "BANNED: -x — "),
    ("PYTEST_ADDOPTS='-q --lf' python3 -m pytest", "BANNED: --lf — "),
    ("export PYTEST_ADDOPTS=--sw; pytest", "BANNED: --sw — "),
    ("uv run pytest -x", "BANNED: -x — "),
]


@pytest.mark.parametrize(("command", "line"), _HIDDEN_BANS)
def test_d7_a_ban_hidden_in_a_cluster_an_attached_value_or_an_env_var_is_refused(
    command: str, line: str
) -> None:
    result = _check_banned("--cmd=" + command)

    assert result.returncode == 2, result.stdout + result.stderr
    assert any(ln.startswith(line) for ln in result.stdout.splitlines()), result.stdout


def test_d7_a_ban_in_the_environment_at_run_time_is_refused(tmp_path: Path) -> None:
    probe = _fast(tmp_path, "LINT=(echo STEP-RAN)\nTEST=(echo STEP-RAN)\n")
    env = _env()
    env["PYTEST_ADDOPTS"] = "-q --lf"

    result = subprocess.run(["bash", str(probe), "x.py"], capture_output=True, text=True,
                            timeout=120, check=False, env=env)

    assert result.returncode == 2, result.stdout + result.stderr
    assert any(ln.startswith("BANNED: --lf — ") and "PYTEST_ADDOPTS" in ln
               for ln in result.stdout.splitlines()), result.stdout
    assert "STEP-RAN" not in result.stdout


def test_d7_the_collect_command_is_scanned_too(tmp_path: Path) -> None:
    probe = _full(tmp_path, _conf(["lint|echo STEP-RAN", "tests|python3 scripts/stub_junit.py 1 0 0"],
                                  collect='pytest --collect-only -q -m "not slow" | tail -1'))

    result = _run(probe)

    assert result.returncode == 2, result.stdout + result.stderr
    assert any(ln.startswith('BANNED: -m "not slow" — undeclared filter')
               for ln in result.stdout.splitlines()), result.stdout
    assert "STEP-RAN" not in result.stdout


def test_d7_a_declared_filter_in_the_collect_command_is_allowed(tmp_path: Path) -> None:
    """pytest sits in command position here, so the waiver is what keeps it green
    (an `echo pytest …` would pass unscanned and prove nothing)."""
    probe = _full(tmp_path, _conf(
        ["tests|python3 scripts/stub_junit.py 2 0 0"],
        collect='python3 -m pytest --version -m "not real_sleep" >/dev/null 2>&1; echo 2',
        extra=_ALLOW))

    result = _run(probe)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "EXIT GATE GREEN" in result.stdout


@pytest.mark.parametrize("command", ['bash -c "pytest -x"', 'eval "$RUN_TESTS"'])
def test_d7_eval_and_bash_c_are_a_stated_limit_not_a_silent_pass(command: str) -> None:
    result = _check_banned("--cmd=" + command)

    assert result.returncode == 0, result.stdout
    limits = [ln for ln in result.stdout.splitlines() if ln.startswith("limit: ")]
    assert len(limits) == 1, result.stdout
    assert command in limits[0]


def test_d7_ignore_can_be_declared_with_a_reason(tmp_path: Path) -> None:
    probe = _full(tmp_path, _conf(
        ["tests|python3 -m pytest --version --ignore=tests/e2e >/dev/null 2>&1;"
         " python3 scripts/stub_junit.py 1 0 0"],
        extra="VERIFY_ALLOWED_FILTERS=('--ignore=tests/e2e|e2e runs in the nightly job')\n"))

    result = _run(probe)

    assert result.returncode == 0, result.stdout + result.stderr
    assert ("declared filter: --ignore=tests/e2e — e2e runs in the nightly job"
            in result.stdout.splitlines())


def test_d8_the_local_runner_id_never_carries_the_hostname(tmp_path: Path) -> None:
    import hashlib
    import socket

    probe = _full(tmp_path, _conf(["tests|python3 scripts/stub_junit.py 1 0 0"], collect="echo 1"))

    result = _run(probe)

    rec = _record(tmp_path, result)
    host = socket.gethostname()
    assert rec["runner"] == {
        "id": "local:" + hashlib.sha256(host.encode("utf-8")).hexdigest()[:12], "kind": "local"}
    record_text = (tmp_path / _last(result)[len("record: "):]).read_text(encoding="utf-8")
    assert host not in record_text


def test_d9_a_failing_collect_in_the_fast_tier_says_so(tmp_path: Path) -> None:
    probe = _fast(tmp_path, "LINT=(echo lint ran)\n"
                            "TEST=(python3 scripts/stub_junit.py 3 0 0)\n"
                            "VERIFY_COLLECT_CMD='echo 10; false'\n")

    result = _run(probe, "x.py")

    assert result.returncode == 0, result.stdout + result.stderr
    assert _last(result) == "FAST VERIFY OK — partial run: ran 3 of ? — collect failed (exit 1)"
    assert "counts not configured" not in result.stdout


def test_d9_without_a_collect_command_the_fast_tier_says_ran_n_of_unknown(tmp_path: Path) -> None:
    probe = _fast(tmp_path, "LINT=(echo lint ran)\nTEST=(python3 scripts/stub_junit.py 3 0 0)\n")

    result = _run(probe, "x.py")

    assert result.returncode == 0, result.stdout + result.stderr
    assert _last(result) == "FAST VERIFY OK — partial run: ran 3 of ? (counts not configured)"


def test_d10_a_crashed_recorder_never_prints_a_record_path_that_was_not_written(
    tmp_path: Path,
) -> None:
    # A broken JUnit file no longer crashes the recorder (it is RED with a record),
    # so the crash is planted in the copied recorder itself.
    probe = _full(tmp_path, _conf(["tests|python3 scripts/stub_junit.py 1 0 0"]))
    recorder = tmp_path / "scripts" / "verify_record.py"
    body = recorder.read_text(encoding="utf-8")
    anchor = "def cmd_finalize(args: argparse.Namespace) -> int:\n"
    assert body.count(anchor) == 1
    recorder.write_text(body.replace(anchor, anchor + "    raise RuntimeError('planted crash')\n"),
                        encoding="utf-8")

    result = _run(probe)

    assert result.returncode == 1, result.stdout
    assert "EXIT GATE RED" in result.stdout
    assert _last(result).startswith("record: not written ("), result.stdout
    assert not any(ln.startswith("record: .verify") for ln in result.stdout.splitlines())


def test_d11_fast_runs_never_evict_a_full_record(tmp_path: Path) -> None:
    probe = _fast(tmp_path, "LINT=(echo lint)\nTEST=(python3 scripts/stub_junit.py 1 0 0)\n")
    runs = tmp_path / ".verify" / "runs"
    full = runs / "20200101T000000Z-1"
    full.mkdir(parents=True)
    for i in range(25):
        (runs / ("20200102T0000%02dZ-1-fast" % i)).mkdir()

    result = _run(probe, "x.py")

    assert result.returncode == 0, result.stdout + result.stderr
    assert full.is_dir()
    assert len([p for p in runs.iterdir() if p.name.endswith("-fast")]) == 20


def test_d1_the_fast_tier_is_red_over_a_masked_failure(tmp_path: Path) -> None:
    probe = _fast(tmp_path, "LINT=(echo lint)\n"
                            "TEST=(bash -c 'python3 scripts/stub_junit.py 2 1 0; true')\n")

    result = _run(probe, "x.py")

    assert result.returncode == 1, result.stdout + result.stderr
    assert _last(result) == "FAST VERIFY RED — 1 test(s) failed in the JUnit report"


def test_d2_the_fast_tier_refuses_a_conf_that_fails_to_load(tmp_path: Path) -> None:
    probe = _fast(tmp_path, "LINT=(echo STEP-RAN)\nfi\nTEST=(echo STEP-RAN)\n")

    result = _run(probe, "x.py")

    assert result.returncode == 2, result.stdout + result.stderr
    assert "verify.conf failed to load" in result.stdout
    assert "STEP-RAN" not in result.stdout


def test_d3_two_test_steps_with_one_label_are_refused_before_any_step_runs(
    tmp_path: Path,
) -> None:
    probe = _full(tmp_path, _conf(["tests|echo STEP-RAN", "tests|echo STEP-RAN"]))

    result = _run(probe)

    assert result.returncode == 1, result.stdout
    assert any(ln.startswith("EXIT GATE RED — duplicate test step label: tests")
               for ln in result.stdout.splitlines()), result.stdout
    assert "STEP-RAN" not in result.stdout


def test_d5_an_unset_step_list_is_red(tmp_path: Path) -> None:
    probe = _full(tmp_path, "unset STEPS\n")

    result = _run(probe)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "EXIT GATE RED — no steps configured" in result.stdout.splitlines()


def test_d5_the_recorder_never_calls_an_empty_run_green(tmp_path: Path) -> None:
    """The bash >= 4.4 path: the loop runs nothing and finalize sees no steps."""
    (tmp_path / "steps.tsv").write_text("", encoding="utf-8")

    result = subprocess.run(
        ["python3", str(_RECORDER), "finalize", "--tier", "full", "--run-dir", str(tmp_path),
         "--conf-present"], capture_output=True, text=True, timeout=60, check=False, env=_env())

    assert result.stdout.splitlines()[-1] == "VERDICT=RED", result.stdout + result.stderr
    assert "no steps configured" in result.stdout.splitlines()


# ---------------------------------------------------------------------------
# Re-test 1 rework — coordinator ruling D12 to D18 (2026-10-20): a built-in ban
# table for the pytest family only, found in command position after wrappers;
# every other runner, and a listed test step with no pytest runner, is named on
# a `limit:` line; the conf is checked for syntax with `bash -n`.
# ---------------------------------------------------------------------------

_LIMIT_TAIL = "its flags are not scanned — declare bans in VERIFY_EXTRA_BANNED"

#: (command, the BANNED line's start): the pytest family behind each wrapper.
_PYTEST_SPELLINGS = [
    ("python3 -mpytest -x", "BANNED: -x — "),
    ("python3 -u -m pytest -x", "BANNED: -x — "),
    ("python -W error -m pytest --lf", "BANNED: --lf — "),
    ("python3 -X dev -mpytest --sw", "BANNED: --sw — "),
    ("python3.12 -m pytest --ff", "BANNED: --ff — "),
    ("python3 -m py.test -x", "BANNED: -x — "),
    ("python3 .venv/bin/pytest --lf", "BANNED: --lf — "),
    ("coverage run -m pytest -x", "BANNED: -x — "),
    ("coverage run --branch -m pytest -x", "BANNED: -x — "),
    ("coverage run --branch -mpytest --lf", "BANNED: --lf — "),
    ("uv run pytest --reruns 2", "BANNED: --reruns — "),
    ("uv run python -m pytest -x", "BANNED: -x — "),
    ("env -i PYTEST_X=1 pytest --lf", "BANNED: --lf — "),
    ("FOO=1 .venv/bin/pytest -x", "BANNED: -x — "),
    ("py.test --lf", "BANNED: --lf — "),
    ("cd sub && pytest -x", "BANNED: -x — "),
    ("pytest -q | tee log && pytest --lf", "BANNED: --lf — "),
]


@pytest.mark.parametrize(("command", "line"), _PYTEST_SPELLINGS)
def test_rt1_the_pytest_family_is_found_behind_every_wrapper(command: str, line: str) -> None:
    result = _check_banned("--cmd=" + command)

    assert result.returncode == 2, result.stdout + result.stderr
    assert any(ln.startswith(line) for ln in result.stdout.splitlines()), result.stdout


#: Plugin and variant spellings the ruling adds (prefix forms).
@pytest.mark.parametrize("form", ["--sw-reset", "--stepwise-reset", "--last-failed-no-failures",
                                  "--lfnf=all", "--reruns-delay", "--reruns-delay=1"])
def test_rt1_lf_ff_sw_and_reruns_variants_are_refused(form: str) -> None:
    result = _check_banned("--cmd=pytest " + form)

    assert result.returncode == 2, result.stdout + result.stderr
    assert any(ln.startswith("BANNED: %s — " % form) for ln in result.stdout.splitlines()), (
        result.stdout)


@pytest.mark.parametrize("command", [
    "pytest --cache-clear -q",
    "pytest --new-first -q",
    "echo pytest -x",
    "make -C tools/pytest -x",
    "timeout 600 echo --lf",
    "go test -x ./...",
    "go test -failfast -timeout 5m ./...",
    "go test -run TestFoo -count=1 ./...",
    "jest --onlyFailures -b",
    "cargo test -- --retries 2",
    "npm test -- --bail",
])
def test_rt1_only_a_pytest_runner_in_command_position_is_scanned(command: str) -> None:
    result = _check_banned("--cmd=" + command)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "BANNED" not in result.stdout


def _limit_lines(result: subprocess.CompletedProcess[str]) -> list[str]:
    return [ln for ln in result.stdout.splitlines() if ln.startswith("limit:")]


@pytest.mark.parametrize("command", ["cargo nextest run --retries 2",
                                     "bazel test //... --cache_test_results=yes"])
def test_rt1_a_test_step_with_no_pytest_runner_states_the_limit(command: str) -> None:
    """D14/D16, the honest form: not refused (the flags are not guessed), but said."""
    result = _check_banned("--test-steps=tests", "--step=tests|" + command)

    assert result.returncode == 0, result.stdout + result.stderr
    assert _limit_lines(result) == [
        "limit: step tests runs no known runner; " + _LIMIT_TAIL], result.stdout


@pytest.mark.parametrize(("runner", "command"), [
    ("cargo nextest", "cargo nextest run --retries 2"),
    ("bazel test", "bazel test //... --cache_test_results=yes"),
    ("jest", "jest --bail"),
])
def test_rt1_a_listed_runner_is_named_and_its_bans_come_from_extra_banned(
    runner: str, command: str,
) -> None:
    named = _check_banned("--runner=" + runner, "--step=tests|" + command)
    banned = _check_banned("--runner=" + runner, "--extra=--retries --cache_test_results --bail",
                           "--step=tests|" + command)

    assert _limit_lines(named) == [
        "limit: step tests runs %s; %s" % (runner, _LIMIT_TAIL)], named.stdout
    assert named.returncode == 0, named.stdout
    assert banned.returncode == 2, banned.stdout
    assert any(ln.endswith("— project-declared") for ln in banned.stdout.splitlines())


def test_rt1_one_limit_line_per_step_and_none_for_a_scanned_step() -> None:
    result = _check_banned("--runner=pytest", "--runner=jest", "--test-steps=tests unit",
                           "--step=tests|jest a && jest b", "--step=unit|python3 -m pytest -q",
                           "--step=lint|sort -k 2 x | wc -l")

    assert result.returncode == 0, result.stdout
    assert _limit_lines(result) == ["limit: step tests runs jest; " + _LIMIT_TAIL], result.stdout


def test_rt1_a_step_command_with_a_pipe_is_split_on_its_first_bar() -> None:
    result = _check_banned("--step=tests|cat list | pytest --lf")

    assert result.returncode == 2, result.stdout
    assert any(ln.startswith("BANNED: --lf — ") for ln in result.stdout.splitlines())


def test_rt1_a_declared_filter_in_a_real_pytest_command_is_waived() -> None:
    """AC-AC16's teeth: pytest in command position, the filter declared → not refused."""
    allow = '--allow=-m "not real_sleep"|real-sleep tests run in the nightly job'

    waived = _check_banned(allow, '--cmd=python3 -m pytest -m "not real_sleep"')
    other = _check_banned(allow, '--cmd=python3 -m pytest -m "not slow"')

    assert waived.returncode == 0, waived.stdout
    assert ('declared filter: -m "not real_sleep" — real-sleep tests run in the nightly job'
            in waived.stdout.splitlines())
    assert other.returncode == 2, other.stdout


def test_rt1_the_full_gate_records_the_limit_and_keeps_its_verdict(tmp_path: Path) -> None:
    """A listed test step that runs no pytest: GREEN as before, one `limit:` line,
    and the same line in the record's warnings."""
    probe = _full(tmp_path, _conf(["tests|python3 scripts/stub_junit.py 3 0 0"], collect="echo 3"))

    result = _run(probe)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "EXIT GATE GREEN" in result.stdout
    expected = "limit: step tests runs no known runner; " + _LIMIT_TAIL
    assert _limit_lines(result) == [expected], result.stdout
    assert expected in _record(tmp_path, result)["warnings"]


def test_rt1_the_full_gate_names_a_listed_runner(tmp_path: Path) -> None:
    probe = _full(tmp_path, _conf(["tests|python3 scripts/stub_junit.py 3 0 0"], collect="echo 3",
                                  extra="VERIFY_TEST_RUNNERS=(pytest stub_junit.py)\n"))

    result = _run(probe)

    assert result.returncode == 0, result.stdout + result.stderr
    assert _limit_lines(result) == ["limit: step tests runs stub_junit.py; " + _LIMIT_TAIL]


def test_rt1_extra_banned_refuses_in_an_unscanned_test_step(tmp_path: Path) -> None:
    probe = _full(tmp_path, _conf(
        ["lint|echo STEP-RAN", "tests|python3 scripts/stub_junit.py 3 0 0 --retries=2"],
        collect="echo 3", extra="VERIFY_EXTRA_BANNED='--retries'\n"))

    result = _run(probe)

    assert result.returncode == 2, result.stdout
    assert "BANNED: --retries=2 — project-declared" in result.stdout.splitlines()
    assert "STEP-RAN" not in result.stdout


def test_rt1_a_project_with_no_conf_prints_no_limit_line(tmp_path: Path) -> None:
    """R12: the shipped steps and an unfilled fast tier add no new line."""
    (tmp_path / "full").mkdir()
    (tmp_path / "fast").mkdir()
    full = _run(_copy(tmp_path / "full", _FULL, *_STUB_PERMANENT))
    fast = _run(_fast(tmp_path / "fast"), "x.py")

    assert full.returncode == 0 and fast.returncode == 0, full.stdout + fast.stdout
    assert _limit_lines(full) == [] and _limit_lines(fast) == [], full.stdout + fast.stdout


def test_rt1_the_fast_tier_names_a_listed_runner_but_never_no_known_runner(
    tmp_path: Path,
) -> None:
    probe = _fast(tmp_path, "LINT=(echo lint)\nTEST=(python3 scripts/stub_junit.py 1 0 0)\n"
                  "VERIFY_TEST_STEPS=tests\nVERIFY_TEST_RUNNERS=(pytest stub_junit.py)\n")

    result = _run(probe, "x.py")

    assert result.returncode == 0, result.stdout + result.stderr
    assert _limit_lines(result) == ["limit: step tests runs stub_junit.py; " + _LIMIT_TAIL]


def test_rt1_a_fast_conf_whose_last_test_is_false_still_loads(tmp_path: Path) -> None:
    """D18, fast tier: only a syntax error is a load failure."""
    probe = _fast(tmp_path, "LINT=(echo lint)\nTEST=(python3 scripts/stub_junit.py 1 0 0)\n"
                  '[ -n "${QA_NEVER_SET_FLAG:-}" ] && VERIFY_STEP_BUDGET_S=600\n')

    result = _run(probe, "x.py")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "failed to load" not in result.stdout
    assert _last(result).startswith("FAST VERIFY OK")


def test_rt1_a_same_size_edit_with_an_unchanged_mtime_is_hashed_by_content(
    tmp_path: Path,
) -> None:
    """Racy git: the recorder hashes through a COPY of the index, whose fresh mtime
    makes every entry look stat-clean. An edit that keeps size and mtime was hashed
    as the committed content — a record naming a tree that is not on disk (AC-AC10),
    and the cause of test_ac3's intermittent "tree changed during the run"."""
    f = tmp_path / "f.txt"
    f.write_text("count 4\n", encoding="utf-8")
    os.utime(f, (1_000_000_000, 1_000_000_000))
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "core.trustctime", "false")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-q", "-m", "init")
    f.write_text("count 5\n", encoding="utf-8")
    os.utime(f, (1_000_000_000, 1_000_000_000))

    tree = subprocess.run(["python3", str(_RECORDER), "tree-hash"], cwd=tmp_path,
                          capture_output=True, text=True, check=True, env=_env()).stdout.strip()

    assert _git(tmp_path, "cat-file", "-p", tree + ":f.txt") == "count 5"


@pytest.mark.parametrize("runner", ["python3", "uv", "coverage", "env"])
def test_rt1_listing_a_wrapper_as_a_runner_cannot_hide_pytest(runner: str) -> None:
    command = {"python3": "python3 -m pytest -x", "uv": "uv run pytest -x",
               "coverage": "coverage run -m pytest -x", "env": "env pytest -x"}[runner]

    result = _check_banned("--runner=" + runner, "--cmd=" + command)

    assert result.returncode == 2, result.stdout
    assert any(ln.startswith("BANNED: -x — ") for ln in result.stdout.splitlines())


@pytest.mark.parametrize(("command", "line"), [
    ("if pytest --lf; then echo ok; fi", "BANNED: --lf — "),
    ("! pytest -x", "BANNED: -x — "),
    ("{ pytest -x; }", "BANNED: -x — "),
    ("time pytest -x", "BANNED: -x — "),
    ("time -p python3 -m pytest -x", "BANNED: -x — "),
    ("while pytest --sw; do :; done", "BANNED: --sw — "),
    ("until pytest -x; do :; done", "BANNED: -x — "),
    ("if true; then pytest -x; else pytest --ff; fi", "BANNED: --ff — "),
])
def test_rt1_shell_grammar_before_pytest_is_not_the_program(command: str, line: str) -> None:
    """D15: the command position comes after the shell's reserved words."""
    result = _check_banned("--cmd=" + command)

    assert result.returncode == 2, result.stdout + result.stderr
    assert any(ln.startswith(line) for ln in result.stdout.splitlines()), result.stdout


# ---------------------------------------------------------------------------
# AC-AC24 — retry-plugin flags are hard bans (amendment 2, AM2-ADR-3)
# doc/specs/SPEC-verify-tiers-merge-gate-am2-scanner-scope.md
# ---------------------------------------------------------------------------

_RETRY_REASON = " — retries turn a failure into a pass"

#: (configured command, token the BANNED line names)
_RETRY_PLUGIN_FORMS = [
    ("pytest --force-flaky", "--force-flaky"),
    ("pytest --max-runs 3", "--max-runs"),
    ("pytest --max-runs=3", "--max-runs=3"),
    ("python3 -m pytest -q --force-flaky", "--force-flaky"),
    ("PYTEST_ADDOPTS=--max-runs=2 pytest", "--max-runs=2"),
]


@pytest.mark.parametrize(("command", "token"), _RETRY_PLUGIN_FORMS)
def test_ac24_a_retry_plugin_flag_in_a_full_step_is_refused_before_any_step_runs(
    tmp_path: Path, command: str, token: str
) -> None:
    probe = _full(tmp_path, _conf(["lint|echo STEP-RAN", "tests|%s" % command]))

    result = _run(probe)

    assert result.returncode == 2, result.stdout + result.stderr
    assert any(ln.startswith("BANNED: " + token + _RETRY_REASON)
               for ln in result.stdout.splitlines()), result.stdout
    assert "STEP-RAN" not in result.stdout
    assert "EXIT GATE" not in result.stdout


@pytest.mark.parametrize(("command", "token"), _RETRY_PLUGIN_FORMS)
def test_ac24_a_retry_plugin_flag_in_the_fast_tier_config_is_refused(
    tmp_path: Path, command: str, token: str
) -> None:
    probe = _fast(tmp_path, "LINT=(echo STEP-RAN)\nTEST=(%s)\n" % command)

    result = _run(probe, "x.py")

    assert result.returncode == 2, result.stdout + result.stderr
    assert any(ln.startswith("BANNED: " + token + _RETRY_REASON)
               for ln in result.stdout.splitlines()), result.stdout
    assert "STEP-RAN" not in result.stdout


@pytest.mark.parametrize("args", [["--force-flaky"], ["--max-runs", "3"], ["--max-runs=3"]])
def test_ac24_a_retry_plugin_flag_passed_to_the_fast_tier_is_refused(
    tmp_path: Path, args: list[str]
) -> None:
    probe = _fast(tmp_path, "LINT=(echo STEP-RAN)\nTEST=(echo STEP-RAN)\n")

    result = _run(probe, "x.py", *args)

    assert result.returncode == 2, result.stdout + result.stderr
    assert any(ln.startswith("BANNED: " + args[0] + _RETRY_REASON)
               for ln in result.stdout.splitlines()), result.stdout
    assert "STEP-RAN" not in result.stdout


@pytest.mark.parametrize("flag", ["--force-flaky", "--max-runs", "--max-runs=3"])
def test_ac24_a_retry_plugin_flag_can_never_be_allow_listed(tmp_path: Path, flag: str) -> None:
    probe = _full(tmp_path, _conf(["lint|echo STEP-RAN", "tests|pytest %s" % flag],
                                  extra="VERIFY_ALLOWED_FILTERS=('%s|flaky suite')\n" % flag))

    result = _run(probe)

    assert result.returncode == 2, result.stdout
    assert "BANNED: %s can never be allow-listed" % flag in result.stdout.splitlines(), result.stdout
    assert "STEP-RAN" not in result.stdout


def test_ac24_flake_runs_alone_is_a_declared_limit_not_a_ban() -> None:
    """L7: --flake-runs repeats nothing without --flake-finder, which is banned."""
    result = _check_banned("--test-steps=tests", "--step=tests|pytest --flake-runs 3")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "BANNED" not in result.stdout
