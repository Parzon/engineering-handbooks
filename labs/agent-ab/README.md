# Lab: measure a coding-agent skill on the reference build

Handbook 1, Chapter 18. A skill's README benchmark was run by its maintainer on its
maintainer's tasks. This lab measures a skill or plugin on triage-assistant with
the same task text, a fresh worktree per run and the repository's own checks
afterwards. It produced the numbers in Figure 18.5.

## What it does

`run.sh <arm> <task> <n>` makes a detached worktree of triage-assistant at the
pinned tag, runs Claude Code headless on the task with the agent allowed to read
and edit but not to run commands, then measures the change (files, lines added
and removed, tests added, dependency files touched) and runs the checks the
pipeline runs: `uv sync --locked`, `ruff check`, `ruff format --check`, `mypy`,
the unit tests, `tsc -b`, `oxlint`, `vitest`. One line per run goes to
`results.tsv`; the diff and the agent's answer are kept under `out/`.

The `base` arm loads nothing. Any other arm loads the plugin folder you point
`PLUGIN_DIR` at, for that run only, so the arms differ in exactly one thing.

## Running it

```bash
export TRIAGE_DIR=../../../triage-assistant      # a checkout with the handbook tag fetched
export PLUGIN_DIR=~/.claude/plugins/cache/<marketplace>/<plugin>/<version>
export MODEL=sonnet                              # the model is a variable too; keep it fixed across arms

for run in 1 2; do for task in t1 t2 t3; do for arm in base plugin; do
  ./run.sh "$arm" "$task" "$run"
done; done; done
column -t -s $'\t' results.tsv
```

The three tasks in `tasks/` are deliberately ordinary: an endpoint with the same
visibility rules as an existing one, a retry in the model client, a filter in a
React list. Write your own in the same shape: an outcome, its constraints, "add
tests", and "do not run commands; I will run the checks".

## Reading the result

- Compare lines added, output tokens and cost per arm, then **read the diffs**.
  A green run can still contain an unnecessary feature: in the handbook's run,
  the SDK already retried, and only half the runs in either arm noticed.
- Two runs per cell is a pilot. It is enough to see whether a README headline
  appears on your code; it is not enough to publish a percentage.
- Expect the checks to fail for the same reason in both arms when the agent
  cannot run them (a type error, an unformatted file). That is the price of
  "do not run commands", not of either arm.
- If the plugin ships an `evals/` folder, `claude plugin eval <plugin>` runs its
  cases with a no-plugin baseline arm and is the more rigorous tool.

## Verifying inside the stack instead

The web checks need Node 22 or newer and the api checks need `uv`. If the host
has neither, run the measurement step inside the dev containers:
`docker compose run --rm --no-deps api make check` from the worktree, and the
web equivalents from the `web` service.
