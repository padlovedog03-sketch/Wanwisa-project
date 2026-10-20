"""QA regression tests for increment A+C (no fake green), from doc/qa/QA-verify-tiers-AC.md.

Each test below except the last pins a fake-green or ban-bypass route that QA found
in the A+C implementation (commits 46c5930, cb76109). They are red against that code
on purpose: the defect list in the QA report names the fix each one waits for.

Every case runs a stubbed COPY of the scripts in `tmp_path` through the helpers of
`test_verify_tiers.py` (which are built on `test_verify_scripts._copy`). Running the
real `verify-full.sh` from here would recurse without bound.

Run: `python3 -m pytest tests/hooks/test_regression_verify_tiers_qa.py -q`
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from test_verify_tiers import _conf, _fast, _full, _last, _run


def _green(result: subprocess.CompletedProcess[str]) -> bool:
    return any(ln.startswith("EXIT GATE GREEN") for ln in result.stdout.splitlines())


def test_regression_a_test_step_failure_masked_by_its_exit_code_is_red(tmp_path: Path) -> None:
    """D1. The JUnit says 1 test failed, but `|| true` makes the step exit 0.
    Design §AC.2: failures (all are new when no baseline is set) → RED."""
    probe = _full(tmp_path, _conf(["tests|python3 scripts/stub_junit.py 3 1 0 || true"],
                                  collect="echo 4"))

    result = _run(probe)

    assert result.returncode == 1, result.stdout
    assert not _green(result), result.stdout
    assert "EXIT GATE RED" in result.stdout


def test_regression_a_conf_that_stops_parsing_cannot_drop_the_test_step_check(
    tmp_path: Path,
) -> None:
    """D2. A syntax error on line 2 of the conf leaves STEPS set and
    VERIFY_TEST_STEPS unset; the listed step writes no JUnit at all."""
    conf = "STEPS=('tests|true')\nfi\nVERIFY_TEST_STEPS=\"tests\"\n"
    probe = _full(tmp_path, conf)

    result = _run(probe)

    assert result.returncode != 0, result.stdout + result.stderr
    assert not _green(result), result.stdout
    assert "EXIT GATE RED" in result.stdout, result.stdout


def test_regression_two_steps_sharing_a_test_label_are_not_double_counted(
    tmp_path: Path,
) -> None:
    """D3. Two steps labelled `tests` share one JUnit directory: 3 cases ran, the
    second step wrote nothing, yet each step counts the shared 3 → `6 of 6`."""
    probe = _full(tmp_path, _conf(
        ["tests|python3 scripts/stub_junit.py 3 0 0", "tests|true"], collect="echo 6"))

    result = _run(probe)

    assert result.returncode == 1, result.stdout
    assert not _green(result), result.stdout
    assert "counts: reported 6 of 6 collected" not in result.stdout
    assert "EXIT GATE RED" in result.stdout, result.stdout


def test_regression_m_after_a_path_named_python_is_still_a_filter(tmp_path: Path) -> None:
    """D4 (configured). `-m` belongs to the interpreter only when the previous
    token IS the interpreter; `tests/python_api` is a path, not a program."""
    probe = _full(tmp_path, _conf(
        ['tests|pytest tests/python_api -m "not slow"', "lint|echo STEP-RAN"]))

    result = _run(probe)

    assert result.returncode == 2, result.stdout + result.stderr
    assert any(ln.startswith('BANNED: -m "not slow" — undeclared filter')
               for ln in result.stdout.splitlines()), result.stdout
    assert "STEP-RAN" not in result.stdout


def test_regression_m_after_a_path_named_python_is_refused_at_runtime(tmp_path: Path) -> None:
    """D4 (runtime). Arguments typed at verify-fast.sh are never waived."""
    probe = _fast(tmp_path, "LINT=(echo STEP-RAN)\nTEST=(echo STEP-RAN)\n")

    result = _run(probe, "tests/python_api", "-m", "not slow")

    assert result.returncode == 2, result.stdout + result.stderr
    assert any(ln.startswith("BANNED: -m — ") for ln in result.stdout.splitlines()), result.stdout
    assert "STEP-RAN" not in result.stdout


def test_regression_an_empty_step_list_is_red_not_vacuously_green(tmp_path: Path) -> None:
    """D5. `STEPS=()` runs nothing. bash 3.2 dies on an unbound variable with no
    banner; bash >= 4.4 reaches finalize, which returns VERDICT=GREEN."""
    probe = _full(tmp_path, "STEPS=()\n")

    result = _run(probe)

    assert result.returncode == 1, result.stdout + result.stderr
    assert "EXIT GATE RED" in result.stdout, result.stdout + result.stderr


def test_regression_junit_written_outside_the_run_dir_is_not_counted(tmp_path: Path) -> None:
    """Positive control (passes today): a report written anywhere but this run's
    fresh $VERIFY_JUNIT_DIR does not count."""
    (tmp_path / ".gitignore").write_text("reports/\n", encoding="utf-8")
    probe = _full(tmp_path, _conf(
        ["tests|VERIFY_JUNIT_DIR=reports python3 scripts/stub_junit.py 3 0 0"], collect="echo 3"))

    result = _run(probe)

    assert result.returncode == 1, result.stdout
    assert "no JUnit report written by step tests" in result.stdout.splitlines()
    assert _last(result).startswith("record: ")


# ---------------------------------------------------------------------------
# Re-test 1 (after commit 1785567). Defects D12-D16, D18 of the QA report.
# The static pins call the recorder's `check-banned` directly: what is under
# test is how a command is scanned, and no go/bazel/cargo binary is needed.
# ---------------------------------------------------------------------------

import os  # noqa: E402

import pytest  # noqa: E402

from test_verify_scripts import _FULL, _copy  # noqa: E402
from test_verify_tiers import _STUB_PERMANENT, _env, _init_repo, _write_stub  # noqa: E402

_RECORDER = Path(__file__).resolve().parents[2] / "scripts" / "verify_record.py"


def _check_banned(command: str) -> subprocess.CompletedProcess[str]:
    """`check-banned` on one configured command, with no runner options set in the
    environment (the recorder scans PYTEST_ADDOPTS / JEST_* too)."""
    env = {k: v for k, v in _env().items()
           if k != "PYTEST_ADDOPTS" and not k.startswith("JEST_")}
    return subprocess.run(
        ["python3", str(_RECORDER), "check-banned", "--cmd=" + command],
        capture_output=True, text=True, timeout=60, check=False, env=env,
    )


def _banned_lines(result: subprocess.CompletedProcess[str]) -> list[str]:
    return [ln for ln in result.stdout.splitlines() if ln.startswith("BANNED:")]


def test_regression_a_go_project_with_no_conf_is_not_refused_for_go_test_timeout(
    tmp_path: Path,
) -> None:
    """D12 (R12, AC-AC15). Go flags are single-dash long options; the cluster walk
    reads `-timeout` as `-t -i -m eout`, a marker filter. A project as filled in
    today, with no conf, must not be refused for an ordinary `go test` line."""
    probe = _copy(tmp_path, _FULL, *_STUB_PERMANENT,
                  ('"tests|echo TODO: set the full test command"',
                   '"tests|go test -timeout 5m ./..."'))
    _write_stub(tmp_path)
    _init_repo(tmp_path)

    result = _run(probe)

    assert _banned_lines(result) == [], result.stdout
    assert result.returncode != 2, result.stdout + result.stderr


@pytest.mark.parametrize("command", [
    "go test -mod=vendor ./...",
    "go test -memprofile mem.out ./...",
    "go test -exec sudo ./...",
])
def test_regression_go_single_dash_long_flags_are_not_read_as_short_clusters(
    command: str,
) -> None:
    """D12. Each of these was passed by cb76109 and is refused by 1785567."""
    result = _check_banned(command)

    assert _banned_lines(result) == [], result.stdout
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(("command", "token"), [
    ("python3 -mpytest --reruns 2", "--reruns"),
    ("python3 -mpytest --lf", "--lf"),
])
def test_regression_an_attached_interpreter_m_still_finds_the_runner(
    command: str, token: str,
) -> None:
    """D13 (AC-AC8). `-mpytest` is the attached spelling of `-m pytest`: the
    runner's argv after it must be scanned."""
    result = _check_banned(command)

    assert result.returncode == 2, result.stdout + result.stderr
    assert any(ln.startswith("BANNED: %s — " % token) for ln in _banned_lines(result)), (
        result.stdout)


# test_regression_a_design_listed_ban_is_refused_in_the_tool_it_belongs_to: retired by doc/specs/SPEC-verify-tiers-merge-gate-am2-scanner-scope.md (D14 is a declared limit).


def test_regression_a_path_argument_named_like_a_runner_is_not_a_runner() -> None:
    """D15 (ruling D6: bans apply to test-runner argv only). `tools/jest` is a
    directory given to make, not jest; make's `-k` is keep-going."""
    result = _check_banned("make -C tools/jest -k")

    assert _banned_lines(result) == [], result.stdout
    assert result.returncode == 0, result.stdout + result.stderr


def test_regression_a_test_step_with_no_recognised_runner_says_it_was_not_scanned(
    tmp_path: Path,
) -> None:
    """D16 (R4 honesty). A listed test step that runs no VERIFY_TEST_RUNNERS entry
    (here a stub standing in for `tox -- --reruns 2`) is not ban-scanned. Like the
    eval / sh -c case, the run must say so on a `limit:` line naming the step.
    Reruns do not change the case count, so the count check cannot catch it."""
    probe = _full(tmp_path, _conf(
        ["tests|python3 scripts/stub_junit.py 3 0 0 --reruns=2"], collect="echo 3"))

    result = _run(probe)

    assert any(ln.startswith("limit:") and "tests" in ln
               for ln in result.stdout.splitlines()), result.stdout


def test_regression_a_conf_whose_last_test_is_false_still_loads(tmp_path: Path) -> None:
    """D18. `[ -n "$X" ] && VAR=…` as the conf's last line returns 1 when X is
    unset. The conf loaded completely; "failed to load" names the wrong reason."""
    probe = _full(tmp_path, _conf(
        ["tests|python3 scripts/stub_junit.py 3 0 0"], collect="echo 3",
        extra='[ -n "${QA_NEVER_SET_FLAG:-}" ] && VERIFY_STEP_BUDGET_S=600\n'))
    assert "QA_NEVER_SET_FLAG" not in os.environ

    result = _run(probe)

    assert "failed to load" not in result.stdout, result.stdout
    assert result.returncode == 0, result.stdout + result.stderr
    assert "EXIT GATE GREEN" in result.stdout
