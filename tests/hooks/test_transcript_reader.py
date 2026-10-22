"""Tests for `.claude/meter/transcript_reader.py` — adapter ก's reader for the meter.

WHY THIS FILE EXISTS. The coordinator's first hand-run measurement treated the
assistant's internal bookkeeping events (attachments, API requests) as activity
and reported idle time 7 minutes wrong, with no error (PRD brief). The reader
therefore admits an allow-list of clock events, `CLOCK_EVENT_TYPES`, and this
file proves two things about it: over the golden timeline written in the
adapter's own format, with internal events interleaved, the totals equal the
neutral golden totals exactly; and widening the allow-list by the two types
that caused the original mistake is caught, naming the numbers that move.

It also proves the meter never prints transcript content (R39): a canary is
planted in a tool command, the first inbound message, the run's description
and its file name.

Run: `python3 -m pytest tests/hooks/test_transcript_reader.py -q`   (stdlib only)
"""

from __future__ import annotations

import datetime as dt
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "scripts"))
import agent_time  # noqa: E402  (path must be set up first)

_READER_REL = ".claude/meter/transcript_reader.py"
_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "transcripts"
_SINCE = dt.datetime(2000, 1, 1, tzinfo=dt.timezone.utc)
_CANARY = "CANARY-7f3a"

#: Golden totals in seconds (SPEC-verify-tiers-merge-gate.md, Increment 1).
GOLDEN = {
    "model": 150,
    "tests": 361,
    "tests:running": 120,
    "tests:bg-launch": 1,
    "tests:bg-wait": 120,
    "tests:polling": 120,
    "waits": 0,
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


@pytest.fixture()
def reader():
    module = agent_time.load_reader(_REPO_ROOT / _READER_REL)
    assert module is not None, f"{_READER_REL} is missing"
    return module


def _only_run(reader, source: Path = _FIXTURE) -> agent_time.Run:
    runs = list(reader.runs(source, _SINCE))
    assert len(runs) == 1, len(runs)
    return runs[0]


def _meter(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "scripts/agent_time.py", "--reader", _READER_REL, *args],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


# ---- J-AC2: the adapter's format gives the neutral golden totals -------------


def test_adapter_transcript_gives_the_golden_totals(reader) -> None:
    run = _only_run(reader)
    assert run.agent_type == "ai-engineer"
    assert_totals(agent_time.categorise(run), GOLDEN)


def test_internal_events_are_excluded_and_counted_by_type(reader) -> None:
    run = _only_run(reader)
    assert dict(run.excluded) == {
        "api-request-blob": 1,
        "api-request": 1,
        "attachment": 1,
        "system": 1,
        "queue-operation": 1,
    }
    assert run.unreadable_lines == 1


def test_cli_prints_excluded_counts_and_the_golden_run(reader) -> None:
    result = _meter("--dir", str(_FIXTURE), "--since", "2000-01-01")
    assert result.returncode == 0, result.stderr
    out = result.stdout
    assert (
        "excluded events (adapter-internal, not timed): api-request 1 · api-request-blob 1"
        " · attachment 1 · queue-operation 1 · system 1"
    ) in out
    assert "reader: transcript_reader.py · unreadable lines: 1" in out
    # 578 s active = 9.6 min, 9 turns, 150 s model = 2.5 min (26%).
    assert "ai-engineer: 1 runs · active median 9.6 min · turns median 9" in out
    assert re.search(r"model generating\s+2\.5 min/run\s+26%", out), out
    assert "idle (not active): median 10.0 min/run" in out


# ---- J-AC3: widening the clock allow-list is caught (RED-FIRST mutation) -----


def test_widening_the_clock_allow_list_is_caught(reader, monkeypatch: pytest.MonkeyPatch) -> None:
    """The coordinator's own first-measurement mistake, planted on purpose.

    With `attachment` and `api-request` admitted as clock events, the golden
    check must fail naming idle 600 → 675 and active 578 → 503.
    """
    monkeypatch.setattr(
        reader, "CLOCK_EVENT_TYPES", reader.CLOCK_EVENT_TYPES | {"attachment", "api-request"}
    )
    totals = agent_time.categorise(_only_run(reader))
    with pytest.raises(AssertionError) as caught:
        assert_totals(totals, GOLDEN)
    message = str(caught.value)
    assert "idle 600 → 675" in message
    assert "active 578 → 503" in message
    # The hand-derived numbers of design §J.4, now measured.
    assert (totals["model"], totals["tests"]) == (149, 287)


def test_the_allow_list_is_exactly_user_and_assistant(reader) -> None:
    assert reader.CLOCK_EVENT_TYPES == frozenset({"user", "assistant"})


# ---- J-AC6: no transcript content in the output (R39) ------------------------


def test_the_canary_never_reaches_stdout_or_stderr() -> None:
    assert any(_CANARY in p.name for p in _FIXTURE.rglob("*")), "canary file name not planted"
    planted = (_FIXTURE / "session-0001" / "subagents" / f"agent-{_CANARY}.jsonl").read_text("utf-8")
    assert planted.count(_CANARY) == 3, "canary must sit in the brief, a command and a file path"
    result = _meter("--dir", str(_FIXTURE), "--since", "2000-01-01", "--rework")
    assert result.returncode == 0
    assert "ai-engineer: 1 runs" in result.stdout, "the run must actually be read"
    assert _CANARY not in result.stdout
    assert _CANARY not in result.stderr


# ---- J-AC7 (reader half): unreadable lines and empty runs --------------------


def test_malformed_lines_are_counted_and_reported(tmp_path: Path, reader) -> None:
    sub = tmp_path / "s" / "subagents"
    sub.mkdir(parents=True)
    (sub / "agent-a.meta.json").write_text(json.dumps({"agentType": "qa"}), "utf-8")
    (sub / "agent-a.jsonl").write_text(
        '{"type": "user", "timestamp": "2026-10-20T00:00:00.000Z", "message": {"content": "go"}}\n'
        "{broken\n"
        '{"type": "assistant", "timestamp": "2026-10-20T00:00:05.000Z", "message": {"id": "m", "content": []}}\n',
        "utf-8",
    )
    run = _only_run(reader, tmp_path)
    assert (run.agent_type, run.unreadable_lines, len(run.events)) == ("qa", 1, 2)


def test_a_run_of_internal_events_only_has_no_clock_events(tmp_path: Path, reader) -> None:
    sub = tmp_path / "s" / "subagents"
    sub.mkdir(parents=True)
    (sub / "agent-a.meta.json").write_text(json.dumps({"agentType": "qa"}), "utf-8")
    (sub / "agent-a.jsonl").write_text('{"type": "attachment", "timestamp": "2026-10-20T00:00:00.000Z"}\n', "utf-8")
    run = _only_run(reader, tmp_path)
    assert run.events == [] and run.excluded == {"attachment": 1}


def test_main_thread_sessions_are_read_as_the_main_thread(tmp_path: Path, reader) -> None:
    (tmp_path / "session-x.jsonl").write_text(
        '{"type": "user", "timestamp": "2026-10-20T00:00:00.000Z", "message": {"content": "hi"}}\n'
        '{"type": "assistant", "timestamp": "2026-10-20T00:00:03.000Z", "message": {"id": "m", "content": []}}\n',
        "utf-8",
    )
    run = _only_run(reader, tmp_path)
    assert run.agent_type == "(main thread)"
    assert agent_time.categorise(run)["model"] == 3


def test_runs_ending_before_since_are_left_out(reader) -> None:
    assert list(reader.runs(_FIXTURE, dt.datetime(2027, 1, 1, tzinfo=dt.timezone.utc))) == []


def test_a_mention_of_task_notification_is_not_a_notification(tmp_path: Path, reader) -> None:
    """Only the tag counts: local transcripts carry user lines that merely mention the word."""
    (tmp_path / "s.jsonl").write_text(
        '{"type": "user", "timestamp": "2026-10-20T00:00:00.000Z", "message": {"content": "about task-notification"}}\n',
        "utf-8",
    )
    assert _only_run(reader, tmp_path).events[0].kind == "inbound"


def test_a_timestamp_without_an_offset_is_excluded_and_counted(tmp_path: Path, reader) -> None:
    """Not timed (guessing UTC could move it by hours) and not hidden: it shows on the excluded line."""
    (tmp_path / "s.jsonl").write_text(
        '{"type": "user", "timestamp": "2026-10-20T00:00:00.000Z", "message": {"content": "go"}}\n'
        '{"type": "assistant", "timestamp": "2026-10-20T00:00:05", "message": {"id": "m", "content": []}}\n',
        "utf-8",
    )
    run = _only_run(reader, tmp_path)
    assert [e.kind for e in run.events] == ["inbound"]
    assert run.excluded == {"assistant (timestamp without offset)": 1}


def test_a_shell_command_that_is_not_a_string_is_not_classified(tmp_path: Path, reader) -> None:
    (tmp_path / "s.jsonl").write_text(
        '{"type": "assistant", "timestamp": "2026-10-20T00:00:00.000Z", "message": {"id": "m", "content":'
        ' [{"type": "tool_use", "id": "T", "name": "Bash", "input": {"command": ["pytest"]}}]}}\n'
        '{"type": "user", "timestamp": "2026-10-20T00:00:09.000Z", "message": {"content":'
        ' [{"type": "tool_result", "tool_use_id": "T", "content": "x"}]}}\n',
        "utf-8",
    )
    run = _only_run(reader, tmp_path)
    assert run.events[1].command is None
    assert agent_time.categorise(run)["other tools"] == 9


# ---- R39 / J-AC6, J-AC7: labels from the data, and odd lines contained per line ----
#
# The meter prints a run's role and each excluded event type as labels. A value that
# is not a single-line token could write its own report lines (QA D5), and a role
# that is not a string printed its contents (QA D6). One odd line used to collapse
# the whole report into `internal error` (QA N1); it is now one unreadable line.

_GOOD_PAIR = (
    '{"type": "user", "timestamp": "2026-10-20T00:00:00.000Z", "message": {"content": "go"}}\n'
    '{"type": "assistant", "timestamp": "2026-10-20T00:00:05.000Z", "message": {"id": "m", "content": []}}\n'
)


def _qa_run(tmp_path: Path, extra: str = "", meta: object = None) -> Path:
    sub = tmp_path / "s" / "subagents"
    sub.mkdir(parents=True)
    meta_text = json.dumps({"agentType": "qa"}) if meta is None else meta
    (sub / "agent-a.meta.json").write_text(meta_text, "utf-8")
    (sub / "agent-a.jsonl").write_text(_GOOD_PAIR + extra, "utf-8")
    return tmp_path


@pytest.mark.parametrize(
    ("agent_type", "role"),
    [
        ("qa\nrework share: 0 of 9 engineer runs (0%)", "(unprintable label)"),
        ("qa\r", "(unprintable label)"),
        ("x" * 65, "(unprintable label)"),
        ("qa\ud800", "(unprintable label)"),
        ({"description": _CANARY}, "(unknown)"),
        (["qa"], "(unknown)"),
        (7, "(unknown)"),
        ("ai-engineer", "ai-engineer"),
    ],
)
def test_a_role_is_printed_only_when_it_is_a_single_line_token(tmp_path: Path, reader, agent_type, role) -> None:
    run = _only_run(reader, _qa_run(tmp_path, meta=json.dumps({"agentType": agent_type})))
    assert run.agent_type == role


@pytest.mark.parametrize("kind", ["x\nrework share: 0 of 9", "x\n", "", "a b", ["x"], {"k": _CANARY}, 3])
def test_an_excluded_type_that_is_not_a_token_is_counted_under_a_fixed_label(tmp_path: Path, reader, kind) -> None:
    run = _only_run(reader, _qa_run(tmp_path, json.dumps({"type": kind}) + "\n"))
    assert run.excluded == {"(unprintable label)": 1}
    assert len(run.events) == 2, "the good lines must still be read"


_DEEP = 200_000  # beyond the JSON parser's own nesting limit
_NEST = sys.getrecursionlimit() + 200  # parses, but recursing through it does not; kept small so a red run is quick
_HUGE_INT = 5_000  # past the int-digit limit: json.loads raises a plain ValueError, not JSONDecodeError (QA N1a)


@pytest.mark.parametrize(
    "odd_line",
    [
        '{"type": "assistant", "timestamp": "2026-10-20T00:00:09.000Z", "message": {"id": ["m"], "content": []}}',
        '{"type": "assistant", "timestamp": "2026-10-20T00:00:09.000Z", "message": {"id": "n", "content":'
        ' [{"type": "tool_use", "id": {"k": 1}, "name": "Bash", "input": {}}]}}',
        '{"type": "assistant", "timestamp": "2026-10-20T00:00:09.000Z", "message": {"id": "n", "content":'
        ' [{"type": "tool_use", "id": "T", "name": ["Bash"], "input": {}}]}}',
        '{"type": "user", "timestamp": "2026-10-20T00:00:09.000Z", "message": {"content":'
        ' [{"type": "tool_result", "tool_use_id": ["T"], "content": "x"}]}}',
        "[" * _DEEP + "]" * _DEEP,
        '{"type": "user", "timestamp": "2026-10-20T00:00:09.000Z", "message": {"content": '
        + '[{"content": ' * _NEST + '"x"' + "}]" * _NEST + "}}",
        "1" * _HUGE_INT,
        '{"type": "user", "timestamp": "2026-10-20T00:00:09.000Z", "n": ' + "1" * _HUGE_INT + "}",
    ],
    ids=[
        "list-message-id",
        "dict-tool-id",
        "list-tool-name",
        "list-tool-use-id",
        "deep-json",
        "deep-content",
        "huge-int",
        "huge-int-field",
    ],
)
def test_one_odd_line_is_one_unreadable_line_and_the_report_goes_on(tmp_path: Path, reader, odd_line: str) -> None:
    source = _qa_run(tmp_path, odd_line + "\n")
    run = _only_run(reader, source)
    assert (run.unreadable_lines, len(run.events)) == (1, 2)
    result = _meter("--dir", str(source), "--since", "2000-01-01")
    assert result.returncode == 0 and "Traceback" not in result.stderr
    assert "internal error" not in result.stdout, result.stdout
    assert "unreadable lines: 1" in result.stdout and "qa: 1 runs" in result.stdout, result.stdout


def test_a_meta_file_nested_too_deep_is_an_unknown_role_and_one_unreadable_line(tmp_path: Path, reader) -> None:
    run = _only_run(reader, _qa_run(tmp_path, meta="[" * _DEEP + "]" * _DEEP))
    assert (run.agent_type, run.unreadable_lines, len(run.events)) == ("(unknown)", 1, 2)


# ---- J2-AC9: edited paths for the size class (R41) ------------------------------
#
# Input keys measured 2026-10-20 over 909 local transcripts: Edit and Write carry
# `file_path` (9,612 calls, every one absolute, every line with a top-level `cwd`).
# NotebookEdit's `notebook_path` is from the tool's own schema. MultiEdit appeared
# in no local transcript; its `file_path` follows the spec and is unverified.

_CWD = "/work/repo"


def _tool_line(name: str, tool_input: object, cwd: object = _CWD, tool_id: str = "T") -> str:
    record = {
        "type": "assistant",
        "timestamp": "2026-10-20T00:00:01.000Z",
        "message": {"id": "m-" + tool_id, "content": [{"type": "tool_use", "id": tool_id, "name": name, "input": tool_input}]},
    }
    if cwd is not None:
        record["cwd"] = cwd
    return json.dumps(record) + "\n"


def _engineer_run(tmp_path: Path, lines: str) -> Path:
    sub = tmp_path / "s" / "subagents"
    sub.mkdir(parents=True)
    (sub / "agent-a.meta.json").write_text(json.dumps({"agentType": "ai-engineer"}), "utf-8")
    (sub / "agent-a.jsonl").write_text(_GOOD_PAIR + lines, "utf-8")
    return tmp_path


def _calls(run: agent_time.Run) -> list:
    return [(e.tool_kind, e.paths) for e in run.events if e.kind == "tool_call"]


def test_edit_events_carry_exactly_the_edited_paths(tmp_path: Path, reader) -> None:
    lines = (
        _tool_line("Edit", {"file_path": "/work/repo/a.py", "old_string": "x", "new_string": "y"}, tool_id="T1")
        + _tool_line("Write", {"file_path": "/work/repo/b.py", "content": "z"}, tool_id="T2")
        + _tool_line("MultiEdit", {"file_path": "/work/repo/c.py", "edits": []}, tool_id="T3")
        + _tool_line("NotebookEdit", {"notebook_path": "/work/repo/d.ipynb", "new_source": "s"}, tool_id="T4")
        + _tool_line("Edit", {"old_string": "x", "new_string": "y"}, tool_id="T5")
        + _tool_line("Read", {"file_path": "/work/repo/r.py"}, tool_id="T6")
        + _tool_line("Edit", {"file_path": "sub/../e.py"}, tool_id="T7")
    )
    run = _only_run(reader, _engineer_run(tmp_path, lines))
    assert _calls(run) == [
        ("edit", ("/work/repo/a.py",)),
        ("edit", ("/work/repo/b.py",)),
        ("edit", ("/work/repo/c.py",)),
        ("edit", ("/work/repo/d.ipynb",)),
        ("edit", ()),
        ("read", ()),
        ("edit", ("/work/repo/e.py",)),
    ]
    assert run.unreadable_lines == 0


@pytest.mark.parametrize(
    ("name", "tool_input", "cwd"),
    [
        ("Edit", {"file_path": 7}, _CWD),
        ("Edit", {"file_path": ["/a.py"]}, _CWD),
        ("Edit", {"file_path": {"p": _CANARY}}, _CWD),
        ("Edit", {"file_path": None}, _CWD),
        ("Edit", {"file_path": ""}, _CWD),
        ("Write", {}, _CWD),
        ("Edit", ["/work/repo/a.py"], _CWD),
        ("Edit", "/work/repo/a.py", _CWD),
        ("NotebookEdit", {"file_path": "/work/repo/d.ipynb"}, _CWD),
        ("MultiEdit", {"notebook_path": "/work/repo/d.ipynb"}, _CWD),
        ("Edit", {"file_path": "a.py"}, None),
        ("Edit", {"file_path": "a.py"}, "relative/cwd"),
        ("Edit", {"file_path": "a.py"}, 7),
        ("Edit", {"file_path": "a.py"}, ""),
    ],
    ids=[
        "int-path", "list-path", "dict-path", "null-path", "empty-path", "no-path-key", "list-input",
        "string-input", "notebook-with-file_path", "multiedit-with-notebook_path", "relative-no-cwd",
        "relative-relative-cwd", "relative-int-cwd", "relative-empty-cwd",
    ],
)
def test_an_edit_whose_path_cannot_be_determined_has_no_path(tmp_path: Path, reader, name, tool_input, cwd) -> None:
    """Never a crash and never an unreadable line: the call stays timed, its path is unknown."""
    run = _only_run(reader, _engineer_run(tmp_path, _tool_line(name, tool_input, cwd)))
    assert _calls(run) == [("edit", ())]
    assert run.unreadable_lines == 0 and len(run.events) == 4


@pytest.mark.parametrize(
    ("file_path", "cwd", "expected"),
    [
        ("./a.py", _CWD, "/work/repo/a.py"),
        ("a.py", _CWD + "/", "/work/repo/a.py"),
        ("../other/a.py", _CWD, "/work/other/a.py"),
        ("/work/repo/x/../a.py", _CWD, "/work/repo/a.py"),
        ("/work/repo//a.py", "/elsewhere", "/work/repo/a.py"),
        ("/work/repo/a\nb.py", _CWD, "/work/repo/a\nb.py"),
        ("/work/repo/a b.py", _CWD, "/work/repo/a b.py"),
    ],
)
def test_paths_are_normalised_against_the_line_cwd(tmp_path: Path, reader, file_path, cwd, expected) -> None:
    run = _only_run(reader, _engineer_run(tmp_path, _tool_line("Edit", {"file_path": file_path}, cwd)))
    assert _calls(run) == [("edit", (expected,))]


def _meter_lines(source: Path, *extra: str) -> list:
    result = _meter("--dir", str(source), "--since", "2000-01-01", *extra)
    assert result.returncode == 0 and "Traceback" not in result.stderr
    assert "internal error" not in result.stdout, result.stdout
    return result.stdout.splitlines()


def test_ten_thousand_edits_to_one_file_through_the_reader_are_small(tmp_path: Path) -> None:
    spellings = ["/work/repo/a.py", "./a.py", "a.py", "x/../a.py"]
    lines = "".join(
        _tool_line("Edit", {"file_path": spellings[i % 4]}, tool_id=f"T{i}") for i in range(10_000)
    )
    out = _meter_lines(_engineer_run(tmp_path, lines))
    assert any(line.strip().startswith("small  n=1") for line in out), out


def test_a_symlinked_spelling_is_counted_as_written(tmp_path: Path, reader) -> None:
    """Stated limit: paths are compared lexically, never resolved on disk.

    Resolving would read today's disk for yesterday's run: of 3,761 distinct edited
    paths in local engineer runs, 2,248 no longer exist (measured 2026-10-20), and
    none of those runs used a symlinked path.
    """
    real = tmp_path / "real"
    real.mkdir()
    (real / "a.py").write_text("", "utf-8")
    (tmp_path / "link").symlink_to(real)
    lines = _tool_line("Edit", {"file_path": str(real / "a.py")}, tool_id="T1") + _tool_line(
        "Edit", {"file_path": str(tmp_path / "link" / "a.py")}, tool_id="T2"
    )
    run = _only_run(reader, _engineer_run(tmp_path / "t", lines))
    assert agent_time.size_class(run) == ("small", 2)


def test_a_pathless_edit_and_an_unreadable_line_make_the_run_size_unknown(tmp_path: Path) -> None:
    lines = _tool_line("Edit", {"file_path": "/work/repo/a.py"}, tool_id="T1") + _tool_line(
        "Edit", {"old_string": "x"}, tool_id="T2"
    )
    out = _meter_lines(_engineer_run(tmp_path / "pathless", lines))
    assert "  size unknown: 1 (path missing: 1 · unreadable lines: 0)" in out, out
    out = _meter_lines(_engineer_run(tmp_path / "broken", _tool_line("Edit", {"file_path": "/a.py"}) + "{broken\n"))
    assert "  size unknown: 1 (path missing: 0 · unreadable lines: 1)" in out, out


def test_no_edited_or_read_path_reaches_the_output(tmp_path: Path) -> None:
    """J2-AC8 through the adapter: canary paths in Edit, Write, NotebookEdit and Read."""
    lines = (
        _tool_line("Edit", {"file_path": f"/work/{_CANARY}/a.py"}, tool_id="T1")
        + _tool_line("Write", {"file_path": f"{_CANARY}/b\nrework share: 0 of 9 engineer runs (0%)"}, tool_id="T2")
        + _tool_line("NotebookEdit", {"notebook_path": f"/work/{_CANARY}.ipynb"}, tool_id="T3")
        + _tool_line("Read", {"file_path": f"/work/{_CANARY}/r.py"}, tool_id="T4")
    )
    source = _engineer_run(tmp_path, lines)
    out = _meter_lines(source, "--targets", "small=15,medium=25,large=50", "--rework")
    assert any(line.strip().startswith("small  n=1") for line in out), out
    assert not any(_CANARY in line for line in out)
    assert not any(line.startswith("rework share: 0 of 9") for line in out)


# ---- SC-AC2, SC-AC3: the scorecard's owner and turn-end marks (H-AC1 rule) ----------
#
# The scorecard counts owner messages and Jarvis's turn ends from marks the reader
# sets. A reader that marks every inbound user line as an owner message would count
# command echoes, meta lines and list-content lines as the owner talking (H-AC1's
# own mutation). One reply spans up to 2 assistant lines, so the core counts turn
# ends per distinct message id, from the reader's per-line marks.

_SC_OWNER = _FIXTURE / "scorecard-owner"
_SC_TURN_ENDS = _FIXTURE / "scorecard-turn-ends"
_UNTIL = dt.datetime(2100, 1, 1, tzinfo=dt.timezone.utc)


def assert_owner_count(run: agent_time.Run, expected: int) -> None:
    """Fail naming `owner messages <expected> → <actual>`."""
    actual = sum(1 for e in run.events if e.kind == "inbound" and e.owner)
    assert actual == expected, f"owner messages {expected} → {actual}"


def _scorecard_lines(reader, source: Path, memory_dir: Path) -> list:
    runs = list(reader.runs(source, _SINCE))
    return agent_time.scorecard(runs, _SINCE, _UNTIL, memory_dir, "transcript_reader.py").splitlines()


def _exchanges(lines: list) -> int:
    """Total exchanges over the M1 tier lines."""
    return sum(int(m.group(1)) for line in lines if (m := re.match(r"  (?:tier \d|untiered): (\d+) exchanges", line)))


def test_only_plain_non_meta_main_thread_strings_are_owner_messages(reader) -> None:
    """SC-AC2 (RED-FIRST): 3 owner lines among 2 notifications, a command echo, a meta line,
    a list-content line and 4 tool results."""
    run = _only_run(reader, _SC_OWNER)
    assert_owner_count(run, 3)
    assert sum(1 for e in run.events if e.kind == "tool_result") == 4
    assert sum(1 for e in run.events if e.kind == "notification") == 2


def test_the_scorecard_reports_3_owner_messages_and_3_exchanges(reader, tmp_path: Path) -> None:
    """SC-AC2 through the core: the per-day owner line and the M1 exchanges."""
    lines = _scorecard_lines(reader, _SC_OWNER, tmp_path)
    assert "owner messages per day (UTC): 2026-10-20 3" in lines, lines
    assert _exchanges(lines) == 3, lines


def test_marking_every_inbound_line_as_owner_is_caught(reader, monkeypatch: pytest.MonkeyPatch) -> None:
    """SC-AC2 planted mistake (H-AC1's mutation): every inbound user line marked owner gives 6, not 3."""
    monkeypatch.setattr(reader, "_is_owner", lambda *args, **kwargs: True)
    with pytest.raises(AssertionError) as caught:
        assert_owner_count(_only_run(reader, _SC_OWNER), 3)
    assert "owner messages 3 → 6" in str(caught.value)


def test_a_subagent_brief_is_never_an_owner_message(tmp_path: Path, reader) -> None:
    """Subagent inbound lines are briefs from Jarvis, never the owner."""
    run = _only_run(reader, _qa_run(tmp_path))
    assert [e.owner for e in run.events if e.kind == "inbound"] == [False]


def test_a_reply_spanning_two_lines_is_one_turn_end(reader, tmp_path: Path) -> None:
    """SC-AC3 (RED-FIRST, reader marks): 3 end_turn lines, 2 distinct ids → 2 turn ends, 1 extra."""
    run = _only_run(reader, _SC_TURN_ENDS)
    assert [e.message_id for e in run.events if e.kind == "model" and e.turn_end] == ["r1", "r1", "r2"]
    lines = _scorecard_lines(reader, _SC_TURN_ENDS, tmp_path)
    assert "  tier 0: 1 exchanges · 1 extra · mean 1.00 · 0 with none" in lines, lines


def test_model_events_carry_their_text_for_tier_lines(reader) -> None:
    run = _only_run(reader, _SC_TURN_ENDS)
    assert next(e.text for e in run.events if e.kind == "model").startswith("Tier: 0")


@pytest.mark.parametrize(
    ("message", "turn_end"),
    [
        ({"stop_reason": "end_turn", "content": []}, True),  # no id: a turn end all the same
        ({"id": "m", "stop_reason": "tool_use", "content": []}, False),
        ({"id": "m", "stop_reason": ["end_turn"], "content": []}, False),
        ({"id": "m", "stop_reason": None, "content": []}, False),
    ],
)
def test_only_an_end_turn_stop_reason_is_a_turn_end(tmp_path: Path, reader, message: dict, turn_end: bool) -> None:
    """SC-AC3 hostile: a missing id, a tool_use stop and a non-string stop_reason, with no crash."""
    (tmp_path / "s.jsonl").write_text(
        json.dumps({"type": "assistant", "timestamp": "2026-10-20T00:00:00.000Z", "message": message}) + "\n",
        "utf-8",
    )
    run = _only_run(reader, tmp_path)
    assert run.unreadable_lines == 0
    assert [e.turn_end for e in run.events if e.kind == "model"] == [turn_end]


def test_an_end_turn_line_with_no_timestamp_is_excluded(tmp_path: Path, reader) -> None:
    """SC-AC3 hostile: an assistant line with no timestamp is excluded, as today."""
    (tmp_path / "s.jsonl").write_text(
        '{"type": "user", "timestamp": "2026-10-20T00:00:00.000Z", "message": {"content": "go"}}\n'
        '{"type": "assistant", "message": {"id": "m", "stop_reason": "end_turn", "content": []}}\n',
        "utf-8",
    )
    run = _only_run(reader, tmp_path)
    assert [e.kind for e in run.events] == ["inbound"]
    assert run.excluded == {"assistant (no timestamp)": 1}


def test_two_turn_ends_with_no_id_count_as_two(tmp_path: Path, reader) -> None:
    """SC-AC3 hostile: each id-less turn end counts as one, not merged into one."""
    source = tmp_path / "src"
    source.mkdir()
    (source / "s.jsonl").write_text(
        '{"type": "user", "timestamp": "2026-10-20T00:00:00.000Z", "message": {"content": "go"}}\n'
        '{"type": "assistant", "timestamp": "2026-10-20T00:00:01.000Z", "message": {"stop_reason": "end_turn", "content": []}}\n'
        '{"type": "assistant", "timestamp": "2026-10-20T00:00:02.000Z", "message": {"stop_reason": "end_turn", "content": []}}\n',
        "utf-8",
    )
    lines = _scorecard_lines(reader, source, tmp_path)
    assert "  untiered: 1 exchanges · 1 extra · mean 1.00 · 0 with none" in lines, lines
