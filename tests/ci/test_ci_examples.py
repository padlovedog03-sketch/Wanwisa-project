"""Proof that `ci-examples/` actually does what it claims to do.

WHY THIS FILE EXISTS. The wave that shipped `ci-examples/github-actions.yml`
and `ci-examples/azure-pipelines.yml` said, verbatim, in its own retrospective:
"`ci-examples/` has never been run or tested at all — every mechanism in this
repo declares that the real enforcement is CI on a protected branch, and
nothing proves those two files even work." That sentence was true. This file
makes it false, by extracting every command the two YAML files run and
executing each one for real, from a clean checkout, the way CI would invoke
it — not by reading the YAML and reasoning about it.

**`act` (the usual way to run GitHub Actions locally) was checked and is not
available in this environment** (`which act` — not found, and there is no
network access here to install it). Azure Pipelines cannot be run locally at
all outside a hosted agent. So every claim below is backed by running the
literal extracted shell/Python text as a real subprocess, never by a
simulated or hosted run — that substitution is stated here once rather than
re-argued at every test.

Two real, reproducible defects were found and fixed while building this:

1. **`on:` in `github-actions.yml` parsed as the boolean `True`, not the
   string `"on"`.** YAML 1.1 — what PyYAML's `SafeLoader` and most schema
   tools actually implement — resolves the bare word `on` as a boolean.
   GitHub's own workflow parser special-cases this and the file still ran on
   GitHub either way, so this is exactly the "a YAML linter is not enough"
   class of mistake: syntactically fine, semantically landmined the moment a
   standard tool touches it. Fixed by quoting it (`"on":`).
2. **The registry-check step used a different shell variable name in each
   file** (`$REGISTRY` in the GitHub version, `$APPROVAL_REGISTRY` in the
   Azure version) for what is otherwise the identical ~40-line inline Python
   check. Harmless functionally, but it meant the two files could no longer
   be verified as "the same gate, different syntax" — which is the whole
   promise `azure-pipelines.yml`'s own header comment makes ("ด่านเหมือนกับ
   ci-examples/github-actions.yml ทุกประการ ต่างแค่ไวยากรณ์"). Renamed the
   GitHub side to match; `test_gate_1_scripts_are_byte_identical` pins it.

**What is executed here, and what deliberately is not:**

* Gate 1 (registry check) and Gate 3 (placeholder scan) are self-contained —
  they touch no test infrastructure of their own — so they are run for real,
  repeatedly, with deliberately forged/clean inputs, exactly like the guard
  tests in `tests/hooks/` prove their hooks bite.
* Gate 2 (the exit gate) is proven via the same stub-copy technique
  `tests/hooks/test_verify_scripts.py` already established: a copy of
  `scripts/verify-full.sh` with only its own nested-pytest steps replaced by
  a harmless `echo`, so the real control flow runs but nothing recurses.
* Gate 4 (`python3 -m pytest tests/hooks/ -q`) is **not executed here on
  purpose** — this file lives outside `tests/hooks/`, but a hosted CI run of
  Gate 4 *is* this exact command, and if it is broken, every other test in
  this repo already fails to collect. Re-running it here would prove nothing
  additional and would risk exactly the unbounded-recursion trap
  `test_verify_scripts.py`'s docstring already warns about, one directory
  over. What is checked instead: the literal string in both CI files is
  identical to the literal string `scripts/verify-full.sh` itself runs for
  that step — so the three can never quietly drift apart.

Run: `python3 -m pytest tests/ci/ -q`   (no project dependencies required
beyond PyYAML, already used by nothing else in this repo — see the note on
`_YAML_UNAVAILABLE` below for what happens without it.)
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

try:
    import yaml

    _YAML_UNAVAILABLE = None
except ImportError as exc:  # pragma: no cover - environment-dependent
    yaml = None  # type: ignore[assignment]
    _YAML_UNAVAILABLE = str(exc)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_GH_PATH = _REPO_ROOT / "ci-examples" / "github-actions.yml"
_ADO_PATH = _REPO_ROOT / "ci-examples" / "azure-pipelines.yml"
_FULL = _REPO_ROOT / "scripts" / "verify-full.sh"
_BOOTSTRAP = _REPO_ROOT / "scripts" / "bootstrap.sh"

#: The exact strings the exit gate and the fast tier use for their two
#: permanent (non-placeholder) steps. Both CI files must invoke the gate the
#: same way the gate invokes itself — that agreement is the entire point of
#: this module, so it is pinned as data, not re-typed per test.
_EXIT_GATE_COMMAND = "./scripts/verify-full.sh"
_HOOKS_TEST_COMMAND = "python3 -m pytest tests/hooks/ -q"

pytestmark = pytest.mark.skipif(
    _YAML_UNAVAILABLE is not None,
    reason=f"PyYAML not installed, cannot parse the CI examples: {_YAML_UNAVAILABLE}",
)


def _load(path: Path) -> dict:
    """Parse a CI example with the real YAML 1.1 resolver, no fallback."""
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _gh_steps() -> list[dict]:
    return _load(_GH_PATH)["jobs"]["gates"]["steps"]


def _ado_steps() -> list[dict]:
    return _load(_ADO_PATH)["steps"]


def _find_step(steps: list[dict], name_key: str, needle: str) -> dict:
    """The single step whose name/displayName contains `needle`, or a loud
    failure naming what WAS found — an IndexError from a bad guess is a much
    worse failure message than this."""
    matches = [s for s in steps if needle in str(s.get(name_key, ""))]
    assert len(matches) == 1, (
        f"expected exactly one step with {name_key!r} containing {needle!r}, "
        f"found {len(matches)}: {[s.get(name_key) for s in steps]}"
    )
    return matches[0]


def _gh_step(needle: str) -> dict:
    return _find_step(_gh_steps(), "name", needle)


def _ado_step(needle: str) -> dict:
    return _find_step(_ado_steps(), "displayName", needle)


# ---------------------------------------------------------------------------
# Schema-specific mistakes a generic YAML linter does not catch
# ---------------------------------------------------------------------------


def test_both_files_parse_as_yaml() -> None:
    """The baseline a linter WOULD catch — kept anyway so a future edit that
    breaks basic syntax fails here with a clear message instead of surfacing
    three tests down as a confusing KeyError."""
    gh = _load(_GH_PATH)
    ado = _load(_ADO_PATH)
    assert isinstance(gh, dict) and isinstance(ado, dict)


def test_the_on_key_survives_as_a_string_not_a_boolean() -> None:
    """Regression pin for the defect found while building this file.

    Measured before the fix: `yaml.safe_load(...)` on the original unquoted
    `on:` returned a dict with key `True` (a `bool`), not `"on"` (a `str`) —
    because YAML 1.1 resolves the bare words `on`/`off`/`yes`/`no` as
    booleans, and PyYAML's `SafeLoader` (like most general-purpose YAML
    tooling) follows that spec. GitHub's own parser tolerates the unquoted
    form, which is exactly why this kind of mistake survives unnoticed: it
    never breaks the one consumer anyone tests against.
    """
    gh = _load(_GH_PATH)
    assert "on" in gh, f"expected a string key 'on', got keys: {list(gh.keys())}"
    assert True not in gh, "the 'on' key is still parsing as the boolean True"


def test_checkout_is_the_first_step_in_both_files() -> None:
    """Missing-checkout is the specific schema mistake named in the brief:
    every later step assumes the repo is already on disk."""
    gh_first = _gh_steps()[0]
    assert "actions/checkout" in str(gh_first.get("uses", "")), gh_first

    ado_first = _ado_steps()[0]
    assert ado_first.get("checkout") == "self", ado_first


def test_full_history_is_fetched_in_both_files() -> None:
    """`fetch-depth: 0` / `fetchDepth: 0` — a shallow clone would silently
    break any gate a team adds later that diffs against a base branch."""
    gh_first = _gh_steps()[0]
    assert gh_first["with"]["fetch-depth"] == 0, gh_first

    ado_first = _ado_steps()[0]
    assert ado_first["fetchDepth"] == 0, ado_first


def test_runs_on_and_pool_name_a_real_hosted_runner() -> None:
    gh = _load(_GH_PATH)
    assert gh["jobs"]["gates"]["runs-on"] == "ubuntu-latest"

    ado = _load(_ADO_PATH)
    assert ado["pool"]["vmImage"] == "ubuntu-latest"


def test_the_six_gate_names_match_between_the_two_files_in_order() -> None:
    """The header comment in `azure-pipelines.yml` promises "the same gates,
    only the syntax differs" — this is what makes that promise checkable
    instead of aspirational."""
    gh_names = [s.get("name") for s in _gh_steps()[1:]]  # [0] is checkout, unnamed
    ado_names = [s.get("displayName") for s in _ado_steps()[1:]]
    assert gh_names == ado_names
    assert len(gh_names) == 6, gh_names


# ---------------------------------------------------------------------------
# Gate 1 — the approval-registry check. Executed for real: clean, forged, and
# matching-registry inputs. This inline ~40-line Python script exists ONLY in
# the two YAML files (it is not delegated to a checked-in script), so nothing
# else in this repo's test suite has ever run it.
# ---------------------------------------------------------------------------


def test_gate_1_scripts_are_byte_identical() -> None:
    """Regression pin for the second defect: after renaming the GitHub side's
    shell variable from `$REGISTRY` to `$APPROVAL_REGISTRY`, the two files run
    the exact same check, not two checks that happen to agree today."""
    gh_run = _gh_step("มีคีย์ในทะเบียน")["run"]
    ado_script = _ado_step("มีคีย์ในทะเบียน")["script"]
    assert gh_run.strip() == ado_script.strip()


def _extract_gate_1_script(tmp_path: Path) -> Path:
    """The Gate 1 shell body, written to a runnable file. Both CI files carry
    the identical text (pinned above), so either source works."""
    body = _gh_step("มีคีย์ในทะเบียน")["run"]
    script = tmp_path / "gate1.sh"
    script.write_text(body, encoding="utf-8")
    return script


def _run_gate_1(
    tmp_path: Path, doc_root: Path, registry_content: str
) -> subprocess.CompletedProcess[str]:
    script = _extract_gate_1_script(tmp_path)
    # Inherit the real environment (so `python3` resolves whatever PATH this
    # test process has) and override only the one variable Gate 1 reads.
    env = {**os.environ, "APPROVAL_REGISTRY": registry_content}
    return subprocess.run(
        ["bash", str(script)],
        cwd=doc_root,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def test_gate_1_passes_when_no_document_declares_an_approval(tmp_path: Path) -> None:
    (tmp_path / "doc" / "specs").mkdir(parents=True)
    (tmp_path / "doc" / "specs" / "SPEC-quiet.md").write_text(
        "Status: Draft\n\nnothing to see here\n", encoding="utf-8"
    )

    result = _run_gate_1(tmp_path, tmp_path, registry_content="")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "ทุกเอกสารที่อนุมัติแล้วมีคีย์รองรับครบ" in result.stdout


def test_gate_1_goes_red_naming_the_forged_file_and_key(tmp_path: Path) -> None:
    """The core claim SETUP.md makes about this gate: a document that claims
    an approval key nobody registered makes CI fail, by name.

    Measured directly (not just via this test): running this exact extracted
    script against a real forged document in a scratch worktree produced
    `exit 1` with stderr naming
    `doc/specs/SPEC-forged-example.md` and the key
    `forged-key-that-does-not-exist-2026-08-12` — reproduced here as an
    automated, permanent regression.
    """
    specs = tmp_path / "doc" / "specs"
    specs.mkdir(parents=True)
    (specs / "SPEC-forged-example.md").write_text(
        "Status: Approved\n"
        "Approval: forged-key-that-does-not-exist-2026-08-12\n\n"
        "## Approval history\n",
        encoding="utf-8",
    )

    result = _run_gate_1(tmp_path, tmp_path, registry_content="")

    assert result.returncode == 1, result.stdout + result.stderr
    assert "doc/specs/SPEC-forged-example.md" in result.stderr
    assert "forged-key-that-does-not-exist-2026-08-12" in result.stderr


def test_gate_1_passes_when_the_registry_has_a_matching_entry(tmp_path: Path) -> None:
    specs = tmp_path / "doc" / "specs"
    specs.mkdir(parents=True)
    (specs / "SPEC-real.md").write_text(
        "Status: Approved\nApproval: spec-real-2026-08-12\n\n## Approval history\n",
        encoding="utf-8",
    )
    registry_line = json.dumps(
        {
            "key": "spec-real-2026-08-12",
            "artifact": "doc/specs/SPEC-real.md",
            "status": "Approved",
            "approved_by": "test",
            "approved_at": "2026-08-12T00:00:00+00:00",
        }
    )

    result = _run_gate_1(tmp_path, tmp_path, registry_content=registry_line + "\n")

    assert result.returncode == 0, result.stdout + result.stderr


def test_gate_1_ignores_templates_and_framework_directories(tmp_path: Path) -> None:
    """`doc/templates/` and `doc/framework/` carry `Status:` lines by design
    (they are templates, or `Status: Living`) and must never be treated as
    approval claims — this is the same exclusion `scripts/approve.py` and
    `scripts/verify_approvals.py` apply, checked here against the THIRD, inline
    copy of the rule that lives only in the YAML."""
    templates = tmp_path / "doc" / "templates"
    templates.mkdir(parents=True)
    (templates / "spec.md").write_text(
        "Status: Approved\nApproval: whatever-not-real\n", encoding="utf-8"
    )
    framework = tmp_path / "doc" / "framework"
    framework.mkdir(parents=True)
    (framework / "NORTH-STAR.md").write_text("Status: Living\n", encoding="utf-8")

    result = _run_gate_1(tmp_path, tmp_path, registry_content="")

    assert result.returncode == 0, result.stdout + result.stderr


# ---------------------------------------------------------------------------
# Gate 3 — no leftover placeholders. Executed for real against this repo's
# ACTUAL current state (red, because it has not been bootstrapped — this
# template repo IS its own "fresh clone") and again after running
# `scripts/bootstrap.sh` on a scratch copy (green) — proving the sequencing
# `doc/framework/SETUP.md` documents (bootstrap, THEN wire CI) is not just
# asserted but actually holds.
# ---------------------------------------------------------------------------


def _extract_gate_3_script(tmp_path: Path) -> Path:
    body = _gh_step("ไม่มีตัวยึดหลงเหลือ")["run"]
    script = tmp_path / "gate3.sh"
    script.write_text(body, encoding="utf-8")
    return script


def test_gate_3_scripts_are_byte_identical_between_the_two_files() -> None:
    gh_run = _gh_step("ไม่มีตัวยึดหลงเหลือ")["run"]
    ado_script = _ado_step("ไม่มีตัวยึดหลงเหลือ")["script"]
    assert gh_run.strip() == ado_script.strip()


_BOOTSTRAP_INPUT = "Acme Portal\nacme\n/tmp/acme-backend\n/tmp/acme-frontend\n"


def _run_bootstrap(repo: Path, tmp_path: Path) -> subprocess.CompletedProcess[str]:
    """Run `scripts/bootstrap.sh` in `repo` with HOME pointed at a scratch dir.

    Bootstrap ends with `mkdir -p ~/.jarvis/approvals && touch .../registry.jsonl`;
    run with the real HOME, every test here moved the owner's real approval
    registry's mtime without writing an approval (D8). Every bootstrap run in
    this module goes through here — `test_bootstrap_runs_only_through_the_isolating_helper`
    pins that."""
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    return subprocess.run(
        ["bash", "scripts/bootstrap.sh"],
        cwd=repo,
        input=_BOOTSTRAP_INPUT,
        capture_output=True,
        text=True,
        env={**os.environ, "HOME": str(home)},
        timeout=30,
    )


def test_bootstrap_in_these_tests_never_touches_the_real_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """D8: stand a sentinel in for the owner's HOME, run bootstrap the way
    these tests do, and require the sentinel untouched — while the registry
    still lands in the helper's scratch HOME, so bootstrap really reached
    the line that writes it."""
    sentinel_home = tmp_path / "sentinel-home"
    sentinel_home.mkdir()
    monkeypatch.setenv("HOME", str(sentinel_home))
    repo = tmp_path / "repo"
    (repo / "scripts").mkdir(parents=True)
    shutil.copy2(_BOOTSTRAP, repo / "scripts" / "bootstrap.sh")
    (repo / "AGENTS.md").write_text("name <PROJECT>\n", encoding="utf-8")

    result = _run_bootstrap(repo, tmp_path)

    assert result.returncode == 0, result.stdout + result.stderr
    assert list(sentinel_home.iterdir()) == [], "bootstrap wrote under the real HOME"
    assert (tmp_path / "home" / ".jarvis" / "approvals" / "registry.jsonl").is_file()


def test_bootstrap_runs_only_through_the_isolating_helper() -> None:
    """A future test that calls bootstrap directly would reopen D8 silently,
    so the module may spell the bootstrap command exactly once: in the helper."""
    needle = '["bash", ' + '"scripts/bootstrap.sh"]'  # split so this line is not a match
    assert Path(__file__).read_text(encoding="utf-8").count(needle) == 1


#: Every path Gate 3 skips, in the exact `grep -v` form both CI files and
#: `scripts/bootstrap.sh` must spell it.
_GATE_3_EXCLUSIONS = (
    "doc/framework/",
    "doc/templates/",
    "scripts/bootstrap.sh",
    r"^\.claude/worktrees/",
)


def test_gate_3_exclusions_match_bootstraps_own_leftover_check(tmp_path: Path) -> None:
    """`scripts/bootstrap.sh` runs the identical grep, with the identical
    exclusions, to report what IT left unfilled. If a future edit adds an
    excluded directory to one and not the other, bootstrap would call a
    placeholder "filled" that CI would still fail on, or vice versa — this
    is the drift this test exists to catch.

    The textual match alone does not prove bootstrap's *substitution* skips
    agent worktrees too, so the second half runs bootstrap on a scratch copy:
    a placeholder inside `.claude/worktrees/` is neither rewritten nor
    reported, while real files beside it (including one merely named
    `worktrees-…`) still are."""
    gate3_body = _gh_step("ไม่มีตัวยึดหลงเหลือ")["run"]
    bootstrap_body = _BOOTSTRAP.read_text(encoding="utf-8")
    for excluded in _GATE_3_EXCLUSIONS:
        needle = f"grep -v '{excluded}'"
        assert needle in gate3_body, f"{needle!r} missing from the CI gate"
        assert needle in bootstrap_body, f"{needle!r} missing from bootstrap.sh"
    assert gate3_body.count("grep -v '") == len(_GATE_3_EXCLUSIONS), (
        "CI gate 3 has an exclusion this test does not list"
    )

    repo = tmp_path / "repo"
    shutil.copytree(
        _REPO_ROOT,
        repo,
        ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache", "*.pyc", "worktrees"),
    )
    worktree_file = repo / ".claude/worktrees/agent-x/doc/f.md"
    worktree_md = repo / ".claude/worktrees/agent-x/AGENTS.md"
    notes = repo / "doc/worktrees-notes.md"
    for path, text in (
        (worktree_file, "fixture <ABC_DEF>\n"),
        (worktree_md, "name <PROJECT>\n"),
        (notes, "leftover <ABC_DEF>\n"),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    result = _run_bootstrap(repo, tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert not re.search(r"^\s*\.claude/worktrees/", result.stdout, re.MULTILINE), result.stdout
    assert worktree_md.read_text(encoding="utf-8") == "name <PROJECT>\n"
    assert "doc/worktrees-notes.md:1:leftover <ABC_DEF>" in result.stdout
    assert "<PROJECT>" not in (repo / "AGENTS.md").read_text(encoding="utf-8")
    assert "Acme Portal" in (repo / "AGENTS.md").read_text(encoding="utf-8")


def test_gate_3_is_red_on_this_repos_own_current_state(tmp_path: Path) -> None:
    """This repo, right now, has not been bootstrapped — `<PROJECT>` still
    appears in `.claude/agents/*.md`. That is not a bug (`doc/framework/
    SETUP.md` puts bootstrapping as literal step 1, before CI is ever wired
    in), but it means Gate 3 is genuinely red on a template's own tree, which
    is worth pinning explicitly so nobody "fixes" it by loosening the grep.
    """
    script = _extract_gate_3_script(tmp_path)
    result = subprocess.run(
        ["bash", str(script)], cwd=_REPO_ROOT, capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 1, result.stdout + result.stderr
    assert "<PROJECT>" in result.stderr


def test_gate_3_is_green_after_bootstrap_runs(tmp_path: Path) -> None:
    """The complement: once `scripts/bootstrap.sh` has filled the placeholders
    it owns, Gate 3 passes — proving the two scripts actually agree in
    practice, not just in the exclusion list compared above."""
    repo_copy = tmp_path / "repo"
    shutil.copytree(
        _REPO_ROOT,
        repo_copy,
        ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache", "*.pyc"),
    )

    bootstrap_result = _run_bootstrap(repo_copy, tmp_path)
    assert bootstrap_result.returncode == 0, bootstrap_result.stdout + bootstrap_result.stderr

    script = _extract_gate_3_script(tmp_path)
    result = subprocess.run(
        ["bash", str(script)], cwd=repo_copy, capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, (
        "gate 3 still red after bootstrap:\n" + result.stdout + result.stderr
    )
    assert "ไม่มีตัวยึดหลงเหลือ" in result.stdout


def _bootstrapped_copy_with(tmp_path: Path, extra: dict[str, str]) -> Path:
    """A bootstrapped scratch copy of this repo plus `extra` files
    (relative path -> content), ready for Gate 3 to scan."""
    repo_copy = tmp_path / "repo"
    shutil.copytree(
        _REPO_ROOT,
        repo_copy,
        ignore=shutil.ignore_patterns(
            ".git", "__pycache__", ".pytest_cache", "*.pyc", "worktrees"
        ),
    )
    bootstrap_result = _run_bootstrap(repo_copy, tmp_path)
    assert bootstrap_result.returncode == 0, bootstrap_result.stdout + bootstrap_result.stderr
    for rel, content in extra.items():
        target = repo_copy / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    return repo_copy


def _run_gate_3(tmp_path: Path, repo: Path) -> subprocess.CompletedProcess[str]:
    script = _extract_gate_3_script(tmp_path)
    return subprocess.run(
        ["bash", str(script)], cwd=repo, capture_output=True, text=True, timeout=30
    )


def test_gate_3_ignores_an_agent_worktree_under_dot_claude(tmp_path: Path) -> None:
    """An isolated agent worktree lives at `.claude/worktrees/<name>/` — an
    untracked copy of the repo that may hold test fixtures with upper-case
    placeholders. It is not part of the project, so Gate 3 must not go red
    on it (same skip as `_WORKTREES` in scripts/check_neutrality.py)."""
    repo = _bootstrapped_copy_with(
        tmp_path, {".claude/worktrees/agent-x/doc/f.md": "fixture <ABC_DEF>\n"}
    )
    result = _run_gate_3(tmp_path, repo)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "ไม่มีตัวยึดหลงเหลือ" in result.stdout


@pytest.mark.parametrize(
    "rel",
    [
        ".claude/agents/x.md",
        "doc/x.md",
        "doc/worktrees-notes.md",
        "doc/.claude/worktrees/x.md",
        ".claude/worktreesX/x.md",
        ".claude/worktrees.md",
    ],
)
def test_gate_3_still_scans_real_paths_next_to_a_worktree(tmp_path: Path, rel: str) -> None:
    """The worktree skip must not widen: a placeholder in a real path — even
    one whose name merely contains `worktrees`, contains `.claude/worktrees/`
    below the repo root, or starts with `.claude/worktrees` without the `/` —
    is still red. Pins the `^` anchor and the trailing `/` of the filter."""
    repo = _bootstrapped_copy_with(
        tmp_path,
        {
            ".claude/worktrees/agent-x/doc/f.md": "fixture <ABC_DEF>\n",
            rel: "leftover <ABC_DEF>\n",
        },
    )
    result = _run_gate_3(tmp_path, repo)
    assert result.returncode == 1, result.stdout + result.stderr
    assert f"{rel}:1:leftover <ABC_DEF>" in result.stderr
    assert "agent-x" not in result.stderr


def test_gate_3_still_reports_a_real_file_whose_content_mentions_a_worktree(
    tmp_path: Path,
) -> None:
    """The filter matches the path at the start of grep's output line, not the
    content after it: a real file whose placeholder line also mentions
    `.claude/worktrees/` must still be reported. Pins the `^` anchor."""
    repo = _bootstrapped_copy_with(
        tmp_path,
        {
            ".claude/worktrees/agent-x/doc/f.md": "fixture <ABC_DEF>\n",
            "doc/x.md": "leftover <ABC_DEF> see .claude/worktrees/\n",
        },
    )
    result = _run_gate_3(tmp_path, repo)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "doc/x.md:1:leftover <ABC_DEF> see .claude/worktrees/" in result.stderr
    assert "agent-x" not in result.stderr


_PRE_COMMIT = _REPO_ROOT / ".githooks" / "pre-commit"


def _hook_gate_3_drift(hook: str) -> list[str]:
    """Every way the pre-commit hook's placeholder scan differs from CI gate 3
    (pattern, roots, `grep -v` list) and from bootstrap's substitution keys
    (the hook's template-mode `allowed=` list). Empty when they agree."""
    gate3 = _gh_step("ไม่มีตัวยึดหลงเหลือ")["run"]
    shape = re.search(r"grep -rn ('[^']+') (.+?) 2>/dev/null", gate3)
    assert shape, "CI gate 3's grep line changed shape: " + gate3
    pattern, roots = shape.groups()
    problems = []
    if pattern not in hook:
        problems.append(f"the hook does not hold CI's pattern {pattern}")
    if roots not in hook:
        problems.append(f"the hook does not hold CI's roots {roots!r}")
    hook_exclusions = re.findall(r"grep -v '([^']*)'", hook)
    for missing in [e for e in _GATE_3_EXCLUSIONS if e not in hook_exclusions]:
        problems.append(f"exclusion {missing!r} is missing from the hook")
    for extra in [e for e in hook_exclusions if e not in _GATE_3_EXCLUSIONS]:
        problems.append(f"the hook has exclusion {extra!r}, which CI gate 3 does not")
    filters = hook.count("grep -v '")
    if filters != len(_GATE_3_EXCLUSIONS):
        problems.append(f"the hook has {filters} grep -v filters, "
                        f"CI gate 3 has {len(_GATE_3_EXCLUSIONS)}")
    allowed = re.search(r"^allowed='([^']*)'$", hook, re.MULTILINE)
    hook_tokens = set(allowed.group(1).split("|")) if allowed else set()
    if not allowed:
        problems.append("the hook has no allowed='...' template-mode token list")
    subs = set(re.findall(r"^\s*'<([A-Z_]+)>':", _BOOTSTRAP.read_text(encoding="utf-8"),
                          re.MULTILINE))
    assert subs, "bootstrap.sh's subs table changed shape"
    for extra in sorted(hook_tokens - subs):
        problems.append(f"the hook allows {extra}, which bootstrap does not substitute")
    for missing in sorted(subs - hook_tokens):
        problems.append(f"bootstrap substitutes {missing}, which the hook does not allow")
    return problems


def test_pre_commit_placeholder_scan_equals_ci_gate_3_and_bootstrap() -> None:
    """AM3-AC20: one list (`_GATE_3_EXCLUSIONS`) governs CI, bootstrap and the
    pre-commit hook; the hook's allowed tokens are exactly bootstrap's keys."""
    assert _hook_gate_3_drift(_PRE_COMMIT.read_text(encoding="utf-8")) == []


@pytest.mark.parametrize(
    ("plant", "named"),
    [
        (lambda h: h + "\n  | grep -v 'doc/extra/'\n", "'doc/extra/'"),
        (lambda h: h.replace("grep -v 'doc/templates/'", ""), "'doc/templates/'"),
        (lambda h: h.replace("allowed='", "allowed='SIXTH|", 1), "SIXTH"),
    ],
    ids=["extra-exclusion", "missing-exclusion", "sixth-allowed-token"],
)
def test_the_drift_helper_names_a_planted_difference(plant, named: str) -> None:
    hook = _PRE_COMMIT.read_text(encoding="utf-8")
    planted = plant(hook)
    assert planted != hook, "the plant changed nothing — the hook text moved"
    problems = _hook_gate_3_drift(planted)
    assert any(named in p for p in problems), problems


# ---------------------------------------------------------------------------
# Gate 2 — the exit gate. The CI files run `./scripts/verify-full.sh` verbatim;
# proven here with the same stub-copy technique `tests/hooks/
# test_verify_scripts.py` uses, for the same reason (the real script's own
# steps run `pytest tests/hooks/ -q` and, as of this wave, `pytest tests/ci/
# -q` — running it unmodified from inside either suite would recurse).
# ---------------------------------------------------------------------------

_REAL_HOOK_STEP = '"hooks|python3 -m pytest tests/hooks/ -q"'
_REAL_CI_STEP = '"ci-examples|python3 -m pytest tests/ci/ -q"'
#: Added alongside the Scar Forge (Task B). The stub copy below carries only
#: the single script file, not a `tests/scars/` directory, so this step must
#: be neutralised too or the copy fails for a reason unrelated to Gate 2.
_REAL_SCAR_STEP = (
    '"scar-forge|python3 -m pytest tests/scars/ -q && python3 scripts/scar_status.py"'
)
_REAL_COORD_STEP = '"coordinator|python3 -m pytest tests/coordinator/ -q"'
_REAL_FRAMEWORK_STEP = (
    '"framework|python3 -m pytest tests/framework/ -q && python3 scripts/check_neutrality.py && python3 scripts/memory_lint.py"'
)


def test_gate_2_command_is_the_exit_gate_and_the_path_is_real_and_executable() -> None:
    # The last line runs the exit gate, after the base's gate code is checked out
    # (test_gate_2_takes_the_gate_code_from_the_base_branch).
    gh_run = _gh_step("ประตูออก")["run"].strip()
    ado_script = _ado_step("ประตูออก")["script"].strip()
    assert gh_run.splitlines()[-1].strip() == _EXIT_GATE_COMMAND
    assert ado_script.splitlines()[-1].strip() == _EXIT_GATE_COMMAND

    resolved = _REPO_ROOT / "scripts" / "verify-full.sh"
    assert resolved.is_file(), f"{_EXIT_GATE_COMMAND} does not exist at {resolved}"
    assert os.access(resolved, os.X_OK), f"{resolved} is not executable"


def test_gate_2_extracted_command_actually_runs(tmp_path: Path) -> None:
    """A stubbed copy of the real script, run with no arguments — exactly the
    invocation in both CI files. Only the two nested-pytest steps are
    replaced; every other line, including the placeholder/OK/FAIL/verdict
    logic, is the real file, byte for byte."""
    body = _FULL.read_text(encoding="utf-8")
    for old in (
        _REAL_HOOK_STEP, _REAL_CI_STEP, _REAL_SCAR_STEP, _REAL_COORD_STEP, _REAL_FRAMEWORK_STEP
    ):
        assert body.count(old) == 1, f"expected exactly one {old!r} in {_FULL}"
    body = body.replace(_REAL_HOOK_STEP, '"hooks|echo hooks ran"', 1)
    body = body.replace(_REAL_CI_STEP, '"ci-examples|echo ci-examples ran"', 1)
    body = body.replace(_REAL_SCAR_STEP, '"scar-forge|echo scar-forge ran"', 1)
    body = body.replace(
        _REAL_COORD_STEP, '"coordinator|echo coordinator-constitution ran"', 1
    )
    body = body.replace(_REAL_FRAMEWORK_STEP, '"framework|echo framework ran"', 1)

    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    probe = scripts_dir / "verify-full.sh"
    probe.write_text(body, encoding="utf-8")
    recorder = _REPO_ROOT / "scripts" / "verify_record.py"
    (scripts_dir / recorder.name).write_text(recorder.read_text(encoding="utf-8"), encoding="utf-8")

    result = subprocess.run(
        ["bash", str(probe)], capture_output=True, text=True, timeout=60, check=False
    )

    assert result.returncode == 0, result.stdout + result.stderr
    # lint/format/tests are still real TODO placeholders in this template —
    # so INCOMPLETE, not GREEN, is the honest verdict for THIS repo today.
    assert "EXIT GATE INCOMPLETE" in result.stdout, result.stdout


def _git_ci(cwd: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True,
                          check=True).stdout.strip()


def _gate_2_clone(tmp_path: Path) -> Path:
    """A CI checkout of a candidate branch whose gate code differs from its base:
    the base's verify-full.sh prints BASE GATE, the candidate's prints CANDIDATE
    GATE, and the candidate adds a verify.conf the base does not have."""
    origin = tmp_path / "origin.git"
    _git_ci(tmp_path, "init", "-q", "--bare", str(origin))
    work = tmp_path / "work"
    _git_ci(tmp_path, "clone", "-q", str(origin), str(work))
    for k, v in (("user.name", "t"), ("user.email", "t@example.invalid")):
        _git_ci(work, "config", k, v)
    _git_ci(work, "symbolic-ref", "HEAD", "refs/heads/main")
    scripts = work / "scripts"
    scripts.mkdir()
    gate = scripts / "verify-full.sh"
    gate.write_text("#!/usr/bin/env bash\necho BASE GATE\n", encoding="utf-8")
    gate.chmod(0o755)
    (scripts / "verify_record.py").write_text("# base recorder\n", encoding="utf-8")
    _git_ci(work, "add", "-A")
    _git_ci(work, "commit", "-q", "-m", "base")
    _git_ci(work, "push", "-q", "origin", "main")
    _git_ci(work, "checkout", "-q", "-b", "candidate")
    gate.write_text("#!/usr/bin/env bash\necho CANDIDATE GATE\n", encoding="utf-8")
    (scripts / "verify.conf").write_text("VERIFY_MERGE_GATE=runner\n", encoding="utf-8")
    _git_ci(work, "add", "-A")
    _git_ci(work, "commit", "-q", "-m", "candidate rewrites the gate")
    _git_ci(work, "checkout", "-q", "--detach")  # CI checks out a commit, not a branch
    # The runner's clone knows nothing of the base yet; gate 2 must fetch it.
    _git_ci(work, "update-ref", "-d", "refs/remotes/origin/main")
    return work


def _gate_2_script(which: str) -> tuple[str, dict[str, str]]:
    if which == "github":
        step = _gh_step("ประตูออก")
        # Emulates the expression GitHub evaluates; empty on a push build.
        assert step.get("env", {}).get("BASE_BRANCH") == "${{ github.base_ref || 'main' }}"
        return step["run"], {"BASE_BRANCH": "main"}
    if which == "azure-pr":
        return _ado_step("ประตูออก")["script"], {"SYSTEM_PULLREQUEST_TARGETBRANCH": "refs/heads/main"}
    return _ado_step("ประตูออก")["script"], {}  # a push build: no PR target branch


@pytest.mark.parametrize("which", ["github", "azure-pr", "azure-push"])
def test_gate_2_takes_the_gate_code_from_the_base_branch(tmp_path: Path, which: str) -> None:
    """R11: the runner must not judge a candidate with gate code the candidate
    wrote. Gate 2 runs the base's verify-full.sh, with the base's recorder and
    conf, and says so when the candidate changed them."""
    work = _gate_2_clone(tmp_path)
    body, env = _gate_2_script(which)
    script = tmp_path / "gate2.sh"
    script.write_text(body, encoding="utf-8")
    run_env = {k: v for k, v in os.environ.items() if k != "SYSTEM_PULLREQUEST_TARGETBRANCH"}
    result = subprocess.run(["bash", str(script)], cwd=work, capture_output=True, text=True,
                            timeout=60, check=False, env={**run_env, **env})
    out = result.stdout + result.stderr
    assert result.returncode == 0, out
    assert "BASE GATE" in result.stdout and "CANDIDATE GATE" not in result.stdout, out
    assert ("note: this candidate changes the gate code — judged with origin/main's copy; "
            "review the gate diff") in result.stdout, out
    assert not (work / "scripts" / "verify.conf").exists(), "the candidate's conf was not removed"
    assert (work / "scripts" / "verify_record.py").read_text(encoding="utf-8") == "# base recorder\n"


# ---------------------------------------------------------------------------
# Gate 4 — deliberately NOT executed. See the module docstring for why.
# ---------------------------------------------------------------------------


def test_gate_4_command_matches_the_string_the_exit_gate_itself_runs() -> None:
    """The only proof this step gets: its text cannot drift from the text
    `scripts/verify-full.sh` runs for the same purpose, without this test
    naming exactly where the three disagree."""
    gh_run = _gh_step("เทสต์ hook")["run"].strip()
    ado_script = _ado_step("เทสต์ hook")["script"].strip()
    assert gh_run == _HOOKS_TEST_COMMAND
    assert ado_script == _HOOKS_TEST_COMMAND

    gate_body = _FULL.read_text(encoding="utf-8")
    assert _HOOKS_TEST_COMMAND in gate_body, (
        f"{_HOOKS_TEST_COMMAND!r} no longer appears in {_FULL} — Gate 4 in both "
        f"CI files would now test a command the exit gate itself does not run"
    )


# ---------------------------------------------------------------------------
# The stale-path check the brief asked for explicitly: every script path
# either CI file names must exist in THIS repo, post wave-1's renames.
# ---------------------------------------------------------------------------


def test_every_script_path_named_in_either_ci_file_exists() -> None:
    """Catches exactly the failure mode named in the brief: a path that was
    correct until wave 1 renamed something under `scripts/` and this example
    was never updated to match."""
    for source_path in (_GH_PATH, _ADO_PATH):
        text = source_path.read_text(encoding="utf-8")
        for raw_line in text.splitlines():
            for token in raw_line.replace("./", " ").split():
                token = token.strip("`\"'")
                if not token.startswith("scripts/"):
                    continue
                token = token.rstrip(".,;")  # sentence or shell punctuation
                candidate = _REPO_ROOT / token
                if token == "scripts/verify.conf":
                    # A project's own file, made from the committed example (SETUP §6).
                    candidate = _REPO_ROOT / "scripts" / "verify.conf.example"
                assert candidate.is_file(), (
                    f"{token!r} named in {source_path.name} does not exist at {candidate}"
                )


# ---------------------------------------------------------------------------
# Gate 6 — the decision log only grows at the end (SPEC-delegated-autonomy-am2
# AM2-AC2). The same script in both files, run for real against a clone whose
# base branch moved on after the candidate forked.
# ---------------------------------------------------------------------------

_LOG_STEP = "บันทึกการตัดสินใจต่อท้ายได้อย่างเดียว"
_DECISION_LOG = "doc/decisions/decision-log.jsonl"


def test_gate_6_scripts_are_byte_identical() -> None:
    gh_run = _gh_step(_LOG_STEP)["run"]
    ado_script = _ado_step(_LOG_STEP)["script"]
    assert gh_run == ado_script
    assert "scripts/autonomy.py verify-log --append-only" in gh_run


def _write_log(work: Path, lines: list[str]) -> None:
    path = work / _DECISION_LOG
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(f"{line}\n" for line in lines), encoding="utf-8")
    _git_ci(work, "add", "-A")
    _git_ci(work, "commit", "-q", "-m", "log")


def _gate_6_clone(tmp_path: Path, candidate: list[str]) -> Path:
    """main holds three log lines; the candidate forks and writes `candidate`;
    main then gains a fourth line the candidate never saw."""
    origin = tmp_path / "origin.git"
    _git_ci(tmp_path, "init", "-q", "--bare", str(origin))
    work = tmp_path / "work"
    _git_ci(tmp_path, "clone", "-q", str(origin), str(work))
    for k, v in (("user.name", "t"), ("user.email", "t@example.invalid")):
        _git_ci(work, "config", k, v)
    _git_ci(work, "symbolic-ref", "HEAD", "refs/heads/main")
    (work / "scripts").mkdir()
    for name in ("autonomy.py", "verify_approvals.py"):
        shutil.copy(_REPO_ROOT / "scripts" / name, work / "scripts" / name)
    _write_log(work, ['{"id": "a"}', '{"id": "b"}', '{"id": "c"}'])
    _git_ci(work, "checkout", "-q", "-b", "candidate")
    _write_log(work, candidate)
    _git_ci(work, "checkout", "-q", "main")
    _write_log(work, ['{"id": "a"}', '{"id": "b"}', '{"id": "c"}', '{"id": "main-only"}'])
    _git_ci(work, "push", "-q", "origin", "main")
    _git_ci(work, "checkout", "-q", "--detach", "candidate")
    _git_ci(work, "update-ref", "-d", "refs/remotes/origin/main")  # the step must fetch it
    return work


def _run_gate_6(tmp_path: Path, work: Path, which: str) -> subprocess.CompletedProcess[str]:
    body = _gh_step(_LOG_STEP)["run"] if which == "github" else _ado_step(_LOG_STEP)["script"]
    env = {k: v for k, v in os.environ.items() if k not in ("GITHUB_BASE_REF", "SYSTEM_PULLREQUEST_TARGETBRANCH")}
    env["HOME"] = str(tmp_path / "home")
    env["APPROVAL_LOG"] = str(tmp_path / "registry.jsonl")
    if which == "github":
        env["GITHUB_BASE_REF"] = "main"
    elif which == "azure-pr":
        env["SYSTEM_PULLREQUEST_TARGETBRANCH"] = "refs/heads/main"
    script = tmp_path / "gate6.sh"
    script.write_text(body, encoding="utf-8")
    return subprocess.run(["bash", str(script)], cwd=work, capture_output=True, text=True,
                          timeout=60, check=False, env=env)


@pytest.mark.parametrize("which", ["github", "azure-pr", "azure-push"])
def test_gate_6_is_green_on_an_append_although_the_base_moved_on(tmp_path: Path, which: str) -> None:
    work = _gate_6_clone(tmp_path, ['{"id": "a"}', '{"id": "b"}', '{"id": "c"}', '{"id": "d"}'])
    result = _run_gate_6(tmp_path, work, which)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("which", ["github", "azure-pr", "azure-push"])
def test_gate_6_is_red_naming_the_line_when_an_earlier_line_changed(tmp_path: Path, which: str) -> None:
    work = _gate_6_clone(tmp_path, ['{"id": "a"}', '{"id": "B"}', '{"id": "c"}', '{"id": "d"}'])
    result = _run_gate_6(tmp_path, work, which)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "line 2" in result.stderr, result.stderr
