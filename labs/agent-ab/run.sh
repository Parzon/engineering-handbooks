#!/usr/bin/env bash
# One headless Claude Code run of one task in a fresh worktree, then the repository's checks.
# usage: run.sh <arm: base|plugin> <task: t1|t2|t3> <run-number>
# env:   TRIAGE_DIR (a triage-assistant checkout), PLUGIN_DIR (the plugin folder for the plugin arm),
#        MODEL (default sonnet), TA_REF (default handbook-1)
set -u
ARM=$1; TASK=$2; RUN=$3
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=${TRIAGE_DIR:-$HERE/../../../triage-assistant}
REF=${TA_REF:-handbook-1}
MODEL=${MODEL:-sonnet}
NAME="$ARM-$TASK-$RUN"
WT=$HERE/runs/$NAME
mkdir -p "$HERE/runs" "$HERE/out"
[ -d "$WT" ] && git -C "$REPO" worktree remove --force "$WT" >/dev/null 2>&1
git -C "$REPO" worktree add -q --detach "$WT" "$REF" || exit 1

PLUGIN=()
[ "$ARM" != base ] && PLUGIN=(--plugin-dir "${PLUGIN_DIR:?set PLUGIN_DIR for the plugin arm}")

cd "$WT"
START=$(date +%s)
env -u CLAUDECODE claude -p "$(cat "$HERE/tasks/$TASK.md")" \
  --model "$MODEL" --output-format json \
  --permission-mode acceptEdits --disallowedTools Bash \
  --setting-sources project --max-budget-usd 6 \
  "${PLUGIN[@]}" > "$HERE/out/$NAME.json" 2> "$HERE/out/$NAME.err"
END=$(date +%s)

# The change (a throwaway worktree: staging everything is fine here)
git add -A
git diff --cached --numstat > "$HERE/out/$NAME.numstat"
git diff --cached > "$HERE/out/$NAME.diff"
FILES=$(wc -l < "$HERE/out/$NAME.numstat")
ADDED=$(awk '{a+=$1} END{print a+0}' "$HERE/out/$NAME.numstat")
REMOVED=$(awk '{r+=$2} END{print r+0}' "$HERE/out/$NAME.numstat")
TESTS=$(grep -c -E '^\+.*(def test_|\b(it|test)\()' "$HERE/out/$NAME.diff")
DEPS=$(grep -c -E '^diff --git .*(pyproject\.toml|uv\.lock|package\.json|package-lock\.json)' "$HERE/out/$NAME.diff")

# The checks the pipeline runs (api)
cd "$WT/apps/api"
uv sync --locked --quiet >/dev/null 2>&1 && LOCK=ok || LOCK=FAIL
.venv/bin/ruff check . -q >/dev/null 2>&1 && RUFF=ok || RUFF=FAIL
.venv/bin/ruff format --check -q . >/dev/null 2>&1 && FMT=ok || FMT=FAIL
.venv/bin/mypy >/dev/null 2>&1 && MYPY=ok || MYPY=FAIL
DATABASE_URL=postgresql+asyncpg://u:p@localhost:1/x REDIS_URL=redis://localhost:1/0 \
  LLM_BASE_URL=http://localhost:1/v1 LLM_API_KEY=x LLM_MODEL=mock \
  OIDC_CLIENT_ID=x OIDC_CLIENT_SECRET=x OIDC_ISSUER=http://localhost:1 \
  .venv/bin/pytest tests/unit -q -p no:cacheprovider > "$HERE/out/$NAME.pytest" 2>&1 && PYTEST=ok || PYTEST=FAIL
# (web)
cd "$WT/apps/web"
npm ci --no-audit --no-fund --silent >/dev/null 2>&1
npx tsc -b >/dev/null 2>&1 && TSC=ok || TSC=FAIL
npx oxlint >/dev/null 2>&1 && OXLINT=ok || OXLINT=FAIL
npx vitest run --coverage=false > "$HERE/out/$NAME.vitest" 2>&1 && VITEST=ok || VITEST=FAIL

[ -s "$HERE/results.tsv" ] || printf 'name\tarm\ttask\trun\tcost_usd\tdur_s\twall_s\tturns\tout_tok\terror\tfiles\tadded\tremoved\ttests\tdeps\tlock\truff\tfmt\tmypy\tpytest\ttsc\toxlint\tvitest\n' > "$HERE/results.tsv"
python3 - "$HERE/out/$NAME.json" "$NAME" "$ARM" "$TASK" "$RUN" "$((END-START))" "$FILES" "$ADDED" "$REMOVED" "$TESTS" "$DEPS" "$LOCK" "$RUFF" "$FMT" "$MYPY" "$PYTEST" "$TSC" "$OXLINT" "$VITEST" <<'EOF' >> "$HERE/results.tsv"
import json, sys
f, name, arm, task, run, secs, files, added, removed, tests, deps, lock, ruff, fmt, mypy, pytest_, tsc, oxlint, vitest = sys.argv[1:]
try:
    d = json.load(open(f))
    cost = round(d.get("total_cost_usd", 0), 3); turns = d.get("num_turns"); dur = round(d.get("duration_ms", 0) / 1000)
    out_tok = d.get("usage", {}).get("output_tokens"); err = d.get("is_error")
except Exception as e:
    cost = turns = dur = out_tok = None; err = f"nojson:{e}"
print("\t".join(str(x) for x in [name, arm, task, run, cost, dur, secs, turns, out_tok, err, files, added, removed, tests, deps, lock, ruff, fmt, mypy, pytest_, tsc, oxlint, vitest]))
EOF
echo "done $NAME"
