#!/usr/bin/env bash
# Inner loop while iterating. ALWAYS pass the paths you touched — scoping is the whole point
# (on one real project this was 0.49s scoped vs 47.6s unscoped, which is the difference
# between running it every time and quietly skipping it).
#
# Forbidden here and in verify-full.sh: --lf, -x, and -k/-m filtering used to reach green.
# Each can report success while executing nothing.
set -euo pipefail
cd "$(dirname "$0")/.."

# ---- fill these in for your stack -------------------------------------------
LINT=(echo "TODO: set LINT in scripts/verify-fast.sh — e.g. ruff check")
TEST=(echo "TODO: set TEST in scripts/verify-fast.sh — e.g. pytest -q")
# -----------------------------------------------------------------------------

[ $# -eq 0 ] && { echo "usage: $0 <paths…>   (ส่ง path ที่แตะเสมอ)" >&2; exit 2; }

# ---- run record, project conf, bans (increment A+C) ---------------------------
# VERIFY_JUNIT_DIR is exported BEFORE the conf is sourced, because the conf's
# LINT/TEST arrays expand it at assignment time.
if [ ! -f scripts/verify_record.py ]; then
  echo "FAST VERIFY RED — recorder missing (scripts/verify_record.py)"
  exit 1
fi
RUN_DIR=".verify/runs/$(date -u +%Y%m%dT%H%M%SZ)-$$-fast"
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
mkdir -p "$RUN_DIR/junit/tests"
export VERIFY_RUN_DIR="$RUN_DIR" VERIFY_JUNIT_DIR="$RUN_DIR/junit/tests"
if [ -f scripts/verify.conf ]; then
  # A syntax error drops the rest of the conf without a word: check it first
  # (the same rule as verify-full.sh). A false last line is not a load failure,
  # so `.` runs outside set -e. bash 3.2's `bash -n` prints an array left open at
  # EOF yet exits 0, so any output from it is a failure too.
  if ! conf_err="$("$BASH" -n scripts/verify.conf 2>&1)" || [ -n "$conf_err" ]; then
    echo "FAST VERIFY REFUSED — scripts/verify.conf failed to load (syntax error)"
    printf '%s\n' "$conf_err"
    exit 2
  fi
  set +e
  . scripts/verify.conf
  set -e
fi
allow_args=()
for e in ${VERIFY_ALLOWED_FILTERS[@]+"${VERIFY_ALLOWED_FILTERS[@]}"}; do
  allow_args+=("--allow=$e")
done
runner_args=()
for r in ${VERIFY_TEST_RUNNERS[@]+"${VERIFY_TEST_RUNNERS[@]}"}; do
  runner_args+=("--runner=$r")
done
collect_cmd_args=()
[ -n "${VERIFY_COLLECT_CMD:-}" ] && collect_cmd_args=("--step=VERIFY_COLLECT_CMD|${VERIFY_COLLECT_CMD}")
runtime_args=()
for a in "$@"; do runtime_args+=("--runtime=$a"); done
# The paths typed here are runtime arguments: the allow-list never covers them.
python3 -I scripts/verify_record.py check-banned ${allow_args[@]+"${allow_args[@]}"} \
  ${runner_args[@]+"${runner_args[@]}"} "--extra=${VERIFY_EXTRA_BANNED:-}" \
  "--step=lint|$(printf '%q ' "${LINT[@]}")" "--step=tests|$(printf '%q ' "${TEST[@]}")" \
  ${collect_cmd_args[@]+"${collect_cmd_args[@]}"} "${runtime_args[@]}"
t0=$(date +%s)
# -----------------------------------------------------------------------------

# A placeholder step runs `echo`, which exits 0. Counting it as a pass and then
# printing OK is the same false assurance verify-full.sh used to commit, one
# tier down — and this is the tier that runs dozens of times a day.
todo=0
echo "== lint";  "${LINT[@]}" "$@"
case "${LINT[0]}${LINT[1]-}" in *"TODO: set"*) todo=$((todo + 1));; esac
t1=$(date +%s)
echo "== tests"; "${TEST[@]}" "$@"
case "${TEST[0]}${TEST[1]-}" in *"TODO: set"*) todo=$((todo + 1));; esac
t2=$(date +%s)

# The framework's own teeth travel with every stack. Touching a hook, an
# approval script, the file that REGISTERS the hooks, or any of their tests
# runs the hook suite too — the fill-in commands above know nothing about it,
# and a TODO stub passing is not evidence about a guard.
#
# `.claude/settings.json` is in this list for the quietest failure of the set:
# an unregistered hook never runs, and the tests that catch exactly that
# (`test_the_guard_is_registered_in_settings_json` and its siblings) would
# otherwise be skipped by the very edit that breaks them.
case " $* " in
  *".claude/hooks"* | *"tests/hooks"* | *"scripts/approve"* \
  | *"scripts/verify_approvals"* | *".claude/settings.json"*)
    echo "== framework hook tests"
    python3 -m pytest tests/hooks/ -q
    ;;
esac

# Touching a CI example, the exit gate itself, or bootstrap's placeholder list
# can silently desync ci-examples/ from what it claims to run — that is the
# exact failure tests/ci/ exists to catch, so a touch to any of these paths
# has to pay for it here too, not just at the exit gate.
case " $* " in
  *"ci-examples"* | *"tests/ci"* | *"scripts/verify-full.sh"* | *"scripts/bootstrap.sh"*)
    echo "== ci-examples drift tests"
    python3 -m pytest tests/ci/ -q
    ;;
esac

# The verify tiers themselves (increment A+C): a touch to either tier, the
# recorder or the project conf re-earns the no-fake-green tests.
case " $* " in
  *"scripts/verify"* | *"tests/hooks/test_verify_"*)
    echo "== verify-tier tests"
    python3 -m pytest tests/hooks/test_verify_scripts.py tests/hooks/test_verify_tiers.py -q
    ;;
esac

# The Scar Forge's station tracker (scripts/scar_status.py) has its own
# mechanically-checked claims (a closed scar must carry a Station 6 date, a
# scar's Status must not collide with the approval-registry vocabulary) — a
# touch to the tracker, its template, or a scar record itself has to pay for
# re-checking those, same as any other guard in this repo.
case " $* " in
  *"scripts/scar_status.py"* | *"tests/scars"* | *"doc/scars"* | *"doc/templates/SCAR.md"*)
    echo "== scar-forge tests"
    python3 -m pytest tests/scars/ -q
    ;;
esac

# The mechanically-checked half of the Coordinator Constitution
# (scripts/coordinator_lint.py) has its own grammar checks that a touch to
# the checker or its contract has to re-earn.
case " $* " in
  *"scripts/coordinator_lint.py"* | *"scripts/handback_lint.py"* | *"tests/coordinator"* | *"doc/framework/COORDINATOR-CONSTITUTION.md"*)
    echo "== coordinator-constitution tests"
    python3 -m pytest tests/coordinator/ -q
    ;;
esac

# The agent-time meter (scripts/agent_time.py) and adapter ก's reader for it
# are pinned to a golden timeline with planted mutations; a touch to either,
# their fixtures, or the ADAPTERS.md rows that declare them has to re-earn it.
case " $* " in
  *"scripts/agent_time.py"* | *"tests/framework/test_agent_time.py"* | *"tests/framework/fixtures/agent_time"* \
  | *".claude/meter"* | *"tests/hooks/test_transcript_reader.py"* | *"tests/hooks/fixtures/transcripts"* \
  | *"tests/framework/test_doc_contracts.py"* | *"doc/framework/ADAPTERS.md"*)
    echo "== agent-time meter tests"
    python3 -m pytest tests/framework/test_agent_time.py tests/hooks/test_transcript_reader.py \
      tests/framework/test_doc_contracts.py -q
    ;;
esac

# The always-human list (scripts/autonomy.py) is imported by the hooks AND by
# the commit-msg hook, so a touch to it, its project file, the git hooks or
# their tests re-runs both suites that exercise it.
case " $* " in
  *"scripts/autonomy"* | *"tests/framework/test_autonomy"* | *".githooks"* \
  | *"tests/framework/test_pre_commit"*)
    echo "== always-human list tests"
    python3 -m pytest tests/framework/ tests/hooks/ -q
    ;;
esac

if [ "$todo" -ne 0 ]; then
  echo "FAST VERIFY INCOMPLETE — ${todo} of 2 step(s) not configured; they verified NOTHING."
  echo "Fill LINT and TEST in scripts/verify-fast.sh."
  exit 0
fi
# Never more than it ran: "ran N of M", or EMPTY (exit 1) when the tests ran zero cases.
printf 'lint\t0\t%s\t0\t\ntests\t0\t%s\t0\t%s\n' $((t1 - t0)) $((t2 - t1)) "$VERIFY_JUNIT_DIR" \
  >"$RUN_DIR/steps.tsv"
collect_args=()
if [ -n "${VERIFY_COLLECT_CMD:-}" ]; then
  crc=0
  eval "$VERIFY_COLLECT_CMD" >"$RUN_DIR/collect.txt" 2>"$RUN_DIR/collect.err" || crc=$?
  collect_args=(--collect-file "$RUN_DIR/collect.txt" --collect-rc "$crc")
fi
exec python3 -I scripts/verify_record.py finalize --tier fast --run-dir "$RUN_DIR" \
  --started-at "$STARTED_AT" ${collect_args[@]+"${collect_args[@]}"} \
  ${allow_args[@]+"${allow_args[@]}"}
