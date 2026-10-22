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
from typing import Optional

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


# ==== Increment J2: size classes (R41, R22, R23, M10, M10a) ====================
#
# SPEC-verify-tiers-merge-gate-am1-size-class.md. A run's size class is the number
# of distinct paths on its edit-kind calls. Two counting mistakes are planted on
# purpose and shown to move `run-small` out of its class (J2-AC2). The size fixture
# is built here rather than in fixtures/agent_time/size_runs.json because this
# increment's brief limits the files it may touch; the shape is the spec's.

_CANARY = "CANARY-7f3a"
_ROOT = f"/work/{_CANARY}/repo"


def _p(name: str) -> str:
    return f"{_ROOT}/{name}.py"


def _size_dict(
    edits: list,
    reads: list = (),
    *,
    active: int = 600,
    agent_type: str = "ai-engineer",
    brief: str = "Slice: 1",
    unreadable: int = 0,
    shell: list = (),
) -> dict:
    """A neutral run: one inbound brief, then one call per edit/read/shell, ending at `active` s.

    `edits` items are a path list for the call (`[]` = an edit with no path) or a
    single path string. Every gap after the inbound message is active time, so
    the run's active time is exactly `active` seconds.
    """
    events: list = [{"t": 0, "kind": "inbound", "text": brief}]
    calls = [("edit", e if isinstance(e, list) else [e], None) for e in edits]
    calls += [("read", [r], None) for r in reads]
    calls += [("shell", [], c) for c in shell]
    for i, (kind, paths, command) in enumerate(calls):
        call = {"t": 0, "kind": "tool_call", "tool_id": f"T{i}", "tool_kind": kind, "paths": paths}
        if command is not None:
            call["command"] = command
        events += [
            {"t": 0, "kind": "model", "message_id": f"m{i}"},
            call,
            {"t": 0, "kind": "tool_result", "tool_id": f"T{i}"},
        ]
    events.append({"t": active, "kind": "model", "message_id": "end"})
    return {
        "agent_type": agent_type,
        "t0": "2026-10-20T00:00:00+00:00",
        "events": events,
        "unreadable_lines": unreadable,
    }


#: `run-small`: 5 distinct files edited through 8 calls (a, b, c twice), 6 other
#: files read, and a and b read too.
RUN_SMALL = _size_dict(
    [_p(x) for x in "abcdeabc"],
    [_p(x) for x in "fghijkab"],
)


def _run(data: dict) -> agent_time.Run:
    return agent_time.load_reader(_STUB_READER).run_from_dict(data)


def _files(n: int) -> list:
    return [_p(f"f{i}") for i in range(n)]


def assert_size(actual: tuple, expected: tuple) -> None:
    """Fail naming `<expected class> → <actual class> (<count>)`."""
    assert actual == expected, f"size class differs: {expected[0]} → {actual[0]} ({actual[1]})"


def _write_runs(tmp_path: Path, runs: dict) -> None:
    for name, data in runs.items():
        (tmp_path / f"{name}.json").write_text(json.dumps(data), "utf-8")


def _size_meter(tmp_path: Path, *extra: str) -> str:
    result = _meter("--reader", str(_STUB_READER), "--dir", str(tmp_path), "--since", "2000-01-01", *extra)
    assert result.returncode == 0
    assert "Traceback" not in result.stderr and "internal error" not in result.stdout, result.stdout
    return result.stdout


# ---- J2-AC1: the class of a run ------------------------------------------------


def test_run_small_is_small_with_five_files() -> None:
    assert_size(agent_time.size_class(_run(RUN_SMALL)), ("small", 5))


@pytest.mark.parametrize(
    ("n", "expected"),
    [(0, "investigate-only"), (1, "small"), (5, "small"), (6, "medium"), (10, "medium"), (11, "large")],
)
def test_class_boundaries_are_inclusive(n: int, expected: str) -> None:
    assert_size(agent_time.size_class(_run(_size_dict(_files(n), _files(3)))), (expected, n))


# ---- J2-AC2: the two counting mistakes are caught (RED-FIRST mutations) -----------


def test_counting_each_edit_call_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """Planted mistake 1: a per-call counter instead of distinct paths."""
    monkeypatch.setattr(
        agent_time,
        "count_edited_files",
        lambda events: sum(1 for e in events if e.kind == "tool_call" and e.tool_kind in agent_time.SIZE_TOOL_KINDS),
    )
    with pytest.raises(AssertionError) as caught:
        assert_size(agent_time.size_class(_run(RUN_SMALL)), ("small", 5))
    assert "small → medium (8)" in str(caught.value)


def test_counting_read_only_files_is_caught(monkeypatch: pytest.MonkeyPatch) -> None:
    """Planted mistake 2: read-kind calls admitted to the counted set."""
    monkeypatch.setattr(agent_time, "SIZE_TOOL_KINDS", agent_time.SIZE_TOOL_KINDS | {"read"})
    with pytest.raises(AssertionError) as caught:
        assert_size(agent_time.size_class(_run(RUN_SMALL)), ("small", 5))
    assert "small → large (11)" in str(caught.value)


def test_the_counted_kinds_are_exactly_edit() -> None:
    assert agent_time.SIZE_TOOL_KINDS == frozenset({"edit"})


# ---- J2-AC3 / J2-AC4: size unknown ------------------------------------------------


@pytest.mark.parametrize(
    "bad_paths",
    [[], [""], [None], [7], [["a"]], [{"k": _CANARY}], [_p("a"), ""], "MISSING"],
    ids=["empty", "empty-string", "none", "int", "list", "dict", "one-good-one-empty", "no-paths-field"],
)
def test_an_edit_with_no_usable_path_makes_the_run_size_unknown(bad_paths) -> None:
    data = _size_dict([_p("a"), _p("b")])
    call = next(e for e in data["events"] if e["kind"] == "tool_call")
    if bad_paths == "MISSING":
        del call["paths"]
    else:
        call["paths"] = bad_paths
    assert agent_time.size_class(_run(data)) == ("size unknown", None)


@pytest.mark.parametrize("paths", [7, None, "a-string-not-a-tuple"])
def test_a_paths_field_that_is_not_a_sequence_is_size_unknown_not_a_crash(paths) -> None:
    t0 = dt.datetime(2026, 10, 20, tzinfo=dt.timezone.utc)
    run = agent_time.Run(
        "ai-engineer",
        [agent_time.Event(t0, "inbound"), agent_time.Event(t0, "tool_call", tool_id="T", tool_kind="edit", paths=paths)],
    )
    assert agent_time.size_class(run) == ("size unknown", None)


def test_an_unreadable_line_makes_the_run_size_unknown() -> None:
    assert agent_time.size_class(_run(_size_dict([_p("a")], unreadable=1))) == ("size unknown", None)


def test_size_unknown_runs_are_in_no_class_but_in_the_overall_numbers(tmp_path: Path) -> None:
    """J2-AC3 and J2-AC4: each unknown run is counted under exactly one reason.

    A run with both a pathless edit and an unreadable line is counted under
    `path missing`, so the two reasons always add up to the unknown count.
    """
    _write_runs(
        tmp_path,
        {
            "known": _size_dict([_p("a")], active=600),
            "pathless": _size_dict([[]], active=900),
            "unreadable": _size_dict([_p("a")], active=1200, unreadable=1),
            "both": _size_dict([[]], active=1500, unreadable=2),
        },
    )
    out = _size_meter(tmp_path)
    assert "small  n=1  median 10.0 min" in out, out
    assert "size unknown n=3" in out
    assert "size unknown: 3 (path missing: 2 · unreadable lines: 1)" in out
    assert "all engineer runs n=4  mean 17.5 min · median 17.5 min" in out


# ---- J2-AC5: per-class lines and the overall line --------------------------------


def _ac5_runs() -> dict:
    return {
        "s1": _size_dict(_files(1), active=600),
        "s2": _size_dict(_files(3), active=900),
        "s3": _size_dict(_files(5), active=1200),
        "m1": _size_dict(_files(7), active=2400),
        "u1": _size_dict([[]], active=300),
    }


def test_the_report_gives_each_class_its_count_and_median(tmp_path: Path) -> None:
    _write_runs(tmp_path, _ac5_runs())
    out = _size_meter(tmp_path)
    assert "investigate-only n=0  no median" in out, out
    assert "small  n=3  median 15.0 min" in out
    assert "medium n=1  median 40.0 min" in out
    assert "large  n=0  no median" in out
    assert "size unknown n=1" in out
    # mean (600+900+1200+2400+300)/5 = 1080 s = 18.0 min; median 900 s.
    assert "all engineer runs n=5  mean 18.0 min · median 15.0 min" in out
    assert not re.search(r"large .*0\.0", out)
    assert "acceptance" not in out, "no --targets, so nothing is judged"


def test_size_classes_are_reported_per_engineer_type_and_only_for_engineers(tmp_path: Path) -> None:
    runs = _ac5_runs()
    runs["fe"] = _size_dict(_files(12), active=60, agent_type="frontend-engineer")
    runs["qa"] = _size_dict(_files(12), active=60, agent_type="qa")
    _write_runs(tmp_path, runs)
    out = _size_meter(tmp_path)
    assert "all engineer runs n=5" in out and "all engineer runs n=1" in out
    assert "large  n=1  median 1.0 min" in out
    assert out.count("all engineer runs") == 2, "the qa run must not get a size block"


def test_no_engineer_runs_says_so(tmp_path: Path) -> None:
    _write_runs(tmp_path, {"qa": _size_dict(_files(2), agent_type="qa")})
    assert "size classes: no engineer runs in the window" in _size_meter(tmp_path)


# ---- J2-AC6: per-class acceptance ----------------------------------------------------


def test_acceptance_is_judged_per_class_and_the_meter_still_exits_0(tmp_path: Path) -> None:
    _write_runs(tmp_path, _ac5_runs())
    out = _size_meter(tmp_path, "--targets", "small=15,medium=25,large=50", "--min-runs", "3")
    assert "small  n=3  median 15.0 min · met (median 15.0 ≤ 15)" in out, out
    assert "medium n=1  median 40.0 min · not enough runs (1) — extend the trial for this class; not met" in out
    assert "large  n=0  no median · not enough runs (0) — extend the trial for this class; not met" in out
    assert "investigate-only n=0  no median · report only" in out
    assert "acceptance: NOT met (met 1 of 3 classes)" in out


def test_min_runs_defaults_to_3(tmp_path: Path) -> None:
    _write_runs(tmp_path, _ac5_runs())
    out = _size_meter(tmp_path, "--targets", "small=15,medium=25,large=50")
    assert "small  n=3  median 15.0 min · met" in out and "not enough runs (1)" in out, out


def test_a_median_above_its_target_is_not_met(tmp_path: Path) -> None:
    _write_runs(tmp_path, _ac5_runs())
    out = _size_meter(tmp_path, "--targets", "small=14,medium=25,large=50", "--min-runs", "1")
    assert "small  n=3  median 15.0 min · NOT met (median 15.0 > 14)" in out, out
    assert "medium n=1  median 40.0 min · NOT met (median 40.0 > 25)" in out
    assert "acceptance: NOT met (met 0 of 3 classes)" in out


def test_all_three_classes_met_is_accepted(tmp_path: Path) -> None:
    runs = {f"r{n}": _size_dict(_files(n), active=60) for n in (1, 7, 12)}
    _write_runs(tmp_path, runs)
    out = _size_meter(tmp_path, "--targets", "small=15,medium=25,large=50", "--min-runs", "1")
    assert "acceptance: met (met 3 of 3 classes)" in out, out


def test_the_verdict_agrees_with_the_printed_median(tmp_path: Path) -> None:
    """A median of 15.02 min prints as 15.0, so it must not say `NOT met (median 15.0 > 15)`."""
    _write_runs(tmp_path, {"r": _size_dict(_files(1), active=901)})
    out = _size_meter(tmp_path, "--targets", "small=15,medium=25,large=50", "--min-runs", "1")
    assert "met (median 15.0 ≤ 15)" in out, out


@pytest.mark.parametrize(
    "bad",
    [
        ["--targets", "small=abc,medium=25,large=50"],
        ["--targets", "tiny=5,small=15,medium=25,large=50"],
        ["--targets", "small=-1,medium=25,large=50"],
        ["--targets", "small=0,medium=25,large=50"],
        ["--targets", "small=nan,medium=25,large=50"],
        ["--targets", "small=inf,medium=25,large=50"],
        ["--targets", "small=15,medium=25"],
        ["--targets", "small=15,small=16,medium=25,large=50"],
        ["--targets", ""],
        ["--targets", "small=15,medium=25,large=50,"],
        ["--min-runs", "0"],
        ["--min-runs", "-2"],
        ["--min-runs", "x"],
    ],
)
def test_a_bad_target_or_min_runs_is_one_error_line_and_exit_0(tmp_path: Path, bad: list) -> None:
    _write_runs(tmp_path, _ac5_runs())
    result = _meter("--reader", str(_STUB_READER), "--dir", str(tmp_path), *bad)
    assert result.returncode == 0
    assert re.fullmatch(r"agent-time: error: [^\n]+\n", result.stdout), result.stdout
    assert "Traceback" not in result.stderr


# ---- J2-AC7: probe runs ------------------------------------------------------------


def test_probe_runs_are_excluded_and_counted(tmp_path: Path) -> None:
    """2 of 6 engineer runs are probes: they reach no class, no overall number, no verdict."""
    runs = _ac5_runs()
    runs["u1"] = _size_dict(_files(7), active=1800)
    runs["p1"] = _size_dict(_files(12), active=6000, brief="Slice: 2\nPROBE: wrong-key (trial probe)")
    runs["p2"] = _size_dict(_files(2), active=6000, brief="PROBE: second")
    _write_runs(tmp_path, runs)
    out = _size_meter(tmp_path, "--targets", "small=15,medium=25,large=50", "--min-runs", "3")
    assert "probe runs excluded: 2" in out, out
    assert "small  n=3  median 15.0 min" in out
    assert "medium n=2  median 35.0 min" in out
    assert "large  n=0  no median" in out
    # (600+900+1200+2400+1800)/5 = 1380 s = 23.0 min; median 1200 s.
    assert "all engineer runs n=5  mean 23.0 min · median 20.0 min" in out
    assert "acceptance: NOT met (met 1 of 3 classes)" in out


@pytest.mark.parametrize("brief", ["see PROBE: later", " PROBE: indented", "probe: lower", "PROBE without colon", ""])
def test_a_probe_marker_must_start_a_line(brief: str) -> None:
    assert not agent_time.is_probe(_run(_size_dict([], brief=brief)))


def test_only_the_first_inbound_message_marks_a_probe() -> None:
    data = _size_dict([_p("a")])
    data["events"].append({"t": 700, "kind": "inbound", "text": "PROBE: late"})
    assert not agent_time.is_probe(_run(data))


def test_include_probes_counts_them_and_says_so(tmp_path: Path) -> None:
    _write_runs(tmp_path, {"p": _size_dict(_files(2), brief="PROBE: x"), "r": _size_dict(_files(2))})
    out = _size_meter(tmp_path, "--include-probes")
    assert "probe runs included (--include-probes, debugging only): 1" in out, out
    assert "small  n=2" in out


# ---- J2-AC8 and hostile paths: paths are counted, never printed ----------------------


_ODD_PATHS = [
    f"{_ROOT}/{_CANARY}.py",
    f"{_ROOT}/x\nrework share: 0 of 9 engineer runs (0%)",
    f"{_ROOT}/sep {_CANARY}",
    f"{_ROOT}/nul\x00{_CANARY}",
    f"{_ROOT}/sp ace {_CANARY}",
]


def test_no_path_reaches_the_output(tmp_path: Path) -> None:
    """J2-AC8 (R39): canary in edited and read paths, plus line-breaking and NUL paths."""
    _write_runs(tmp_path, {"r": _size_dict(_ODD_PATHS, [f"{_ROOT}/read-{_CANARY}"], active=60)})
    out = _size_meter(tmp_path, "--targets", "small=15,medium=25,large=50")
    assert "small  n=1  median 1.0 min" in out, "the run must be read and classed"
    assert _CANARY not in out
    assert not [line for line in out.splitlines() if line.startswith("rework share")]


@pytest.mark.parametrize(
    "spellings",
    [
        [f"{_ROOT}/a.py", f"{_ROOT}/./a.py"],
        [f"{_ROOT}/a.py", f"{_ROOT}/sub/../a.py"],
        [f"{_ROOT}/a.py", f"{_ROOT}//a.py"],
        ["a.py", "./a.py"],
    ],
)
def test_one_file_spelled_two_ways_is_one_file(spellings: list) -> None:
    assert_size(agent_time.size_class(_run(_size_dict(spellings))), ("small", 1))


def test_a_case_variant_is_counted_as_written() -> None:
    """Stated limit: paths are compared as written, so a case variant counts twice.

    Measured 2026-10-20 over 436 local engineer runs: no run edited one file under
    two case spellings, and folding case would merge distinct files on a
    case-sensitive file system.
    """
    assert_size(agent_time.size_class(_run(_size_dict([f"{_ROOT}/A.py", f"{_ROOT}/a.py"]))), ("small", 2))


def test_ten_thousand_edits_to_one_file_are_one_file() -> None:
    assert_size(agent_time.size_class(_run(_size_dict([_p("a")] * 10_000))), ("small", 1))


# ---- shell-written files: a visible gap, not a class input ---------------------------


@pytest.mark.parametrize(
    ("command", "writes"),
    [
        ("sed -i 's/a/b/' x.py", True),
        ("echo hi > out.txt", True),
        ("cat >> log.txt <<EOF", True),
        ("git apply fix.patch", True),
        ("pytest -q 2>&1 | tail -3", False),
        ("grep x y > /dev/null", False),
        ("make >> /dev/null 2>&1", False),
        ("git log a -> b", False),
        ("python3 -c 'x = {1 => 2}'", False),
        ("python3 -c 'print(3 >= 2)'", False),
        ("ls 2>/dev/null", False),
        ("python3 -m pytest tests -q", False),
    ],
)
def test_shell_file_writes_are_counted_by_pattern(tmp_path: Path, command: str, writes: bool) -> None:
    _write_runs(tmp_path, {"r": _size_dict([_p("a")], shell=[command])})
    out = _size_meter(tmp_path)
    assert f"runs with shell file writes (not counted in size): {int(writes)}" in out, out
    assert "small  n=1" in out, "a shell write never changes the class"


# ---- J2-AC10: the adapter table declares the size class -------------------------------
# Lives here, not in test_doc_contracts.py, because this increment's brief limits its files.


def _size_row(letter: str) -> str:
    text = (_REPO_ROOT / "doc" / "framework" / "ADAPTERS.md").read_text("utf-8")
    section = re.search(rf"^## {letter} — .*?(?=^---$)", text, re.M | re.S)
    assert section, f"no section for adapter {letter}"
    rows = [line for line in section.group(0).splitlines() if line.startswith("| R41 ")]
    assert len(rows) == 1, f"adapter {letter}: expected one R41 size-class row, found {len(rows)}"
    return rows[0]


def test_adapter_a_declares_the_size_class_supported() -> None:
    row = _size_row("ก")
    assert "meter size class (R41)" in row
    assert "unsupported" not in row
    assert "file_path" in row and "notebook_path" in row


def test_adapter_b_declares_the_size_class_unsupported() -> None:
    row = _size_row("ข")
    assert "meter size class (R41)" in row and "unsupported" in row


# ---- The scorecard (SPEC-jarvis-coordinator-inc2-scorecard.md, SC-AC*) ------------
#
# `--scorecard` prints M1–M7 for a window from the same reader events as the time
# report. It is a report, so the tests below hold it to three things: the counting
# rules the spec fixes (exchanges, distinct turn ends, the Tier line grammar, report
# slugs, brief field lines), no misleading zero on odd or empty input, and no
# transcript text in the output.

_SC_FIXTURE = _FIXTURES / "scorecard"
_SC_WINDOW = ("--since", "2026-10-20", "--until", "2026-10-21")
_T0 = "2026-10-20T10:00:00+00:00"


def _owner(t: int, text: str = "Please do it.") -> dict:
    return {"t": t, "kind": "inbound", "owner": True, "text": text}


def _reply(t: int, mid: object, text: str = "", end: bool = True) -> dict:
    return {"t": t, "kind": "model", "message_id": mid, "text": text, "turn_end": end}


def _result(t: int) -> dict:
    return {"t": t, "kind": "tool_result", "tool_id": "T"}


def _edit(t: int, *paths: str) -> dict:
    return {"t": t, "kind": "tool_call", "tool_id": f"E{t}", "tool_kind": "edit", "paths": list(paths)}


def _sc_meter(source: Path, memory_dir: Optional[Path], *extra: str) -> subprocess.CompletedProcess:
    args = ["--reader", str(_STUB_READER), "--dir", str(source), "--scorecard", *extra]
    if memory_dir is not None:
        args += ["--memory-dir", str(memory_dir)]
    return _meter(*args)


def _sc_lines(tmp_path: Path, runs: dict, *extra: str, t0: str = _T0) -> list:
    """Write neutral runs {name: (agent_type, events)} and return the scorecard's lines."""
    source = tmp_path / "runs"
    source.mkdir(exist_ok=True)
    for name, (agent_type, events) in runs.items():
        _neutral_run(source / f"{name}.json", agent_type, events, t0)
    memory = tmp_path / "memory"
    memory.mkdir(exist_ok=True)
    result = _sc_meter(source, memory, *(extra or _SC_WINDOW))
    assert result.returncode == 0
    assert result.stderr == ""
    return result.stdout.splitlines()


def _in_process(tmp_path: Path, runs: dict) -> list:
    """The scorecard in-process over neutral runs, so a monkeypatched helper takes effect."""
    stub = agent_time.load_reader(_STUB_READER)
    built = [
        stub.run_from_dict({"agent_type": agent_type, "t0": _T0, "events": events})
        for agent_type, events in runs.values()
    ]
    since, until = agent_time.parse_since("2026-10-20"), agent_time.parse_since("2026-10-21")
    return agent_time.scorecard(built, since, until, tmp_path, "neutral_reader.py").splitlines()


def _block(lines: list, prefix: str) -> list:
    """The lines of one metric: its header line plus the indented lines under it."""
    start = next(i for i, line in enumerate(lines) if line.startswith(prefix))
    end = next((i for i in range(start + 1, len(lines)) if not lines[i].startswith("  ")), len(lines))
    return lines[start:end]


# ---- SC-AC1: one block per metric, in order, and the scorecard runs alone ----


def test_the_scorecard_prints_m1_to_m7_and_the_owner_line_in_order(tmp_path: Path) -> None:
    result = _sc_meter(_SC_FIXTURE, tmp_path, *_SC_WINDOW)
    assert result.returncode == 0
    lines = result.stdout.splitlines()
    starts = [
        next(i for i, line in enumerate(lines) if line.startswith(prefix))
        for prefix in ("M1 ", "M2 ", "M3 ", "M4 ", "M5 ", "M6 ", "M7 ", "owner messages per day (UTC): ")
    ]
    assert starts == sorted(starts), lines
    assert lines[0].startswith("scorecard — window [2026-10-20T00:00:00Z, 2026-10-21T00:00:00Z)"), lines
    assert "M5 new-user setup time: not measured by this command (timed by hand, R12)" in lines
    assert "  tier 0: 1 exchanges · 1 extra · mean 1.00 · 0 with none" in lines, lines
    assert "  tier 1: no exchanges" in lines
    assert "  untiered: 1 exchanges · 0 extra · mean 0.00 · 1 with none" in lines
    assert "  alpha: review 1 · QA 1" in lines, lines
    assert "M6 role-agent briefs with a Tier: line and a Files: line: 1 of 2" in lines, lines
    assert "owner messages per day (UTC): 2026-10-20 2" in lines
    # Nothing from the time report.
    assert not any(line.startswith(("agent-time —", "size classes", "probe runs", "rework share")) for line in lines)
    assert any(line.startswith("method: ") for line in lines) and any(line.startswith("limits: ") for line in lines)


@pytest.mark.parametrize(
    "other",
    [["--rework"], ["--targets", "small=15,medium=25,large=50"], ["--min-runs", "3"], ["--include-probes"]],
)
def test_the_scorecard_runs_alone(tmp_path: Path, other: list) -> None:
    result = _sc_meter(_SC_FIXTURE, tmp_path, *other)
    assert result.returncode == 0
    assert result.stdout == "agent-time: error: --scorecard runs alone\n"


def test_until_needs_the_scorecard(tmp_path: Path) -> None:
    result = _meter("--reader", str(_STUB_READER), "--dir", str(_SC_FIXTURE), "--until", "2026-10-21")
    assert result.returncode == 0
    assert result.stdout == "agent-time: error: --until needs --scorecard\n"


def test_an_empty_directory_prints_no_for_every_metric_never_zero(tmp_path: Path) -> None:
    """SC-AC1 hostile: with nothing in the window, M1, M3, M4 and M6 say "no …", never 0."""
    lines = _sc_lines(tmp_path, {})
    for prefix in ("M1 ", "M3 ", "M4 ", "M6 "):
        block = _block(lines, prefix)
        assert not any(re.search(r"\b0\b", line.split(":", 1)[-1]) for line in block), block  # past "tier 0:"
        assert any(re.search(r"\bno\b", line) for line in block), block
    assert "owner messages per day (UTC): none" in lines


def test_the_scorecard_with_no_reader_says_unsupported(tmp_path: Path) -> None:
    result = _meter("--dir", str(_SC_FIXTURE), "--scorecard")
    assert result.returncode == 0
    assert "unsupported" in result.stdout
    assert "M1" not in result.stdout


# ---- SC-AC3 (core): turn ends are distinct ids ---------------------------------------


def _two_line_reply() -> dict:
    return {
        "main": (
            "(main thread)",
            [
                _owner(0),
                _reply(5, "r1"),
                _reply(6, "r1"),
                {"t": 60, "kind": "notification", "job_ids": ["b1"]},
                _reply(65, "r2"),
            ],
        )
    }


def test_one_reply_over_two_lines_is_one_turn_end(tmp_path: Path) -> None:
    """SC-AC3 (RED-FIRST): 2 turn ends and so 1 extra, not 3 and 2."""
    lines = _sc_lines(tmp_path, _two_line_reply())
    assert "  untiered: 1 exchanges · 1 extra · mean 1.00 · 0 with none" in lines, lines


def test_counting_turn_ends_per_line_is_caught(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """SC-AC3 planted mistake: counting each turn-end line gives 2 extra."""
    monkeypatch.setattr(agent_time, "count_turn_ends", lambda events: sum(1 for e in events if e.turn_end))
    lines = _in_process(tmp_path, _two_line_reply())
    assert "  untiered: 1 exchanges · 2 extra · mean 2.00 · 0 with none" in lines, lines


def test_turn_ends_with_no_id_count_one_each(tmp_path: Path) -> None:
    runs = {"main": ("(main thread)", [_owner(0), _reply(5, None), _reply(6, None), _reply(7, "x", end=False)])}
    assert "  untiered: 1 exchanges · 1 extra · mean 1.00 · 0 with none" in _sc_lines(tmp_path, runs)


# ---- SC-AC4: the Tier line grammar ---------------------------------------------------


@pytest.mark.parametrize(
    ("owner_text", "reply_text", "tier"),
    [
        ("Please.", "Tier: 1 — x", "tier 1"),
        ("Please.", "- **Tier:** 2 — y", "tier 2"),
        ("Please.", "Please state the Tier: 0 line", "untiered"),
        ("Please.", "No tier here.", "untiered"),
        ("Tier: 1 — said by the owner", "No tier here.", "untiered"),
        ("Please.", "Tier: 3", "untiered"),
        ("Please.", "Tier：0", "tier 0"),
        ("Please.", "1. Tier: 2 — numbered", "tier 2"),
        ("Please.", "Intro line.\n  * **Tier**: 0", "tier 0"),
    ],
)
def test_the_first_tier_line_in_jarvis_text_decides_the_tier(
    tmp_path: Path, owner_text: str, reply_text: str, tier: str
) -> None:
    runs = {"main": ("(main thread)", [_owner(0, owner_text), _reply(5, "m1", reply_text)])}
    lines = _sc_lines(tmp_path, runs)
    assert f"  {tier}: 1 exchanges · 0 extra · mean 0.00 · 1 with none" in lines, lines


def test_a_later_tier_line_does_not_change_the_first(tmp_path: Path) -> None:
    runs = {
        "main": (
            "(main thread)",
            [_owner(0), _reply(5, "m1", "Tier: 1 — first", end=False), _reply(9, "m2", "Tier: 2 — later")],
        )
    }
    lines = _sc_lines(tmp_path, runs)
    assert "  tier 1: 1 exchanges · 0 extra · mean 0.00 · 1 with none" in lines, lines
    assert "  tier 2: no exchanges" in lines


# ---- SC-AC5: the window -------------------------------------------------------------

_T = "2026-10-20T12:00:00+00:00"


def test_only_exchanges_whose_owner_message_is_in_the_window_count(tmp_path: Path) -> None:
    """Owner messages at T−1h, T and T+1h; window [T, T+30m)."""
    runs = {
        # T−1h's reply falls inside the window, but its owner message does not.
        "earlier": ("(main thread)", [_owner(-3600), _reply(300, "e1")]),
        # T: one reply inside, one at T+40m (ignored), then T+1h's owner message.
        "main": ("(main thread)", [_owner(0), _reply(600, "m1"), _reply(2400, "m2"), _owner(3600), _reply(3700, "m3")]),
        # A reviewer run that started before the window and edits inside it.
        "reviewer": (
            "reviewer",
            [{"t": -600, "kind": "inbound", "text": "Tier: 1\nFiles: a"}, _edit(600, "doc/qa/REVIEW-z.md")],
        ),
    }
    lines = _sc_lines(tmp_path, runs, "--since", "2026-10-20T12:00:00Z", "--until", "2026-10-20T12:30:00Z", t0=_T)
    assert "  untiered: 1 exchanges · 0 extra · mean 0.00 · 1 with none" in lines, lines
    assert "owner messages per day (UTC): 2026-10-20 1" in lines
    assert not any("REVIEW" in line or " z:" in line for line in lines)
    assert "M6 role-agent briefs with a Tier: line and a Files: line: no role-agent briefs" in lines, lines
    assert any(line.startswith("M3 ") and "no review or QA runs" in line for line in lines), lines


@pytest.mark.parametrize(
    "window",
    [
        ["--since", "2026-10-21", "--until", "2026-10-21"],
        ["--since", "2026-10-22", "--until", "2026-10-21"],
        ["--until", "2026-10-22 09:00"],
        ["--until", "2026-10-22T09:00:00+07:00"],
        ["--until", "2026/10/22"],
        ["--since", "2026-10-22 09:00"],
        ["--since", "2026-10-22T09:00:00+07:00"],
    ],
)
def test_a_bad_window_is_one_error_line_and_exit_0(window: list) -> None:
    result = _meter("--reader", str(_STUB_READER), "--dir", str(_SC_FIXTURE), "--scorecard", *window)
    assert result.returncode == 0
    assert re.fullmatch(r"agent-time: error: [^\n]*\n", result.stdout), result.stdout
    assert "Traceback" not in result.stderr


def test_since_takes_a_time_of_day_in_utc() -> None:
    assert agent_time.parse_since("2026-10-21T02:03:54Z") == dt.datetime(2026, 10, 21, 2, 3, 54, tzinfo=dt.timezone.utc)


# ---- SC-AC12: M4, minutes to the first reply after a tool result ----------------------


def test_m4_counts_the_first_turn_end_after_a_tool_result(tmp_path: Path) -> None:
    runs = {
        "a": ("(main thread)", [_owner(0), _result(30), _reply(90, "a1", "Tier: 0")]),
        "b": ("(main thread)", [_owner(1000), _reply(1010, "b1", "Tier: 1"), _result(1020), _reply(1060, "b2")]),
        "c": ("(main thread)", [_owner(2000), _reply(2010, "c1", "Tier: 2")]),
        "d": ("(main thread)", [_result(2990), _owner(3000), _reply(3010, "d1", "Tier: 2")]),
    }
    block = _block(_sc_lines(tmp_path, runs), "M4 ")
    assert "  tier 0: median 1.5 min (n 1) · no result: 0" in block, block
    assert "  tier 1: median 1.0 min (n 1) · no result: 0" in block, block
    assert "  tier 2: no result: 2" in block, block
    assert "  untiered: no exchanges" in block, block


# ---- SC-AC6: M3, review and QA runs per report slug ----------------------------------


def _review(name: str, *paths: str, agent_type: str = "reviewer") -> tuple:
    events = [{"t": 0, "kind": "inbound", "text": "Review."}] + [_edit(10 + i, p) for i, p in enumerate(paths)]
    return name, (agent_type, events)


def test_m3_counts_runs_per_slug_once_each(tmp_path: Path) -> None:
    runs = dict(
        [
            _review("r1", "/w/.wt/agent-x/doc/qa/REVIEW-a.md", "/w/.wt/agent-x/doc/qa/REVIEW-a.md"),
            _review("r2", "doc/qa/REVIEW-a.md"),
            _review("q1", "doc/qa/QA-a.md"),
            _review("r3"),
            _review("e1", "doc/qa/QA-a.md", agent_type="ai-engineer"),
        ]
    )
    lines = _sc_lines(tmp_path, runs)
    assert "  a: review 2 · QA 1" in lines, lines
    assert any(line.startswith("M3 ") and line.endswith("· 1 run wrote no report") for line in lines), lines


@pytest.mark.parametrize(
    "path",
    ["doc/qa/REVIEW-.md", "doc/qa/REVIEW-a.md.bak", "doc/qa/REVIEW-a\n.md", "notes/REVIEW-a.md", "xdoc/qa/REVIEW-a.md"],
)
def test_a_path_that_is_not_a_report_is_no_report(tmp_path: Path, path: str) -> None:
    lines = _sc_lines(tmp_path, dict([_review("r", path)]))
    assert any(line.startswith("M3 ") and line.endswith("· 1 run wrote no report") for line in lines), lines
    assert not any(re.match(r"  \S.*: review \d+ · QA \d+$", line) for line in lines), lines


@pytest.mark.parametrize("slug", ["s" * 65, "a b", "a/b"])
def test_a_slug_that_is_not_a_label_is_unprintable(tmp_path: Path, slug: str) -> None:
    lines = _sc_lines(tmp_path, dict([_review("r", f"doc/qa/REVIEW-{slug}.md")]))
    assert "  (unprintable label): review 1 · QA 0" in lines, lines
    assert not any(slug in line for line in lines)


def test_a_pathless_edit_is_no_report_and_no_crash(tmp_path: Path) -> None:
    events = [{"t": 0, "kind": "inbound", "text": "Review."}, {"t": 5, "kind": "tool_call", "tool_kind": "edit", "paths": []}]
    lines = _sc_lines(tmp_path, {"r": ("qa", events)})
    assert any(line.startswith("M3 ") and line.endswith("· 1 run wrote no report") for line in lines), lines


# ---- SC-AC7: M6, briefs carrying a Tier: and a Files: line -----------------------------


def _brief(text: Optional[str], agent_type: str) -> tuple:
    events = [{"t": 0, "kind": "inbound", "text": text}] if text is not None else []
    return agent_type, events + [{"t": 5, "kind": "model", "message_id": "m"}]


def test_m6_counts_briefs_with_both_field_lines(tmp_path: Path) -> None:
    runs = {
        "1": _brief("Tier: 1 — x\nFiles: a", "ai-engineer"),
        "2": _brief("- **Tier:** 2\n- Files:\n  - a", "reviewer"),
        "3": _brief("Files: a", "qa"),
        "4": _brief("Tier: 1", "pm"),
        "5": _brief("see the Tier: 1 and Files: a lines", "ba-sa"),
        "6": _brief("Explore freely.", "Explore"),
    }
    lines = _sc_lines(tmp_path, runs)
    assert "M6 role-agent briefs with a Tier: line and a Files: line: 2 of 5" in lines, lines


def test_a_role_run_with_no_inbound_event_has_no_brief_lines(tmp_path: Path) -> None:
    lines = _sc_lines(tmp_path, {"1": _brief(None, "frontend-qa"), "2": _brief("Tier: 1\nFiles: a", "frontend-engineer")})
    assert "M6 role-agent briefs with a Tier: line and a Files: line: 1 of 2" in lines, lines


# ---- SC-AC8: M2 and M7 from correction_rate -----------------------------------------


def _lesson(memory: Path, name: str, date: str, mechanism: bool) -> None:
    mech = "mechanism: tests/x.py\n" if mechanism else ""
    (memory / name).write_text(f"---\nname: {name}\ntype: feedback\ndate: {date}\n{mech}---\nbody\n", "utf-8")


def test_m2_and_m7_read_the_memory_directory(tmp_path: Path) -> None:
    memory = tmp_path / "mem"
    memory.mkdir()
    # --until 2026-10-21 → the date is 2026-10-20; 3 and 9 days before it.
    _lesson(memory, "recent.md", "2026-10-17", mechanism=True)
    _lesson(memory, "older.md", "2026-10-11", mechanism=False)
    (memory / "INDEX.md").write_text("# index\n", "utf-8")
    result = _sc_meter(_SC_FIXTURE, memory, *_SC_WINDOW)
    lines = result.stdout.splitlines()
    assert "M2 owner corrections: 1 in the 7 days to 2026-10-20 (previous 7: 1, flat)" in lines, lines
    assert "M7 1 lesson(s) since 2026-10-08 with no mechanism" in lines, lines


def test_a_missing_memory_directory_is_said_not_zero(tmp_path: Path) -> None:
    result = _sc_meter(_SC_FIXTURE, tmp_path / "absent", *_SC_WINDOW)
    lines = result.stdout.splitlines()
    assert result.returncode == 0 and "Traceback" not in result.stderr
    assert "M2, M7: memory directory not found" in lines, lines
    assert not any(line.startswith(("M2 ", "M7 ")) for line in lines), lines
    assert any(line.startswith("M1 ") for line in lines)


def test_an_unreadable_memory_file_is_not_measured_and_the_rest_prints(tmp_path: Path) -> None:
    memory = tmp_path / "mem"
    memory.mkdir()
    (memory / "bad.md").write_bytes(b"---\ntype: feedback\n\xff\xfe\n---\n")
    result = _sc_meter(_SC_FIXTURE, memory, *_SC_WINDOW)
    lines = result.stdout.splitlines()
    assert result.returncode == 0 and "Traceback" not in result.stderr
    assert "M2, M7: not measured (unreadable memory file)" in lines, lines
    for prefix in ("M1 ", "M3 ", "M4 ", "M6 "):
        assert any(line.startswith(prefix) for line in lines), prefix


# ---- SC-AC10: nothing from the transcripts is printed ---------------------------------


def test_the_canary_never_reaches_the_scorecard_output(tmp_path: Path) -> None:
    canary = "CANARY-7f3a"
    raw = "".join(p.read_text("utf-8") for p in _SC_FIXTURE.glob("*.json"))
    assert raw.count(canary) >= 6  # owner, Jarvis, brief and non-slug path text
    result = _sc_meter(_SC_FIXTURE, tmp_path, *_SC_WINDOW)
    assert result.stdout.startswith("scorecard — ")
    assert canary not in result.stdout + result.stderr


def test_an_internal_error_in_the_scorecard_prints_its_type_only(tmp_path: Path) -> None:
    raising = tmp_path / "raising_reader.py"
    raising.write_text(
        "import agent_time, datetime as dt\n"
        "class Odd:\n"
        "    def __lt__(self, other):\n"
        "        raise RuntimeError('/home/someone/CANARY-7f3a/agent.jsonl')\n"
        "    __le__ = __gt__ = __ge__ = __lt__\n"
        "def runs(source, since):\n"
        "    yield agent_time.Run('(main thread)', [agent_time.Event(Odd(), 'inbound', owner=True)])\n",
        "utf-8",
    )
    result = _meter("--reader", str(raising), "--dir", str(tmp_path), "--scorecard")
    assert result.returncode == 0
    assert result.stdout.strip() == "agent-time: internal error: RuntimeError"
    assert "CANARY-7f3a" not in result.stdout + result.stderr
