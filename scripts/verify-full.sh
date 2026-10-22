#!/usr/bin/env bash
# THE EXIT GATE. Run before every handoff when `scripts/verify-handoff.sh --status` says not opted in
# (or that script does not exist). An opted-in project hands off on the handoff tier and runs
# this once per merge, in the merge gate (scripts/verify-merge.sh).
# A claim without this output does not count — that rule exists because "it works now"
# was said, and believed, about code that had never been run.
set -uo pipefail
cd "$(dirname "$0")/.."

# ---- fill these in for your stack -------------------------------------------
# Each entry: "label|command…"  — add project gates (migrations, contract freshness,
# registry counts) as extra lines rather than folding them into the test command.
STEPS=(
  "lint|echo TODO: set the lint command in scripts/verify-full.sh"
  "format|echo TODO: set the format --check command"
  "tests|echo TODO: set the full test command"
  # The next two are NOT placeholders — do not replace them. The framework's own
  # guards ship with tests whatever your stack is, and if they go red a gate
  # you rely on may be open again.
  "hooks|python3 -m pytest tests/hooks/ -q"
  # Proves the CI examples in ci-examples/ still do what they claim: every
  # command they run for real matches this repo's actual scripts, and the
  # registry/placeholder checks they inline still bite. Before this step
  # existed, ci-examples/ had never been run or tested at all — the layer the
  # whole framework calls "the real enforcement" had never made a sound.
  "ci-examples|python3 -m pytest tests/ci/ -q"
  # Proves scripts/scar_status.py (the Scar Forge's station tracker, NORTH-STAR
  # mechanism ๑) parses this repo's own real scar records correctly and still
  # catches a closed-with-no-trace or out-of-order scar. Also runs the tracker
  # itself: a Closed scar with no Station 6 date, or stations entered out of
  # order, fails this step for real, not just in the test suite.
  "scar-forge|python3 -m pytest tests/scars/ -q && python3 scripts/scar_status.py"
  # Proves scripts/coordinator_lint.py (the mechanically-checked half of the
  # Coordinator Constitution, NORTH-STAR mechanism ๓) still catches an
  # untagged count claim, a truncating MEASURED: command, an untagged
  # instruction, and a missing SELF-REPORT: block; and scripts/handback_lint.py
  # still catches a handback missing Could not reach: / Substituted:.
  "coordinator|python3 -m pytest tests/coordinator/ -q"
  # Open-standard layout and portability (RUNTIME-CONTRACT criteria 1-4):
  # provider names stay out of layers 0-1, project memory keeps its
  # lifecycle, skill links resolve, and the commit-time fallback for
  # assistants without interception really refuses a planted violation.
  "framework|python3 -m pytest tests/framework/ -q && python3 scripts/check_neutrality.py && python3 scripts/memory_lint.py"
)
# -----------------------------------------------------------------------------

# ---- run record, project conf, bans (increment A+C) ---------------------------
# Every run gets a fresh directory, so a report left by an earlier run can never
# be counted as this one. The project's own values live in scripts/verify.conf
# (see scripts/verify.conf.example), which may override STEPS; without it the
# gate behaves as before, plus timing, a record and informational lines.
RUN_DIR=".verify/runs/$(date -u +%Y%m%dT%H%M%SZ)-$$"
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
mkdir -p "$RUN_DIR"
export VERIFY_RUN_DIR="$RUN_DIR"
conf_present=""
if [ -f scripts/verify.conf ]; then
  conf_present="--conf-present"
  # A conf with a syntax error stops parsing halfway: bash keeps what it read and
  # drops the rest (VERIFY_TEST_STEPS, say) without a word. So the syntax is
  # checked first. The exit status of `.` is not a load failure: a conf whose
  # last line is `[ -n "$X" ] && VAR=…` loaded completely and returns 1 — and so
  # does a conf with an array left open at EOF, for which bash 3.2's `bash -n`
  # prints the error yet exits 0. So any output from `bash -n` is a failure too.
  if ! conf_err="$("$BASH" -n scripts/verify.conf 2>&1)" || [ -n "$conf_err" ]; then
    echo "EXIT GATE RED — scripts/verify.conf failed to load (syntax error); no step was run"
    printf '%s\n' "$conf_err"
    exit 1
  fi
  . scripts/verify.conf || true
fi
export VERIFY_TEST_STEPS VERIFY_STEP_BUDGET_S VERIFY_TEST_BUDGET_SMALL_S \
  VERIFY_TEST_BUDGET_MEDIUM_S VERIFY_TEST_BUDGET_LARGE_S VERIFY_TEST_SIZE_RULES
# A gate that quietly skipped its own counting would be the failure it exists to catch.
if [ ! -f scripts/verify_record.py ]; then
  echo "EXIT GATE RED — recorder missing (scripts/verify_record.py)"
  exit 1
fi
# Zero steps would verify nothing; bash 3.2 also dies on "${STEPS[@]}" when empty.
if [ -z "${STEPS[*]+x}" ]; then
  echo "EXIT GATE RED — no steps configured"
  exit 1
fi
# Two test steps with one label would share one JUnit directory and count it twice.
seen_test_labels=" "
for entry in "${STEPS[@]}"; do
  label="${entry%%|*}"
  case " ${VERIFY_TEST_STEPS:-} " in
    *" $label "*)
      case "$seen_test_labels" in
        *" $label "*)
          echo "EXIT GATE RED — duplicate test step label: ${label}; give each test step its own label"
          exit 1 ;;
      esac
      seen_test_labels="${seen_test_labels}${label} " ;;
  esac
done
allow_args=()
for e in ${VERIFY_ALLOWED_FILTERS[@]+"${VERIFY_ALLOWED_FILTERS[@]}"}; do
  allow_args+=("--allow=$e")
done
runner_args=()
for r in ${VERIFY_TEST_RUNNERS[@]+"${VERIFY_TEST_RUNNERS[@]}"}; do
  runner_args+=("--runner=$r")
done
cmd_args=()
for entry in "${STEPS[@]}"; do cmd_args+=("--step=${entry}"); done
[ -n "${VERIFY_COLLECT_CMD:-}" ] && cmd_args+=("--step=VERIFY_COLLECT_CMD|${VERIFY_COLLECT_CMD}")
# --lf, -x, retries, cached results and undeclared filters can each report success
# while executing nothing; refused before any step runs. A step whose flags are
# not scanned (a runner other than pytest) is named on a `limit:` line.
python3 -I scripts/verify_record.py check-banned ${allow_args[@]+"${allow_args[@]}"} \
  ${runner_args[@]+"${runner_args[@]}"} "--extra=${VERIFY_EXTRA_BANNED:-}" \
  "--test-steps=${VERIFY_TEST_STEPS:-}" "${cmd_args[@]}"
ban_rc=$?
if [ "$ban_rc" -ne 0 ]; then
  [ "$ban_rc" -eq 2 ] && exit 2
  echo "EXIT GATE RED — recorder failed (check-banned exit ${ban_rc})"
  exit 1
fi
TREE_BEFORE="$(python3 -I scripts/verify_record.py tree-hash)"
collect_args=()
if [ -n "${VERIFY_COLLECT_CMD:-}" ]; then
  eval "$VERIFY_COLLECT_CMD" >"$RUN_DIR/collect.txt" 2>"$RUN_DIR/collect.err"
  collect_args=(--collect-file "$RUN_DIR/collect.txt" --collect-rc "$?")
fi
: >"$RUN_DIR/steps.tsv"
# -----------------------------------------------------------------------------

fail=0
todo=0
todo_labels=""
echo "EXIT GATE — full verify"
for entry in "${STEPS[@]}"; do
  label="${entry%%|*}"; cmd="${entry#*|}"
  # An unfilled placeholder is neither a pass nor a failure, and must never be
  # printed as "OK". A step whose command is still `echo TODO:` runs nothing,
  # yet an `echo` exits 0 — so the honest-looking version of this loop reported
  # OK three times and then declared the gate GREEN over a build that had not
  # been linted, formatted or tested. That is this framework's first truth
  # (a system reporting success while the truth is elsewhere) committed by the
  # very script whose job is to prevent it.
  if [[ "$cmd" == echo\ TODO:* ]]; then
    printf '  %-5s%-18s%s\n' "TODO" "$label" "not configured — this step verified NOTHING"
    todo=$((todo + 1))
    todo_labels="${todo_labels} ${label}"
    printf '%s\t0\t0\t1\t\n' "$label" >>"$RUN_DIR/steps.tsv"
    continue
  fi
  # A step listed in VERIFY_TEST_STEPS writes JUnit into its own fresh directory.
  junit=""
  case " ${VERIFY_TEST_STEPS:-} " in
    *" $label "*) junit="$RUN_DIR/junit/$label"; mkdir -p "$junit" ;;
  esac
  if [ -n "$junit" ]; then export VERIFY_JUNIT_DIR="$junit"; else unset VERIFY_JUNIT_DIR; fi
  t0=$(date +%s)
  if out=$(eval "$cmd" 2>&1); then rc=0; else rc=$?; fi
  secs=$(( $(date +%s) - t0 ))
  if [ "$rc" -eq 0 ]; then
    printf '  %-5s%-18s%s\n' "OK" "$label" "(${secs}s) $(printf '%s' "$out" | tail -1)"
  else
    printf '  %-5s%-18s(%ss) (exit %s)\n' "FAIL" "$label" "$secs" "$rc"
    printf '%s\n' "$out" | tail -30
    fail=1
  fi
  printf '%s\t%s\t%s\t0\t%s\n' "$label" "$rc" "$secs" "$junit" >>"$RUN_DIR/steps.tsv"
done

# Counts, tree identity, budgets and the record. The recorder's last line is
# VERDICT=<v>; anything else (it crashed) is RED, never a silent pass.
TREE_AFTER="$(python3 -I scripts/verify_record.py tree-hash)"
summary="$(python3 -I scripts/verify_record.py finalize --tier full --run-dir "$RUN_DIR" \
  --started-at "$STARTED_AT" --tree-before "$TREE_BEFORE" --tree-after "$TREE_AFTER" \
  ${conf_present:+"$conf_present"} ${collect_args[@]+"${collect_args[@]}"} \
  ${allow_args[@]+"${allow_args[@]}"})"
finalize_rc=$?
verdict="$(printf '%s\n' "$summary" | tail -1)"
printf '%s\n' "$summary" | sed '$d'
case "$verdict" in
  VERDICT=GREEN | VERDICT=INCOMPLETE) ;;
  VERDICT=RED) fail=1 ;;
  *) echo "recorder failed — no verdict from scripts/verify_record.py"; fail=1 ;;
esac
# Never point a handoff at a record that does not exist.
print_record() {
  if [ -f "$RUN_DIR/record.json" ]; then
    echo "record: $RUN_DIR/record.json"
  else
    echo "record: not written (scripts/verify_record.py exited ${finalize_rc} before writing it)"
  fi
}

if [ "$fail" -ne 0 ]; then
  echo "EXIT GATE RED (exit 1)."
  echo "Do not hand off. Diagnose the real cause; do not skip a test, loosen an assertion,"
  echo "or hardcode an expected value to make it pass."
  print_record
  exit 1
fi

if [ "$todo" -ne 0 ]; then
  # Deliberately exit 0: a fresh clone must not be wedged before bootstrap. But
  # the word GREEN is withheld, because that word is what gets pasted into a
  # handoff as evidence, and it would be evidence of nothing.
  echo "EXIT GATE INCOMPLETE — ${todo} step(s) not configured:${todo_labels}"
  echo "Everything configured passed, and that is ALL this run proves."
  echo "Fill those steps in scripts/verify-full.sh before treating this output as a gate."
  print_record
  exit 0
fi
echo "EXIT GATE GREEN. Paste this output in the handoff when not opted in; when opted in, the merge gate's record is the evidence."
print_record
