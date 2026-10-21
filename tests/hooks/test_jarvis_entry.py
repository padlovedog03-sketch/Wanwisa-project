"""Jarvis entry — SPEC-jarvis-coordinator JC-AC1, JC-AC2, JC-AC4.

Every owner message must reach the Jarvis coordinator by default. Two paths
carry that (spec "Path selection (D6)"):

* the committed `agent` setting names `jarvis`, whose definition is a pointer
  to AGENTS.md (JC-AC1, JC-AC2);
* a UserPromptSubmit hook injects the same pointer whenever the main thread
  runs with no named agent (JC-AC4).

Each hostile case runs the same assertion helper against a planted copy under
`tmp_path`, never against an edited repo file.

Run: `python3 -m pytest tests/hooks/test_jarvis_entry.py -q`
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SETTINGS = _REPO_ROOT / ".claude" / "settings.json"
_AGENTS_DIR = _REPO_ROOT / ".claude" / "agents"
_HOOK = _REPO_ROOT / ".claude" / "hooks" / "inject_jarvis.py"
_HOOK_COMMAND = 'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/inject_jarvis.py"'
_MAX_BODY_CHARS = 600

_JARVIS_MD = """---
name: jarvis
description: Main-thread coordinator. Not for dispatch.
---
You are Jarvis. Follow AGENTS.md; it holds every rule.
"""


# ---------------------------------------------------------------------------
# Helpers shared by the repo check and the planted hostile copies
# ---------------------------------------------------------------------------


def _frontmatter_and_body(text: str) -> tuple[str, str]:
    """The frontmatter block and the body below it, as JC-AC2 and JC-AC4 read them:
    the body is everything after the closing `---` line, stripped."""
    match = re.match(r"\A---\n(.*?)\n---\n(.*)\Z", text, re.DOTALL)
    if not match:
        return "", ""
    return match.group(1), match.group(2).strip()


def _entry_problems(settings_path: Path, agents_dir: Path) -> list[str]:
    """JC-AC1: every defect in the Jarvis entry, each named."""
    try:
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
    except ValueError as exc:
        return [f"settings.json is not valid JSON ({exc})"]
    problems = []
    if "agent" not in settings:
        problems.append("settings.json has no `agent` key")
    elif settings["agent"] != "jarvis":
        problems.append(f"settings.json `agent` is {settings['agent']!r}, not exactly 'jarvis'")
    definition = agents_dir / "jarvis.md"
    if not definition.is_file():
        return problems + ["jarvis.md is missing"]
    frontmatter, _ = _frontmatter_and_body(definition.read_text(encoding="utf-8"))
    name = re.search(r"^name:[ \t]*(.*)$", frontmatter, re.MULTILINE)
    if not name or name.group(1) != settings.get("agent"):
        problems.append(f"jarvis.md `name:` is {name.group(1) if name else None!r}, not the setting's value")
    tools = re.search(r"^tools:[ \t]*(.*)$", frontmatter, re.MULTILINE)
    if tools and not re.search(r"\bAgent\b", tools.group(1)):
        problems.append("jarvis.md has a `tools:` line without Agent")
    return problems


def _body_problems(body: str) -> list[str]:
    """JC-AC2: the body is a pointer, not a rule."""
    problems = []
    if "AGENTS.md" not in body:
        problems.append("body does not name AGENTS.md")
    if len(body) > _MAX_BODY_CHARS:
        problems.append(f"body is {len(body)} characters, over {_MAX_BODY_CHARS}")
    if re.search(r"<[A-Z][A-Z0-9_]*>", body):
        problems.append("body carries an upper-case angle-bracket placeholder")
    return problems


def _registered(settings: dict) -> bool:
    """JC-AC4: the fallback hook is registered under UserPromptSubmit."""
    for group in settings.get("hooks", {}).get("UserPromptSubmit", []):
        for hook in group.get("hooks", []):
            if hook.get("command") == _HOOK_COMMAND:
                return True
    return False


def _plant(tmp_path: Path, settings_text: str, jarvis_md: str | None = _JARVIS_MD) -> tuple[Path, Path]:
    settings = tmp_path / "settings.json"
    settings.write_text(settings_text, encoding="utf-8")
    agents = tmp_path / "agents"
    agents.mkdir()
    if jarvis_md is not None:
        (agents / "jarvis.md").write_text(jarvis_md, encoding="utf-8")
    return settings, agents


def _run_hook(stdin: str, hook: Path = _HOOK) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(hook)], input=stdin, capture_output=True, text=True, timeout=30, check=False
    )


def _repo_body() -> str:
    return _frontmatter_and_body((_AGENTS_DIR / "jarvis.md").read_text(encoding="utf-8"))[1]


# ---------------------------------------------------------------------------
# JC-AC1 — the committed setting names jarvis, and the definition matches
# ---------------------------------------------------------------------------


def test_the_committed_entry_names_jarvis_and_its_definition() -> None:
    assert _entry_problems(_SETTINGS, _AGENTS_DIR) == []


@pytest.mark.parametrize(
    ("settings_text", "jarvis_md", "named"),
    [
        ("{}", _JARVIS_MD, "no `agent` key"),
        ('{"agent": "Jarvis"}', _JARVIS_MD, "not exactly 'jarvis'"),
        ('{"agent": "jarvis "}', _JARVIS_MD, "not exactly 'jarvis'"),
        ('{"agent": "jarvis​"}', _JARVIS_MD, "not exactly 'jarvis'"),
        ('{"agent": "jarvis"}', None, "jarvis.md is missing"),
        ('{"agent": "jarvis"}', _JARVIS_MD.replace("name: jarvis", "name: jarvis2"), "`name:` is 'jarvis2'"),
        ('{"agent": "jarvis"}', _JARVIS_MD.replace("description:", "tools: Read, Bash\ndescription:"), "without Agent"),
        ('{"agent": "jarvis",}', _JARVIS_MD, "not valid JSON"),
    ],
    ids=["key-removed", "capitalised", "trailing-space", "zero-width", "md-missing", "name-differs",
         "tools-without-agent", "invalid-json"],
)
def test_a_broken_entry_is_red_naming_the_defect(
    tmp_path: Path, settings_text: str, jarvis_md: str | None, named: str
) -> None:
    settings, agents = _plant(tmp_path, settings_text, jarvis_md)
    problems = _entry_problems(settings, agents)
    assert any(named in p for p in problems), problems


def test_a_renamed_definition_counts_as_missing(tmp_path: Path) -> None:
    settings, agents = _plant(tmp_path, '{"agent": "jarvis"}')
    (agents / "jarvis.md").rename(agents / "jarvis-old.md")
    assert "jarvis.md is missing" in _entry_problems(settings, agents)


def test_a_tools_line_that_lists_agent_is_accepted(tmp_path: Path) -> None:
    settings, agents = _plant(
        tmp_path, '{"agent": "jarvis"}', _JARVIS_MD.replace("description:", "tools: Agent, Read\ndescription:")
    )
    assert _entry_problems(settings, agents) == []


# ---------------------------------------------------------------------------
# JC-AC2 — the body is a pointer to AGENTS.md and holds no rule
# ---------------------------------------------------------------------------


def test_the_committed_body_is_a_short_pointer_to_agents_md() -> None:
    body = _repo_body()
    assert body, "jarvis.md has no body below its frontmatter"
    assert _body_problems(body) == []


@pytest.mark.parametrize(
    ("body", "named"),
    [
        ("Follow AGENTS.md. " + "x" * (601 - len("Follow AGENTS.md. ")), "601 characters"),
        ("Follow the rules file; it holds every rule.", "does not name AGENTS.md"),
        # Not a name bootstrap.sh rewrites, so this case survives bootstrapping.
        ("Follow AGENTS.md for <SERVICE_NAME>.", "placeholder"),
    ],
    ids=["601-chars", "no-agents-md", "placeholder"],
)
def test_a_body_that_is_not_a_pointer_is_red(body: str, named: str) -> None:
    problems = _body_problems(body)
    assert any(named in p for p in problems), problems


def test_a_body_of_exactly_600_characters_passes() -> None:
    body = "Follow AGENTS.md. " + "x" * (600 - len("Follow AGENTS.md. "))
    assert _body_problems(body) == []


# ---------------------------------------------------------------------------
# JC-AC4 — the fallback hook injects the pointer only when no agent is named
# ---------------------------------------------------------------------------


def test_the_fallback_hook_is_registered_under_user_prompt_submit() -> None:
    assert _registered(json.loads(_SETTINGS.read_text(encoding="utf-8")))


def test_the_registration_check_is_red_when_the_entry_is_removed() -> None:
    settings = json.loads(_SETTINGS.read_text(encoding="utf-8"))
    settings["hooks"]["UserPromptSubmit"] = [
        group
        for group in settings["hooks"].get("UserPromptSubmit", [])
        if all(hook.get("command") != _HOOK_COMMAND for hook in group.get("hooks", []))
    ]
    assert not _registered(settings)


@pytest.mark.parametrize(
    "payload",
    [{"hook_event_name": "UserPromptSubmit", "prompt": "hi"}, {"agent_type": None}, {"agent_type": ""}],
    ids=["absent", "null", "empty"],
)
def test_no_named_agent_injects_exactly_the_pointer_body(payload: dict) -> None:
    result = _run_hook(json.dumps(payload))
    assert result.returncode == 0, result.stderr
    assert result.stdout == _repo_body()


@pytest.mark.parametrize("agent_type", ["jarvis", "Jarvis", " jarvis ", "jar​vis", "ｊａｒｖｉｓ"])
def test_the_jarvis_main_thread_gets_nothing(agent_type: str) -> None:
    result = _run_hook(json.dumps({"agent_type": agent_type}))
    assert (result.returncode, result.stdout) == (0, ""), result.stderr


@pytest.mark.parametrize("agent_type", ["reviewer", "Explore", "jarvis-helper"])
def test_a_deliberately_chosen_agent_is_left_alone(agent_type: str) -> None:
    result = _run_hook(json.dumps({"agent_type": agent_type}))
    assert (result.returncode, result.stdout) == (0, ""), result.stderr


@pytest.mark.parametrize("stdin", ["not json", "", "[1, 2]", '"a string"'], ids=["malformed", "empty", "array", "string"])
def test_a_bad_payload_exits_0_silently(stdin: str) -> None:
    result = _run_hook(stdin)
    assert (result.returncode, result.stdout) == (0, "")
    assert "Traceback" not in result.stderr


def _hook_tree(tmp_path: Path) -> Path:
    """A copy of the hook in a tmp `.claude/hooks/`, beside a tmp `.claude/agents/`."""
    hooks = tmp_path / ".claude" / "hooks"
    hooks.mkdir(parents=True)
    (tmp_path / ".claude" / "agents").mkdir()
    return Path(shutil.copy(_HOOK, hooks / "inject_jarvis.py"))


def test_a_missing_definition_injects_nothing(tmp_path: Path) -> None:
    result = _run_hook("{}", _hook_tree(tmp_path))
    assert (result.returncode, result.stdout) == (0, "")
    assert "Traceback" not in result.stderr


def test_a_definition_that_is_not_utf8_injects_nothing(tmp_path: Path) -> None:
    hook = _hook_tree(tmp_path)
    (tmp_path / ".claude" / "agents" / "jarvis.md").write_bytes(b"---\nname: jarvis\n---\n\xff\xfe bad")
    result = _run_hook("{}", hook)
    assert (result.returncode, result.stdout) == (0, "")
    assert "Traceback" not in result.stderr


def test_the_hook_reads_the_definition_beside_it(tmp_path: Path) -> None:
    """The planted-tree cases above are only meaningful if the copied hook
    really reads its own tree: a planted body comes out verbatim."""
    hook = _hook_tree(tmp_path)
    (tmp_path / ".claude" / "agents" / "jarvis.md").write_text(_JARVIS_MD, encoding="utf-8")
    result = _run_hook("{}", hook)
    assert result.stdout == _frontmatter_and_body(_JARVIS_MD)[1]
