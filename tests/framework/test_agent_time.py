"""Tests for `scripts/agent_time.py` — the neutral agent-time meter (R37, R39, R40, R32).

WHY THIS FILE EXISTS. The meter's first hand-run measurement counted adapter
internal events as activity, and idle time came out 7 minutes wrong without
any error (PRD brief). A meter that is quietly wrong is worse than no meter, so
every total here is checked against a golden timeline whose answer is known
(DESIGN-verify-tiers-merge-gate.md §J.4), and every mutation the meter must
resist is planted on purpose and shown to be caught.

These tests use a neutral stub reader (`fixtures/agent_time/neutral_reader.py`)
so they pass in any project made from this template, whatever its assistant.

Run: `python3 -m pytest tests/framework/test_agent_time.py -q`   (stdlib only)
"""

from __future__ import annotations

import datetime as dt
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "scripts"))
import agent_time  # noqa: E402  (path must be set up first)

_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "agent_time"
_STUB_READER = _FIXTURES / "neutral_reader.py"
_SCRIPT = _REPO_ROOT / "scripts" / "agent_time.py"

#: The golden totals in seconds (SPEC-verify-tiers-merge-gate.md, Increment 1).
GOLDEN = {
    "model": 150,
    "tests": 361,
    "tests:running": 120,
    "tests:bg-launch": 1,
    "tests:bg-wait": 120,
    "tests:polling": 120,
    "waits": 0,
    "waits:bg-wait": 0,
    "waits:polling": 0,
    "waits:other": 0,
    "other tools": 60,
    "read/git/edit": 7,
    "polling": 120,
    "idle": 600,
    "active": 578,
    "turns": 9,
}


def _fmt(value: object) -> str:
    return f"{value:g}" if isinstance(value, (int, float)) else str(value)


def assert_totals(actual: dict, expected: dict) -> None:
    """Fail naming every differing total as `<name> <expected> → <actual>`."""
    diffs = [
        f"{key} {_fmt(expected[key])} → {_fmt(actual.get(key, 'missing'))}"
        for key in expected
        if actual.get(key) != expected[key]
    ]
    assert not diffs, "totals differ from golden: " + ", ".join(diffs)


def _golden_run() -> agent_time.Run:
    stub = agent_time.load_reader(_STUB_READER)
    return stub.run_from_dict(json.loads((_FIXTURES / "golden_run.json").read_text("utf-8")))


def _meter(*args: str, cwd: Path = _REPO_ROOT) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(_SCRIPT), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def _neutral_run(path: Path, agent_type: str, events: list, t0: str = "2026-10-20T00:00:00+00:00") -> None:
    path.write_text(json.dumps({"agent_type": agent_type, "t0": t0, "events": events}), "utf-8")


# ---- J-AC1 / J-AC4: the golden timeline ------------------------------------


def test_golden_timeline_gives_exactly_the_golden_totals() -> None:
    """J-AC1: every category, sub-line, idle, active and turns, in seconds."""
    totals = agent_time.categorise(_golden_run())
    assert_totals(totals, GOLDEN)


def test_polling_is_reported_on_its_own_line_but_not_added_to_active_twice() -> None:
    """J-AC1: the polling line repeats time already inside tests or waits."""
    totals = agent_time.categorise(_golden_run())
    parts = sum(totals[c] for c in agent_time.CATEGORIES)
    assert totals["active"] == parts == 578
    assert totals["polling"] == totals["tests:polling"] + totals["waits:polling"] == 120


def test_counting_each_model_event_as_a_turn_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """J-AC4 (RED-FIRST mutation): one response spans two model events (m1).

    Swapping the distinct-id counter for a per-event counter must make the
    golden check fail, naming `turns 9 → 10`.
    """
    monkeypatch.setattr(
        agent_time, "count_turns", lambda events: sum(1 for e in events if e.kind == "model")
    )
    totals = agent_time.categorise(_golden_run())
    with pytest.raises(AssertionError) as caught:
        assert_totals(totals, GOLDEN)
    assert "turns 9 → 10" in str(caught.value)


def test_a_project_test_pattern_extends_the_test_category() -> None:
    """`--test-pattern` (design §J.5): a project's own test command counts as tests."""
    run = _golden_run()
    custom = re.compile(agent_time.TEST_RE.pattern + "|make docs")
    totals = agent_time.categorise(run, test_re=custom)
    assert totals["other tools"] == 0
    assert totals["tests:running"] == 180


# ---- J-AC5: no reader means "unsupported", never a silent zero --------------


@pytest.mark.parametrize("reader_args", [[], ["--reader", "no/such/reader.py"]])
def test_no_reader_prints_unsupported_and_no_durations(tmp_path: Path, reader_args: list) -> None:
    result = _meter(*reader_args, "--dir", str(tmp_path))
    assert result.returncode == 0
    assert "unsupported" in result.stdout
    assert not re.search(r"\bmin\b|%", result.stdout), result.stdout


# ---- J-AC7: missing directory, unreadable input, a run with no events -------


def test_missing_directory_is_said_not_measured(tmp_path: Path) -> None:
    for dir_args in ([], ["--dir", str(tmp_path / "absent")]):
        result = _meter("--reader", str(_STUB_READER), *dir_args)
        assert result.returncode == 0
        assert "transcript directory not found" in result.stdout
        assert not re.search(r"\bmin\b|%", result.stdout), result.stdout


def test_a_run_with_no_events_reports_nothing_measured(tmp_path: Path) -> None:
    _neutral_run(tmp_path / "empty.json", "ai-engineer", [])
    result = _meter("--reader", str(_STUB_READER), "--dir", str(tmp_path), "--since", "2000-01-01")
    assert result.returncode == 0
    assert "runs with no clock events: 1" in result.stdout
    assert "no runs with clock events in the window" in result.stdout
    assert not re.search(r"\bmin\b|%", result.stdout), result.stdout


def test_unreadable_input_is_counted_not_hidden(tmp_path: Path) -> None:
    shutil.copy(_FIXTURES / "golden_run.json", tmp_path / "golden.json")
    (tmp_path / "broken.json").write_text("{not json", "utf-8")
    result = _meter("--reader", str(_STUB_READER), "--dir", str(tmp_path), "--since", "2000-01-01")
    assert result.returncode == 0
    assert "unreadable lines: 1" in result.stdout


# ---- J-AC8: medians, shares, method and limits ------------------------------


def _three_runs(tmp_path: Path) -> None:
    # active = model + tests + model: 100 s, 200 s, 600 s.
    for name, (a, b, c) in {"r1": (30, 40, 30), "r2": (50, 100, 50), "r3": (200, 300, 100)}.items():
        _neutral_run(
            tmp_path / f"{name}.json",
            "ai-engineer",
            [
                {"t": 0, "kind": "inbound", "text": "brief"},
                {"t": a, "kind": "model", "message_id": "m1"},
                {"t": a, "kind": "tool_call", "tool_id": "T1", "tool_kind": "shell", "command": "pytest"},
                {"t": a + b, "kind": "tool_result", "tool_id": "T1"},
                {"t": a + b + c, "kind": "model", "message_id": "m2"},
            ],
        )


def test_report_shows_the_median_and_shares_that_sum_to_100(tmp_path: Path) -> None:
    _three_runs(tmp_path)
    result = _meter("--reader", str(_STUB_READER), "--dir", str(tmp_path), "--since", "2000-01-01")
    assert result.returncode == 0
    out = result.stdout
    assert "ai-engineer: 3 runs · active median 3.3 min · turns median 2" in out
    shares = [int(s) for s in re.findall(r"min/run\s+(\d+)%", out)]
    assert len(shares) == len(agent_time.CATEGORIES)
    assert abs(sum(shares) - 100) <= 1, shares
    assert re.search(r"^method: \S", out, re.M)
    assert re.search(r"^limits: \S", out, re.M)


def test_since_keeps_only_runs_whose_last_event_is_in_the_window(tmp_path: Path) -> None:
    _three_runs(tmp_path)
    _neutral_run(
        tmp_path / "old.json",
        "ai-engineer",
        [{"t": 0, "kind": "inbound"}, {"t": 10, "kind": "model", "message_id": "m"}],
        t0="2020-01-01T00:00:00+00:00",
    )
    result = _meter("--reader", str(_STUB_READER), "--dir", str(tmp_path), "--since", "2026-01-01")
    assert "ai-engineer: 3 runs" in result.stdout


# ---- J-AC9: rework share and rework causes -----------------------------------


def _engineer_runs(tmp_path: Path, rework_runs: int, total: int) -> None:
    for i in range(total):
        brief = "REWORK: doc/qa/QA-x.md\nFix defect 1." if i < rework_runs else "Slice: 1"
        _neutral_run(
            tmp_path / f"e{i}.json",
            "ai-engineer",
            [{"t": 0, "kind": "inbound", "text": brief}, {"t": 10, "kind": "model", "message_id": "m"}],
        )


def test_rework_share_and_causes_are_counted(tmp_path: Path) -> None:
    _engineer_runs(tmp_path, rework_runs=1, total=4)
    result = _meter(
        "--reader", str(_STUB_READER), "--dir", str(tmp_path), "--since", "2026-10-01",
        "--rework", "--qa-dir", str(_FIXTURES / "qa"),
    )
    assert result.returncode == 0
    out = result.stdout
    assert "rework share: 1 of 4 engineer runs (25%)" in out
    assert "missed-ac 2 · regression 0 · spec-defect 0 · test-gap 1 · env-flaky 0" in out
    assert "unclassified defects: 1" in out


def test_rework_marker_must_start_a_line(tmp_path: Path) -> None:
    _neutral_run(
        tmp_path / "e.json",
        "ai-engineer",
        [{"t": 0, "kind": "inbound", "text": "this is not REWORK: a marker"},
         {"t": 10, "kind": "model", "message_id": "m"}],
    )
    result = _meter("--reader", str(_STUB_READER), "--dir", str(tmp_path), "--rework")
    assert "rework share: 0 of 1 engineer runs (0%) — unmarked" in result.stdout
    assert "rework causes: not read (pass --qa-dir)" in result.stdout


def test_rework_with_no_engineer_runs_is_not_a_zero_percent(tmp_path: Path) -> None:
    _neutral_run(tmp_path / "q.json", "qa", [{"t": 0, "kind": "inbound"}, {"t": 5, "kind": "model", "message_id": "m"}])
    result = _meter(
        "--reader", str(_STUB_READER), "--dir", str(tmp_path), "--rework", "--qa-dir", str(tmp_path / "nope"),
    )
    assert "rework share: no engineer runs in the window" in result.stdout
    assert "rework causes: QA directory not found (--qa-dir)" in result.stdout


def test_qa_reports_before_the_window_are_not_counted(tmp_path: Path) -> None:
    _engineer_runs(tmp_path, rework_runs=0, total=1)
    result = _meter(
        "--reader", str(_STUB_READER), "--dir", str(tmp_path), "--since", "2026-10-19",
        "--rework", "--qa-dir", str(_FIXTURES / "qa"),
    )
    # Only QA-beta (2026-10-19) is in the window: one missed-ac, one invalid cause.
    assert "missed-ac 1 · regression 0 · spec-defect 0 · test-gap 0 · env-flaky 0" in result.stdout
    assert "unclassified defects: 1" in result.stdout


def test_the_rework_vocabulary_is_the_one_the_spec_fixes() -> None:
    assert agent_time.REWORK_CAUSES == ("missed-ac", "regression", "spec-defect", "test-gap", "env-flaky")


# ---- J-AC11 companion: the core names no assistant -----------------------------


def test_the_core_never_names_an_adapter_folder() -> None:
    """Design §0: the core must never contain the adapter's folder name."""
    assert "." + "claude" not in _SCRIPT.read_text("utf-8").lower()


@pytest.mark.parametrize("bad_args", [["--since", "2026/10/01"], ["--test-pattern", "("], ["--no-such-flag"]])
def test_a_malformed_argument_prints_an_error_line_and_exits_0(tmp_path: Path, bad_args: list) -> None:
    """R39 / design §J.2: the meter always exits 0, even on a usage error, and says why."""
    result = _meter("--reader", str(_STUB_READER), "--dir", str(tmp_path), *bad_args)
    assert result.returncode == 0
    assert re.search(r"^agent-time: error: .*(invalid|unrecognized)", result.stdout, re.M), result.stdout
    assert "Traceback" not in result.stderr
    assert not re.search(r"\bmin\b|%", result.stdout)


def test_an_unexpected_exception_reports_its_type_only_and_exits_0(tmp_path: Path) -> None:
    """The top-level guard: a reader that raises must not leak a traceback, a path or an exit 1.

    The planted exception's message carries a canary path; only the type may be printed.
    """
    raising = tmp_path / "raising_reader.py"
    raising.write_text(
        "def runs(source, since):\n"
        "    raise RuntimeError('/home/someone/CANARY-7f3a/agent.jsonl')\n",
        "utf-8",
    )
    result = _meter("--reader", str(raising), "--dir", str(tmp_path))
    assert result.returncode == 0
    assert result.stdout.strip() == "agent-time: internal error: RuntimeError"
    assert "Traceback" not in result.stderr
    assert "CANARY-7f3a" not in result.stdout + result.stderr


def test_qa_reports_that_cannot_be_read_are_counted(tmp_path: Path) -> None:
    """A report with no Date:, or a FAIL with no Defects table, must not read as 'no defects'."""
    qa = tmp_path / "qa"
    qa.mkdir()
    (qa / "QA-undated.md").write_text("# QA\n\n## Verdict: FAIL\n", "utf-8")
    (qa / "QA-notable.md").write_text("# QA\n\nDate: 2026-10-19\n\n## Verdict: FAIL\n\nNo table.\n", "utf-8")
    _engineer_runs(tmp_path, rework_runs=0, total=1)
    result = _meter(
        "--reader", str(_STUB_READER), "--dir", str(tmp_path), "--rework", "--qa-dir", str(qa),
    )
    assert "QA reports not read: 2 (no Date: 1 · FAIL with no Defects table: 1)" in result.stdout


def test_parse_since_is_a_utc_midnight() -> None:
    assert agent_time.parse_since("2026-10-20") == dt.datetime(2026, 10, 20, tzinfo=dt.timezone.utc)


# ---- R39 second defence: the core prints only single-line labels ------------------


def test_the_core_never_prints_a_label_that_is_not_a_single_line() -> None:
    """Whatever a reader hands it, a role or excluded type with a line break is not printed.

    The adapter's reader already cleans its labels (QA D5); this is the core's own
    check, for readers that do not.
    """
    t0 = dt.datetime(2026, 10, 20, tzinfo=dt.timezone.utc)
    events = [agent_time.Event(t0, "inbound"), agent_time.Event(t0 + dt.timedelta(seconds=5), "model", message_id="m")]
    forged = "rework share: 0 of 9 engineer runs (0%)"
    runs = [
        agent_time.Run(f"qa\n{forged}", events, agent_time.Counter({f"x\n{forged}": 1, "attachment": 2})),
        agent_time.Run({"k": "CANARY-7f3a"}, events),
        agent_time.Run("qa", events, agent_time.Counter({"user (no timestamp)": 1})),
    ]
    text = agent_time.report(runs, t0, "stub")
    assert not [line for line in text.splitlines() if line.startswith(forged)], text
    assert "CANARY-7f3a" not in text
    assert "(unprintable label) 1" in text and "attachment 2" in text and "user (no timestamp) 1" in text, text
    assert "(unprintable label): 2 runs" in text and "qa: 1 runs" in text, text
