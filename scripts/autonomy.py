#!/usr/bin/env python3
"""The always-human list and its shared checks (SPEC-delegated-autonomy, increment B).

WHY THIS EXISTS. Delegated autonomy lets the assistant proceed without stopping
at every owner gate. Some decisions must never be delegated, whatever the
mandate says: business rules, security and personal data, anything irreversible
or outward-facing, spending, and the assistant's own authority. This module is
the single definition of that list. The interception guards and the commit-time
check import it; they never copy it, so they cannot drift apart.

What it holds:

* `FRAMEWORK_ITEMS` — the five items (AH1-AH5) and their matchers.
* `load_config` — the project file `scripts/autonomy.json`. It can only ADD to
  the framework items; any attempt to remove or narrow one raises `ConfigError`.
* `command_matches` / `classify_command` — which items a shell command touches.
* `classify_artifact` — the derived decision class of a document plus its
  always-human touches. Unknown means `AH-UNSURE`, which counts as always-human.
* `status` / `is_active` — whether autonomy is active for this project.

CLI:
    python3 scripts/autonomy.py items          # the list, with project additions
    python3 scripts/autonomy.py status         # inactive | mandate <k> | order <k> | absence since <t>
    python3 scripts/autonomy.py check-commit --message-file F [--protect GLOB ...]

**Stated limits.** Command matching sees words at command position after
heredocs are dropped and quotes are parsed. Commands hidden inside a script,
`bash -c "..."` or `python -c` are not seen, and a project pattern only knows
the words it lists. The guards make such evasion tamper-evident, not
impossible; the commit-time check and CI are the backstop.

Plain stdlib, no AI required (layer 1).
"""

from __future__ import annotations

import argparse
import fnmatch
import importlib.util
import json
import os
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path


def _load_from_source(name: str, path: Path):  # noqa: ANN202 — returns a module
    """Load `path` as module `name` from its source text alone: never by name
    through `sys.path`, where a planted `scripts/<stdlib name>.py` or a
    `scripts/<name>/` package would win, and never through `__pycache__`,
    where a forged cache would stand in for the source. Registered before it
    runs, as `@dataclass` needs on Python 3.14."""
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    exec(compile(path.read_bytes(), str(path), "exec"), module.__dict__)  # noqa: S102 — our own file, by path
    return module


# Run as a script, Python puts this directory ahead of the stdlib, so the
# commit-msg hook runs this file with `-I`; the imports above are then safe too.
verify_approvals = _load_from_source("verify_approvals", Path(__file__).resolve().parent / "verify_approvals.py")

CONFIG_REL = "scripts/autonomy.json"
UNSURE = "AH-UNSURE"

#: Branches that are always protected; the project file can add more.
FRAMEWORK_PROTECTED_BRANCHES = ("main", "master")

#: The owner's commands. An agent running any of these is refused in every
#: project, autonomy or not (ADR-6): they write the human-only registry.
OWNER_SCRIPTS = frozenset(
    {
        "approve.sh",
        "approve.py",
        "delegate.sh",
        "revoke.sh",
        "override.sh",
        "away.sh",
        "evolve.sh",
        "release.sh",
    }
)
#: Flags with which an owner command writes nothing. `--help`/`-h`: argparse
#: exits before any write, wherever the flag sits in the argv.
READ_ONLY_FLAGS = frozenset({"--list", "--dry-run", "-n", "--help", "-h"})

#: Paths that define or enforce the assistant's authority (design §B.3). An
#: interception adapter adds its own wiring paths through `extra_protected`;
#: naming them here would tie this core file to one tool.
PROTECTED_PATHS = (
    "scripts/autonomy.json",
    "scripts/autonomy.py",
    "scripts/approve.py",
    "scripts/approve.sh",
    "scripts/verify_approvals.py",
    "scripts/delegate.sh",
    "scripts/revoke.sh",
    "scripts/override.sh",
    "scripts/away.sh",
    "scripts/evolve.sh",
    "scripts/release.sh",
    "scripts/check_neutrality.py",
    "doc/mandates/**",
    "doc/orders/**",
    "doc/decisions/**",
    "doc/evolution/ledger.jsonl",
    ".githooks/**",
    "ci-examples/**",
)

MATCHER_KINDS = ("class", "field", "path", "command")

FRAMEWORK_ITEMS: dict[str, dict] = {
    "AH1": {
        "title": "business rules and numbers",
        "class": ["business-rules"],
        "field": [
            "Decision-class touches business-rules",
            "a PRD or spec under autonomy with no Decision-class line -> AH-UNSURE",
        ],
        "path": [],
        "command": [],
    },
    "AH2": {
        "title": "security and personal data",
        "class": ["security", "personal-data"],
        "field": ["Decision-class touches security or personal-data"],
        "path": [],
        "command": [],
    },
    "AH3": {
        "title": "irreversible or outward-facing",
        "class": [],
        "field": [],
        "path": [],
        "command": [
            "git push <remote> <protected-branch>",
            "git push --delete / git push :<ref>",
            "git tag -d followed by git push",
            "git branch -D <protected-branch>",
            "git merge / git rebase while on a protected branch",
            "curl/wget sending data (-X POST|PUT|PATCH|DELETE, -d, --data*, -F, -T)",
            "scp/rsync to host:, ssh host, sendmail, mail",
            "rm -r/-f on a data path",
            "SQL DROP / TRUNCATE / DELETE FROM",
            "deploy patterns (project)",
            "outward patterns (project)",
        ],
    },
    "AH4": {
        "title": "spend beyond budget",
        "class": [],
        "field": [],
        "path": [],
        "command": ["spend patterns (project)"],
    },
    "AH5": {
        "title": "the mandate, this list, or their enforcement",
        "class": [],
        "field": [],
        "path": list(PROTECTED_PATHS),
        "command": [
            "owner-only scripts/approve.sh, approve.py and the owner wrappers",
            "owner-only shell write into the approval registry",
            "redirect, tee, sed -i, cp, mv or rm targeting a protected path",
            "autonomy.py with a subcommand it does not define",
        ],
    },
}

_LIST_KEYS = (
    "protected_branches",
    "data_globs",
    "deploy_dev_patterns",
    "deploy_prod_patterns",
    "spend_patterns",
    "outward_patterns",
)
_ALLOWED_KEYS = frozenset({"project", "extra", "evolution", *_LIST_KEYS})
_ITEM_ID = re.compile(r"^AH\d+$", re.IGNORECASE)


class ConfigError(ValueError):
    """The project file is unusable. The message names why."""


# --------------------------------------------------------------------------- config


def load_config(root: Path) -> dict:
    """The validated project file, or an empty config when the project has none.

    Raises `ConfigError` for anything that would remove or narrow a framework
    item: a `disable` key, a top-level item ID, an empty override, or a key
    this module does not know (an unknown key is a matcher nobody enforces).
    """
    path = root / CONFIG_REL
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ConfigError(f"{CONFIG_REL} is unreadable: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigError(f"{CONFIG_REL} must be a JSON object")

    for key, value in raw.items():
        if key.lower() == "disable":
            named = [str(v).upper() for v in (value if isinstance(value, list) else [value])]
            items = ", ".join(v for v in named if v in FRAMEWORK_ITEMS) or "AH?"
            raise ConfigError(f"{CONFIG_REL}: cannot remove framework item {items} ('disable')")
        if _ITEM_ID.match(key):
            raise ConfigError(
                f"{CONFIG_REL}: cannot remove framework item {key.upper()} "
                "(items are extended under 'extra', never redefined)"
            )
        if key not in _ALLOWED_KEYS:
            raise ConfigError(
                f"{CONFIG_REL}: unknown key '{key}' — the project file can only add to "
                "the framework items"
            )
    for key in _LIST_KEYS:
        value = raw.get(key, [])
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            raise ConfigError(f"{CONFIG_REL}: '{key}' must be a list of strings")
    if "protected_branches" in raw and not raw["protected_branches"]:
        raise ConfigError(
            f"{CONFIG_REL}: cannot remove framework item AH3 (empty 'protected_branches'; "
            f"{', '.join(FRAMEWORK_PROTECTED_BRANCHES)} stay protected — omit the key instead)"
        )
    extra = raw.get("extra", {})
    if not isinstance(extra, dict):
        raise ConfigError(f"{CONFIG_REL}: 'extra' must be an object keyed by item ID")
    for item, kinds in extra.items():
        if item not in FRAMEWORK_ITEMS:
            raise ConfigError(f"{CONFIG_REL}: 'extra' names unknown item '{item}'")
        if not isinstance(kinds, dict):
            raise ConfigError(f"{CONFIG_REL}: 'extra.{item}' must be an object")
        for kind, values in kinds.items():
            name = kind[:-1] if kind.endswith("s") else kind
            if name not in MATCHER_KINDS:
                raise ConfigError(f"{CONFIG_REL}: 'extra.{item}.{kind}' is not a matcher kind")
            if not isinstance(values, list) or not all(isinstance(v, str) for v in values):
                raise ConfigError(f"{CONFIG_REL}: 'extra.{item}.{kind}' must be a list of strings")
            if not values:
                raise ConfigError(
                    f"{CONFIG_REL}: cannot remove framework item {item} "
                    f"(empty override 'extra.{item}.{kind}')"
                )
    return raw


def _extra(config: dict, item: str, kind: str) -> list[str]:
    kinds = config.get("extra", {}).get(item, {})
    return list(kinds.get(kind, [])) + list(kinds.get(kind + "s", []))


def protected_branches(config: dict) -> set[str]:
    return set(FRAMEWORK_PROTECTED_BRANCHES) | set(config.get("protected_branches", []))


def protected_globs(config: dict, extra_protected: tuple[str, ...] = ()) -> list[str]:
    return [*PROTECTED_PATHS, *_extra(config, "AH5", "path"), *extra_protected]


def items_report(config: dict) -> str:
    """The list as `items` prints it: one heading per item, one line per matcher."""
    project_paths = {
        "AH3": list(config.get("data_globs", [])),
    }
    project_commands = {
        "AH3": [*config.get("deploy_prod_patterns", []), *config.get("deploy_dev_patterns", []),
                *config.get("outward_patterns", [])],
        "AH4": list(config.get("spend_patterns", [])),
    }
    lines: list[str] = []
    for item, spec in FRAMEWORK_ITEMS.items():
        lines.append(f"{item}  {spec['title']}")
        for kind in MATCHER_KINDS:
            for matcher in spec[kind]:
                lines.append(f"  {kind}: {matcher}")
            added = _extra(config, item, kind)
            if kind == "path":
                added = project_paths.get(item, []) + added
            if kind == "command":
                added = project_commands.get(item, []) + added
            for matcher in added:
                lines.append(f"  {kind}: {matcher} (project)")
        if item == "AH3":
            for branch in sorted(protected_branches(config)):
                lines.append(f"  branch: {branch}")
    return "\n".join(lines)


# --------------------------------------------------------------------------- paths


def _normalise(path: str) -> str:
    path = os.path.normpath(path).replace(os.sep, "/")
    return "" if path == "." else path


def path_matches(rel: str, glob: str) -> bool:
    """`data/**` matches `data`, `data/` and everything below it."""
    rel = _normalise(rel)
    if glob.endswith("/**"):
        base = glob[:-3]
        if rel == base or rel.startswith(base + "/"):
            return True
    return fnmatch.fnmatchcase(rel, glob)


def _casefold_matches(rel: str, glob: str) -> bool:
    """Case-folded: on a case-insensitive volume (the macOS default)
    `SCRIPTS/Autonomy.json` IS the protected file."""
    return path_matches(rel.casefold(), glob.casefold())


def is_protected(rel: str, config: dict, extra_protected: tuple[str, ...] = ()) -> bool:
    return any(_casefold_matches(rel, g) for g in protected_globs(config, extra_protected))


def _glob_base(glob: str) -> list[str]:
    """The leading path parts of `glob` that hold no wildcard."""
    parts: list[str] = []
    for part in glob.split("/"):
        if any(c in part for c in "*?["):
            break
        parts.append(part)
    return parts


def covers(rel: str, glob: str) -> bool:
    """Removing or moving `rel` takes files under `glob` with it: `rel` matches
    the glob, or is an ancestor of its fixed base (`.`, `scripts`, or a shell
    glob such as `*` that names one)."""
    rel, glob = _normalise(rel).casefold(), glob.casefold()
    if path_matches(rel, glob):
        return True
    if rel == "":
        return True
    base = _glob_base(glob)
    rel_parts = rel.split("/")
    if not base or len(rel_parts) > len(base):
        return False
    return all(fnmatch.fnmatchcase(b, r) for r, b in zip(rel_parts, base))


def repo_relatives(target: str, root: Path | None, cwd: Path | None) -> list[str]:
    """`target` relative to the project root, as written and as resolved through
    symlinks (a link named `cfg.json` may BE `scripts/autonomy.json`). Empty
    when both lie outside the root."""
    expanded = os.path.expanduser(target)
    if root is None:
        return [] if os.path.isabs(expanded) else [_normalise(expanded)]
    joined = os.path.join(os.path.realpath(cwd or Path.cwd()), expanded)
    bases = {str(root), os.path.realpath(root)}
    found: list[str] = []
    for path in (os.path.normpath(joined), os.path.realpath(joined)):
        for base in bases:
            try:
                rel = _normalise(str(Path(path).relative_to(base)))
            except ValueError:
                continue
            if rel not in found:
                found.append(rel)
    return found


# --------------------------------------------------------------------------- commands

_HEREDOC_PATTERN = re.compile(
    r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1.*?^\s*\2\s*$",
    re.DOTALL | re.MULTILINE,
)
_PUNCTUATION = ";&|()<>`\n"
_ENV_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
#: Programs that run the rest of their argv as a command: name -> (options that
#: take a separate value, positional words before the command). Matched by
#: basename, so `/usr/bin/env` is `env`.
_WRAPPERS: dict[str, tuple[frozenset[str], int]] = {
    "env": (frozenset({"-u", "--unset", "-C", "--chdir", "-S", "--split-string"}), 0),
    "exec": (frozenset({"-a"}), 0),
    "nohup": (frozenset(), 0),
    "time": (frozenset({"-o", "-f", "--output", "--format"}), 0),
    "sudo": (frozenset({"-u", "-g", "-h", "-p", "-C", "-D", "-r", "-t", "-T", "-U"}), 0),
    "doas": (frozenset({"-u", "-C"}), 0),
    "command": (frozenset(), 0),
    "builtin": (frozenset(), 0),
    "nice": (frozenset({"-n", "--adjustment"}), 0),
    "timeout": (frozenset({"-s", "--signal", "-k", "--kill-after"}), 1),
    "stdbuf": (frozenset({"-i", "-o", "-e"}), 0),
    "xargs": (
        frozenset({"-I", "-n", "-P", "-L", "-d", "-E", "-s", "-a", "--max-args", "--max-procs",
                   "--max-lines", "--delimiter", "--eof", "--max-chars", "--arg-file"}),
        0,
    ),
    "source": (frozenset(), 0),
    ".": (frozenset(), 0),
}
_INTERPRETERS = re.compile(r"^(bash|sh|zsh|dash|ksh|python(\d+(\.\d+)?)?)$")
#: Interpreter options whose value is the next word, not the script.
_INTERPRETER_VALUE_OPTIONS = frozenset({"-o", "+o", "-O", "+O", "--rcfile", "--init-file", "-W", "-X", "-Q"})
#: Programs that only read or list their arguments: naming an owner script to
#: one of these is a mention, not a run. Anything else that names one is
#: refused (fail closed); add a program here only if it cannot execute a file.
_READERS = frozenset(
    {
        "grep", "egrep", "fgrep", "rg", "ag", "ack", "cat", "less", "more", "head", "tail",
        "wc", "ls", "stat", "file", "diff", "cmp", "echo", "printf", "git", "sed", "awk",
        "shasum", "sha256sum", "md5", "md5sum", "test", "[", "realpath", "readlink",
        "basename", "dirname", "chmod", "shellcheck", "touch", "nl", "sort", "ruff",
    }
)
#: `find` reads unless one of these runs or deletes what it finds.
_FIND_ACTIONS = frozenset({"-exec", "-execdir", "-ok", "-okdir", "-delete"})
_SHELLS = re.compile(r"^(bash|sh|zsh|dash|ksh)$")
_SQL = re.compile(r"\b(DROP|TRUNCATE)\b|\bDELETE\s+FROM\b")
_SEND_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
_CURL_SEND_FLAGS = ("-d", "--data", "-F", "--form", "-T", "--upload-file", "--json")
#: curl short options that send data, and those that take a value (which ends
#: a combined cluster such as `-sd` or `-dfoo`).
_CURL_SEND_SHORT = frozenset("dFT")
_CURL_VALUE_SHORT = frozenset("AbCcDdEeFHKmoPQrTtUuwXxYyz")
_WGET_SEND_FLAGS = ("--post-data", "--post-file", "--body-data", "--body-file")
_REGISTRY_REFERENCE = re.compile(r"\$\{?APPROVAL_LOG\b")
_WRITE_COPY_PROGRAMS = frozenset({"cp", "ln", "install"})
#: git global options whose value is the next word.
_GIT_VALUE_OPTIONS = frozenset({"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--config-env",
                                "--super-prefix"})

#: Subcommands this CLI defines. Anything else run through autonomy.py is an
#: attempt to reach a capability this file does not grant (AH5).
AGENT_SUBCOMMANDS = ("items", "status", "check-commit")


@dataclass(frozen=True)
class Match:
    item: str  # AH1..AH5
    pattern: str  # what matched, for the refusal message
    scope: str  # "always" (owner-only) | "active" (only while autonomy is active)


def _tokens(command: str) -> list[str]:
    text = _HEREDOC_PATTERN.sub(" ", command)

    def lex(source: str) -> list[str]:
        lexer = shlex.shlex(source, posix=True, punctuation_chars=_PUNCTUATION)
        lexer.whitespace = " \t\r"
        lexer.whitespace_split = True
        lexer.commenters = ""  # `#` inside a word is not a comment; shlex disagrees
        return list(lexer)

    try:
        return lex(text)
    except ValueError:  # unbalanced quote — judge the words anyway
        return lex(text.replace("'", " ").replace('"', " "))


def _is_separator(token: str) -> bool:
    return bool(token) and all(c in ";&|()`\n" for c in token)


def _name(token: str) -> str:
    return token.rsplit("/", maxsplit=1)[-1]


def _strip_command_position(words: list[str]) -> list[str]:
    """Drop leading `VAR=value` words and wrappers (with their options and, for
    `timeout`, the duration) until the word that actually runs is first."""
    while words:
        if _ENV_ASSIGNMENT.match(words[0]):
            words = words[1:]
            continue
        spec = _WRAPPERS.get(_name(words[0]))
        if spec is None:
            return words
        takes_value, positionals = spec
        index = 1
        while index < len(words) and words[index].startswith("-") and len(words[index]) > 1:
            if words[index] == "--":
                index += 1
                break
            index += 2 if words[index] in takes_value else 1
        words = words[index + positionals :]
    return words


def segments(command: str) -> list[list[str]]:
    """Commands split at `; && || | & ( ) newline backtick`, each with leading
    `VAR=value` assignments and wrappers removed. Quoted text stays one word,
    so mentioning a command is never running it."""
    result: list[list[str]] = []
    current: list[str] = []
    for token in _tokens(command) + [";"]:
        if _is_separator(token):
            current = _strip_command_position(current)
            if current:
                result.append(current)
            current = []
        else:
            current.append(token)
    return result


def _split_redirects(tokens: list[str]) -> tuple[list[str], list[str]]:
    """(words, redirect targets). `2>&1` and `>&2` duplicate a descriptor and
    have no file target."""
    words: list[str] = []
    targets: list[str] = []
    skip = False
    for index, token in enumerate(tokens):
        if skip:
            skip = False
            continue
        if "<" in token or ">" in token:
            if ">" in token and not token.endswith("&") and index + 1 < len(tokens):
                targets.append(tokens[index + 1])
            skip = True
            continue
        words.append(token)
    return words, targets


def _effective(words: list[str]) -> list[str]:
    """`bash x.sh a` -> `x.sh a`; `python3 -u x.py` -> `x.py`. Other programs as-is."""
    if words and _INTERPRETERS.match(_name(words[0])):
        skip = False
        for index, token in enumerate(words[1:], start=1):
            if skip:
                skip = False
                continue
            if token == "-m":
                return words[index + 1 :]
            if token in _INTERPRETER_VALUE_OPTIONS:
                skip = True
                continue
            if not token.startswith(("-", "+")):
                return words[index:]
        return []
    return words


def _git_subcommand(words: list[str]) -> tuple[str, list[str]]:
    """(`push`, rest) for `git --no-pager -C x push …`: global options skipped."""
    args = words[1:]
    while args and args[0].startswith("-"):
        args = args[2:] if args[0] in _GIT_VALUE_OPTIONS else args[1:]
    return (args[0], args[1:]) if args else ("", [])


def _write_targets(words: list[str]) -> tuple[list[str], list[str]]:
    """(files written, files removed or moved away) by tee, sed -i, dd of=,
    cp/ln/install, mv, rm, `git rm` and `git mv`. A move's sources count as
    removed: moving a protected file away is as much a write to it as
    overwriting it."""
    if not words:
        return [], []
    program = _name(words[0])
    args = [w for w in words[1:] if not w.startswith("-")]
    if program == "tee":
        return args, []
    if program == "sed" and any(w == "--in-place" or re.match(r"^-[a-zA-Z]*i", w) for w in words[1:]):
        return args[1:], []
    if program == "dd":
        return [w[3:] for w in words[1:] if w.startswith("of=")], []
    if program in _WRITE_COPY_PROGRAMS or program == "mv":
        dest: list[str] = []
        for index, token in enumerate(words):
            if token in ("-t", "--target-directory") and index + 1 < len(words):
                dest = [words[index + 1]]
            elif token.startswith("--target-directory="):
                dest = [token.split("=", 1)[1]]
        sources = [a for a in args if a not in dest] if dest else args[:-1]
        dest = dest or args[-1:]
        return dest, sources if program == "mv" else []
    if program == "rm":
        return [], args
    if program == "git":
        sub, rest = _git_subcommand(words)
        positional = [a for a in rest if not a.startswith("-")]
        if sub == "rm":
            return [], positional
        if sub == "mv":
            return positional[-1:], positional[:-1]
    return [], []


def _is_registry_target(target: str, cwd: Path | None) -> bool:
    """The registry file or its directory — the default location AND the
    `$APPROVAL_LOG` override, since the hook's environment need not match the
    command's. Compared resolved (a symlink to the registry is the registry)
    and case-folded (a case-insensitive volume)."""
    if _REGISTRY_REFERENCE.search(target):
        return True
    expanded = Path(os.path.expanduser(os.path.expandvars(target)))
    if not expanded.is_absolute():
        expanded = (cwd or Path.cwd()) / expanded
    candidates = {os.path.normpath(str(expanded)).casefold(), os.path.realpath(expanded).casefold()}
    registries = {verify_approvals.registry_path().expanduser(), verify_approvals._DEFAULT_REGISTRY}
    for reg in registries | {Path(os.path.realpath(r)) for r in registries}:
        if candidates & {str(reg).casefold(), str(reg.parent).casefold()}:
            return True
    return False


def _only_checks(words: list[str]) -> bool:
    """`find` with no action that runs or deletes, `bash -n` (and the other
    shells) and `python -m py_compile`: each reads a script without running it."""
    program = _name(words[0])
    if program == "find":
        return not _FIND_ACTIONS.intersection(words[1:])
    if _SHELLS.match(program):
        skip = False
        for token in words[1:]:
            if skip:
                skip = False
            elif token == "-n":
                return True
            elif token in _INTERPRETER_VALUE_OPTIONS:
                skip = True
            elif not token.startswith(("-", "+")):
                return False
        return False
    return program.startswith("python") and _effective(words)[:1] == ["py_compile"]


def _owner_script(words: list[str]) -> str | None:
    """The owner script this segment runs, found by basename ANYWHERE in its
    argv (so a wrapper nobody listed still cannot hide it), unless the program
    only reads its arguments or a read-only flag follows the script. Tokens
    after the script's first `--` are operands, never flags."""
    effective = _effective(words)
    if not effective or _name(effective[0]) in _READERS or _only_checks(words):
        return None
    for index, token in enumerate(effective):
        if _name(token) in OWNER_SCRIPTS:
            args = effective[index + 1 :]
            options = args[: args.index("--")] if "--" in args else args
            if READ_ONLY_FLAGS.intersection(options):
                return None
            return _name(token)
    return None


def _pattern_hit(words: list[str], pattern: str) -> bool:
    """A project pattern is words: the first at command position (by basename),
    the rest in order anywhere after it."""
    wanted = pattern.split()
    effective = _effective(words) or words
    for candidate in (words, effective):
        if not candidate or not wanted:
            continue
        if candidate[0] != wanted[0] and _name(candidate[0]) != _name(wanted[0]):
            continue
        rest = iter(candidate[1:])
        if all(any(token == w for token in rest) for w in wanted[1:]):
            return True
    return False


def _git_matches(words: list[str], branches: set[str], current_branch: str | None) -> list[str]:
    sub, rest = _git_subcommand(words)
    if not sub:
        return []
    positional = [a for a in rest if not a.startswith("-")]
    hits: list[str] = []
    if sub == "push":
        if "--delete" in rest or "-d" in rest:
            hits.append("git push --delete")
        hits.extend(f"git push {flag}" for flag in ("--all", "--mirror") if flag in rest)
        for refspec in positional[1:]:
            if refspec.startswith(":"):
                hits.append(f"git push :{refspec[1:]}")
                continue
            dest = refspec.lstrip("+").split(":")[-1].removeprefix("refs/heads/")
            if dest in branches:
                hits.append(f"git push <remote> {dest}")
    elif sub == "branch" and ("-D" in rest or "--delete" in rest or "-d" in rest):
        hits.extend(f"git branch -D {b}" for b in positional if b in branches)
    elif sub in ("merge", "rebase") and current_branch in branches:
        hits.append(f"git {sub} while on {current_branch}")
    return hits


def _outward(words: list[str]) -> list[str]:
    program = _name(words[0])
    args = words[1:]
    if program == "curl":
        for index, token in enumerate(args):
            method = None
            if token == "--request" and index + 1 < len(args):
                method = args[index + 1]
            elif token.startswith("--request="):
                method = token.split("=", 1)[1]
            elif token.startswith("-") and not token.startswith("--"):
                # A short-option cluster: `-sd x`, `-dfoo`, `-sSXPOST`.
                for pos, flag in enumerate(token[1:], start=1):
                    if flag == "X":
                        method = token[pos + 1 :] or (args[index + 1] if index + 1 < len(args) else "")
                        break
                    if flag in _CURL_SEND_SHORT:
                        return [f"curl -{flag}"]
                    if flag in _CURL_VALUE_SHORT:
                        break
            if method and method.upper() in _SEND_METHODS:
                return [f"curl -X {method.upper()}"]
            if any(token == f or token.startswith(f + "=") or (f.startswith("--") and token.startswith(f))
                   for f in _CURL_SEND_FLAGS if f.startswith("--")):
                return [f"curl {token.split('=', 1)[0]}"]
    if program == "wget":
        for token in args:
            if token.startswith(_WGET_SEND_FLAGS):
                return [f"wget {token.split('=', 1)[0]}"]
            if token.startswith("--method=") and token.split("=", 1)[1].upper() in _SEND_METHODS:
                return [f"wget {token}"]
    positional = [a for a in args if not a.startswith("-")]
    if program in ("scp", "rsync") and positional and re.match(r"^[^/.][^/]*:", positional[-1]):
        return [f"{program} to {positional[-1].split(':', 1)[0]}:"]
    if program == "ssh" and positional:
        return [f"ssh {positional[0]}"]
    if program in ("sendmail", "mail", "mailx"):
        return [program]
    return []


def command_matches(
    command: str,
    config: dict | None = None,
    *,
    root: Path | None = None,
    cwd: Path | None = None,
    current_branch: str | None = None,
    extra_protected: tuple[str, ...] = (),
) -> list[Match]:
    """Every always-human match in `command`, each with its scope."""
    config = config or {}
    branches = protected_branches(config)
    data_globs = [*config.get("data_globs", []), *_extra(config, "AH3", "path")]
    found: list[Match] = []
    segs = segments(command)
    tag_deleted = False
    here = cwd or Path.cwd()  # follows `cd`, so a relative target resolves where it runs
    for tokens in segs:
        words, redirects = _split_redirects(tokens)
        if not words and not redirects:
            continue
        program = _name(words[0]) if words else ""
        if program in ("cd", "pushd"):
            dest = next((w for w in words[1:] if not w.startswith("-")), "~")
            here = Path(os.path.normpath(os.path.join(str(here), os.path.expanduser(dest))))
            continue

        owner = _owner_script(words)
        if owner:
            found.append(Match("AH5", f"owner-only {owner}", "always"))
        written, removed = _write_targets(words)
        for target in [*redirects, *written, *removed]:
            if _is_registry_target(target, here):
                found.append(Match("AH5", f"owner-only write to the approval registry ({target})", "always"))
                continue
            for rel in repo_relatives(target, root, here):
                if is_protected(rel, config, extra_protected) or (
                    target in removed
                    and any(covers(rel, g) for g in protected_globs(config, extra_protected))
                ):
                    found.append(Match("AH5", f"write to protected path {rel or '.'}", "active"))
                    break
        effective = _effective(words)
        if effective and _name(effective[0]) == "autonomy.py":
            sub = next((w for w in effective[1:] if not w.startswith("-")), "")
            if sub not in AGENT_SUBCOMMANDS:
                found.append(Match("AH5", f"autonomy.py {sub or '(no subcommand)'}", "active"))

        if program == "git":
            sub, rest = _git_subcommand(words)
            if sub == "tag" and "-d" in rest:
                tag_deleted = True
            if tag_deleted and sub == "push":
                found.append(Match("AH3", "git tag -d followed by git push", "active"))
            found.extend(Match("AH3", hit, "active") for hit in _git_matches(words, branches, current_branch))
        if words:
            found.extend(Match("AH3", hit, "active") for hit in _outward(words))
        if program == "rm" and any(
            w in ("--recursive", "--force") or re.match(r"^-[a-zA-Z]*[rRf]", w) for w in words[1:]
        ):
            for arg in (w for w in words[1:] if not w.startswith("-")):
                rels = repo_relatives(arg, root, here)
                hit = next((r for r in rels if any(covers(r, g) for g in data_globs)), None)
                if hit is not None:
                    found.append(Match("AH3", f"rm on data path {hit or '.'}", "active"))
        if words and _SQL.search(" ".join(words[1:])):
            found.append(Match("AH3", "SQL " + _SQL.search(" ".join(words[1:])).group(0), "active"))
        for key, item in (
            ("deploy_prod_patterns", "AH3"),
            ("deploy_dev_patterns", "AH3"),
            ("outward_patterns", "AH3"),
            ("spend_patterns", "AH4"),
        ):
            for pattern in config.get(key, []):
                if _pattern_hit(words, pattern):
                    found.append(Match(item, f"{key[:-9]} pattern '{pattern}'", "active"))
        for item in FRAMEWORK_ITEMS:
            for pattern in _extra(config, item, "command"):
                if _pattern_hit(words, pattern):
                    found.append(Match(item, f"project pattern '{pattern}'", "active"))
    return found


def classify_command(command: str, config: dict | None = None, **kwargs) -> list[str]:
    """The sorted item IDs `command` touches; `[]` when it touches none."""
    return sorted({m.item for m in command_matches(command, config, **kwargs)})


# --------------------------------------------------------------------------- artifacts

TIERS = ("tier-0", "tier-1", "tier-2-feature")
CLASSES = (*TIERS, "test-infra", "framework-non-business", "merge")
_TOUCH_ITEMS = {"business-rules": "AH1", "security": "AH2", "personal-data": "AH2"}
_TEST_INFRA = ("tests/**", "ci-examples/**", "scripts/verify*", "*fixtures/**")
_FRAMEWORK = ("AGENTS.md", ".agents/**", "doc/framework/**", "doc/templates/**", "scripts/**")
_DECISION_LINE = re.compile(r"^Decision-class:\s*(.+?)\s*$", re.MULTILINE)
_RISK_TIER = re.compile(r"Risk tier:\s*(\d)")


def classify_artifact(
    doc: Path,
    changed_paths: list[str],
    config: dict | None = None,
    extra_protected: tuple[str, ...] = (),
) -> tuple[str, set[str]]:
    """(derived class, always-human item IDs) for a document and its changes.

    Fails closed: a PRD or spec with no `Decision-class:` line, or no rule that
    yields a class, adds `AH-UNSURE`. The header can add a touch; it can never
    remove one that a path proves (ADR-9). Called only under autonomy.
    """
    config = config or {}
    text = doc.read_text(encoding="utf-8")
    items: set[str] = set()
    tiers: list[str] = []

    declared = _DECISION_LINE.search(text)
    touches: set[str] = set()
    if declared:
        head, _, tail = declared.group(1).partition(";")
        if head.strip() in TIERS:
            tiers.append(head.strip())
        tail = tail.strip()
        if tail.startswith("touches:"):
            touches = {t.strip() for t in tail[len("touches:"):].split(",") if t.strip()}
    elif doc.name.startswith(("PRD-", "SPEC-")):
        items.add(UNSURE)
    risk = _RISK_TIER.search(text)
    if risk and int(risk.group(1)) < len(TIERS):
        tiers.append(TIERS[int(risk.group(1))])

    for touch in touches - {"none"}:
        items.add(_TOUCH_ITEMS.get(touch, UNSURE))

    paths = [_normalise(p) for p in changed_paths]
    if paths and all(any(path_matches(p, g) for g in _TEST_INFRA) for p in paths):
        cls = "test-infra"
    elif paths and touches <= {"none"} and all(any(path_matches(p, g) for g in _FRAMEWORK) for p in paths):
        cls = "framework-non-business"
    elif tiers:
        cls = max(tiers, key=TIERS.index)
    else:
        cls = UNSURE
        items.add(UNSURE)

    for p in paths:
        if is_protected(p, config, extra_protected):
            items.add("AH5")
        for item in ("AH1", "AH2"):
            if any(path_matches(p, g) for g in _extra(config, item, "path")):
                items.add(item)
    return cls, items


# --------------------------------------------------------------------------- status


def project_root(cwd: Path | None = None) -> Path:
    """The git top level of `cwd`, or `cwd` itself outside a repo."""
    base = cwd or Path.cwd()
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=base,
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return base
    out = result.stdout.strip()
    return Path(out) if result.returncode == 0 and out else base


def current_branch(cwd: Path | None = None) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=cwd or Path.cwd(),
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip() or None if result.returncode == 0 else None


#: Folders that hold the owner's mandate and order documents. Their presence
#: is evidence this project opted in, even when the project file is gone.
_AUTHORITY_DIRS = ("doc/mandates", "doc/orders")


def _git_text(root: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args], cwd=root, capture_output=True, text=True, timeout=10, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout if result.returncode == 0 else None


def _slug(text: str | None) -> str | None:
    try:
        value = json.loads(text or "").get("project")
    except (json.JSONDecodeError, AttributeError):
        return None
    return str(value) if value else None


def _authority(root: Path, today: date | None = None) -> tuple[str, list[tuple[str, dict]]]:
    """(status text, the live mandate/order/absence entries governing `root`).

    Activation is anchored in the owner's registry, which the agent cannot
    write, not in `scripts/autonomy.json`, which it can move. The project is
    identified by, in order: the project file's slug; the slug committed at
    HEAD; else, if a mandate or order folder exists, ANY live mandate or order
    counts (the project cannot be told apart, so the guards stay on). With
    none of these the project never opted in and the registry is not read (R6).
    """
    config_path = root / CONFIG_REL
    claim_any = False
    if config_path.is_file():
        try:
            slug = json.loads(config_path.read_text(encoding="utf-8")).get("project")
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, AttributeError):
            return f"unknown ({CONFIG_REL} unreadable) — treated as active", []
    else:
        slug = _slug(_git_text(root, "show", f"HEAD:{CONFIG_REL}"))
        claim_any = any((root / d).is_dir() for d in _AUTHORITY_DIRS)
        if slug is None and not claim_any:
            return "inactive", []
    registry_file = verify_approvals.registry_path()
    entries, problem = verify_approvals.load_registry(registry_file)
    if problem and registry_file.exists():
        return f"unknown ({problem}) — treated as active", []

    today_text = (today or date.today()).isoformat()
    revoked = _revoked(entries)
    active: list[str] = []
    governing: list[tuple[str, dict]] = []
    for key, entry in entries.items():
        kind = entry.get("kind")
        if kind not in ("mandate", "order", "absence") or key in revoked:
            continue
        ours = (
            (slug and key.startswith(f"{kind}-{slug}-"))
            or (kind != "absence" and (root / str(entry.get("artifact", ""))).is_file())
            or (claim_any and kind != "absence")
        )
        if not ours:
            continue
        limit = str(entry.get("until" if kind == "absence" else "expires", ""))[:10]
        if limit and limit < today_text:
            continue
        active.append(f"absence since {entry.get('approved_at')}" if kind == "absence" else f"{kind} {key}")
        governing.append((key, entry))
    return "; ".join(sorted(active)) or "inactive", governing


def _revoked(entries: dict[str, dict]) -> set[str]:
    return {str(e.get("revokes")) for e in entries.values() if e.get("kind") == "revocation"}


def status(root: Path, today: date | None = None) -> str:
    """`inactive`, or what makes autonomy active (several joined by `; `).

    A project with no `scripts/autonomy.json`, none committed and no mandate or
    order folder has not opted in and is inactive without the registry being
    read (R6). Otherwise anything this cannot read is reported as active — the
    guards stay on (fail closed). Deleting or moving the project file does not
    switch autonomy off while the registry holds a live mandate or order.
    Mandate suspension (increment C) and absence end (increment K) are not
    computed yet; leaving them out keeps the guards on, the safe direction.
    """
    return _authority(root, today)[0]


def is_active(root: Path, today: date | None = None) -> bool:
    return status(root, today) != "inactive"


# --------------------------------------------------------------------------- check-commit

_TRAILER = re.compile(r"^Owner-Approved:\s*(\S+)\s*$", re.MULTILINE)


def _owner_approves(key: str, entries: dict[str, dict], revoked: set[str], artifacts: set[str]) -> bool:
    """`key` is the owner's approval (kind absent or `approval`), unrevoked, of
    one of `artifacts`. A mandate or order key is never consent for a single
    change: `status` prints it, so the agent can always quote it."""
    entry = entries.get(key)
    if entry is None or key in revoked or entry.get("kind", "approval") != "approval":
        return False
    return _normalise(str(entry.get("artifact", ""))).casefold() in artifacts


def _is_opt_in(root: Path, staged: list[str], key: str, entries: dict[str, dict], revoked: set[str]) -> bool:
    """The commit that first adds the project file, with a trailer naming the
    live mandate or order it opts in under. Before it, no committed file named
    the project, so no approval of a project path could exist yet."""
    if CONFIG_REL not in staged or _git_text(root, "cat-file", "-e", f"HEAD:{CONFIG_REL}") is not None:
        return False
    slug = _slug(_git_text(root, "show", f":{CONFIG_REL}"))
    entry = entries.get(key) or {}
    kind = entry.get("kind")
    return bool(slug) and kind in ("mandate", "order") and key not in revoked and key.startswith(f"{kind}-{slug}-")


def check_commit(root: Path, message: str, extra_protected: tuple[str, ...] = ()) -> list[str]:
    """Problems with the staged commit, or `[]`. Under autonomy, a staged
    protected path (added, changed, deleted or renamed) needs an
    `Owner-Approved: <key>` trailer naming the owner's approval of a changed
    path or of the mandate/order governing them."""
    state, governing = _authority(root)
    if state == "inactive":
        return []
    try:
        config = load_config(root)
    except ConfigError:
        config = {}
    staged = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--no-renames"],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    hits = [p for p in staged if is_protected(p, config, extra_protected)]
    if not hits:
        return []
    entries, _ = verify_approvals.load_registry(verify_approvals.registry_path())
    revoked = _revoked(entries)
    # Only a PROTECTED path in this commit or the governing document: an
    # approval of any other co-staged document is one the agent can quote.
    artifacts = {_normalise(p).casefold() for p in hits} | {
        _normalise(str(e.get("artifact", ""))).casefold() for _, e in governing
    }
    keys = _TRAILER.findall(message)
    if any(_owner_approves(k, entries, revoked, artifacts) for k in keys):
        return []
    opt_in = [k for k in keys if _is_opt_in(root, staged, k, entries, revoked)]
    if opt_in:
        # The opt-in clears only what it adds, never an edit to existing files,
        # and of that only the project file and the document the owner's
        # mandate or order entry names (AM1-ADR-3).
        cleared = {CONFIG_REL.casefold()} | {
            _normalise(str(entries[k].get("artifact", ""))).casefold() for k in opt_in
        }
        added = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--no-renames", "--diff-filter=A"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines()
        hits = [p for p in hits if not (p in added and _normalise(p).casefold() in cleared)]
        if not hits:
            return []
    why = (
        f"trailer key(s) {', '.join(keys)} are not the owner's approval of these paths "
        "or of the mandate governing them (a mandate or order key never counts)"
        if keys
        else "no `Owner-Approved: <key>` trailer"
    )
    return [f"always-human item AH5: {p} is protected while autonomy is active ({why})" for p in hits]


# --------------------------------------------------------------------------- CLI


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="scripts/autonomy.py", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("items", help="print the always-human list with project additions")
    sub.add_parser("status", help="inactive, or what makes autonomy active")
    check = sub.add_parser("check-commit", help="commit-time protected-path check")
    check.add_argument("--message-file", required=True)
    check.add_argument("--protect", action="append", default=[], help="extra protected glob")
    args = parser.parse_args(argv)
    root = project_root()

    if args.command == "items":
        try:
            config = load_config(root)
        except ConfigError as exc:
            print(exc, file=sys.stderr)
            return 2
        print(items_report(config))
        return 0
    if args.command == "status":
        print(status(root))
        return 0
    message = Path(args.message_file).read_text(encoding="utf-8")
    problems = check_commit(root, message, tuple(args.protect))
    for problem in problems:
        print(f"check-commit: {problem}", file=sys.stderr)
    if problems:
        print(
            "check-commit: the owner commits these with an `Owner-Approved: <registry key>` "
            "trailer. --no-verify skips this hook, not CI.",
            file=sys.stderr,
        )
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
