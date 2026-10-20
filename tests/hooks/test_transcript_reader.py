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
