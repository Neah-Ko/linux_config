---
name: pr-review
description: Review a GitHub pull request, diff a branch against its base, or figure out what changed and what it breaks. Use whenever the user says "review this PR", "what changed", "look at the diff", "gh pr", "merge-base", "changed files", "blast radius", "is this PR safe", or asks for a code review of a branch. Also use before running tests on a branch, to decide which tests are actually affected.
---

# PR review

Token-efficient review of GitHub pull requests and branch diffs. The goal is to answer
the reviewer's question from **diffs**, not from full-file reads.

## 0. Contract

- **Read-only.** `gh pr create | merge | close | reopen | comment | review | edit | ready`
  are denied by policy. Drafting review text in your answer is fine; **posting it is not**.
- Never `cd`. Use the bash tool's `workdir` parameter.
- Always prefer `rtk git` / `rtk gh` over bare `git` / `gh` — they emit token-optimized output.
- Always pass `--no-pager` to bare `git` if `rtk` is unavailable.
- **Never `read` a file in full because it appears in a diff.** Diff it. Read only the
  surrounding context, with `offset`/`limit` derived from the hunk header.

## 1. Resolve the PR and its base

```bash
rtk gh pr view --json number,title,headRefName,baseRefName,state,isDraft,additions,deletions,changedFiles
```

Add an explicit number (`rtk gh pr view 271 ...`) when not on the PR branch.

Then pin the base commit once and reuse it:

```bash
BASE=$(git merge-base origin/main HEAD)
```

Substitute the real `baseRefName` when it is not `main`. If there is no PR (local branch
review), use `origin/main` directly. Use three-dot ranges (`$BASE...HEAD`) so unrelated
changes on the base branch never pollute the diff.

## 2. Diff ladder — cheapest first, stop as soon as the question is answered

| # | Purpose | Command | Cost |
|---|---|---|---|
| 1 | Shape of the change | `rtk git diff --stat $BASE...HEAD` | ~1 line per file |
| 2 | Exact file list + status | `rtk git diff --name-status --diff-filter=ACMR $BASE...HEAD` | ~1 line per file |
| 3 | Hunks for one file | `rtk git diff $BASE...HEAD -- <path>` | per-file |
| 4 | Commit narrative | `rtk git log --oneline $BASE..HEAD` | 1 line per commit |
| 5 | Provenance of a specific line | `rtk git show <sha>` · `git --no-pager blame -L <a>,<b> -- <path>` | on demand |

Or use the wrapper, which spools the full diff to disk and prints only the summary:

```bash
$HOME/.config/opencode/review-diff.sh            # --stat summary (default)
$HOME/.config/opencode/review-diff.sh files      # --name-status
$HOME/.config/opencode/review-diff.sh log        # --oneline commit list
$HOME/.config/opencode/review-diff.sh full       # tail of the full diff
$HOME/.config/opencode/review-diff.sh --pr 271 stat
$HOME/.config/opencode/review-diff.sh --base origin/release stat
```

It writes `${TMPDIR:-/tmp}/opencode-diff-<repo>.log`. Grep that file for specific hunks
instead of streaming a 3 000-line diff through context.

**Anti-patterns:** `git diff` with no range (unstaged noise) · `git log -p` (whole diff as
log) · `git show` on a merge commit · reading a 2 000-line test file because two lines
changed in it.

## 3. Blast radius — route, do not re-derive

Map each changed path to the next action. Hand off to the existing skill instead of
re-discovering the affected surface.

| Changed path | Next action |
|---|---|
| `packages/**/src/one_analytics/**/*.py` | `test-scoping` skill → one `@tester` call on the mapped test paths |
| `tests/mixins/fixtures.py`, `tests/conftest.py` | fixtures are global → run the whole `tests/unit/` suite |
| `tests/unit/**` only | run just those test files; no source risk |
| pipeline / coef computation logic (`ageing_pipeline.py`, `*_ageing.py`, `*_computation.py`, `*_coef.py`) | `analytics-run-validation` skill → baseline-vs-PR `dbx diff` on the run outputs |
| `liquibase/**`, `dabs/**`, `**/databricks.yml` | `repo-navigation/reference/config.md` (line-indexed) — do not full-read these |
| `.github/workflows/**`, `.github/actions/**` | `repo-navigation/reference/config.md`; check `rtk gh pr checks` for the real outcome |
| `pyproject.toml`, `justfile`, `uv.lock` | `@tester` with `run-checks.sh` (all gates) + full test suite |
| `notebooks/**`, `**/mock/**` | lint-only risk; ruff per-file ignores apply — see `test-scoping` §4 |

For "where is this symbol defined / who calls it", use `repo-navigation` and its
`reference/hot-files.md` symbol index before any `grep -r`.

## 4. CI status

```bash
rtk gh pr checks                      # per-check pass/fail table
rtk gh run view <run-id> --log-failed # failed steps only — never the full log
```

Do not dump complete workflow logs. If a job fails, fetch `--log-failed`, quote the
smallest failing excerpt, then map it back to a changed file via §3.

## 5. Reporting template

```
SCOPE     <n> files, +<add>/-<del>, base <short-sha> (<baseRefName>)
INTENT    one sentence: what this PR is trying to do
BLOCKING  correctness / security / data-loss issues — file:line + why
NON-BLOCKING  style, naming, dead code, missing types
TEST GAP  behaviour changed with no corresponding test change
VERIFY    the exact next command(s): @tester <paths> | dbx diff ... | run-checks.sh --changed
```

Keep `BLOCKING` empty rather than padding it. Every finding must cite `path:line`.

## Related skills

- `test-scoping` — source→test mapping and the `@tester` delegation contract
- `repo-navigation` — symbol/line indexes so diffs never require full-file reads
- `analytics-run-validation` — baseline vs PR data comparison for pipeline changes
- `databricks` — the `dbx` helper used by the above
