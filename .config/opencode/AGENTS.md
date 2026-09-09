# AGENTS.md — General Coding Agent Instructions

This file provides guidance for agentic coding agents (e.g. OpenCode, Copilot, Claude) operating across repositories on this machine.

---

## Global Rules

### Style
- Be concise — short answers by default, expand only if asked
- Prefer diffs over full file rewrites
- No unsolicited explanations or commentary
- No flattery
- Provide sources whenever possible

### Code
- No unnecessary comments in code
- Do not add packages without asking
- Ask before running destructive commands
- Never commit nor push on git
- Always use bash cp to copy files between repositories. Never use the edit tool for file copying.
- Use `rtk git` / `rtk gh` for all VCS reads. Never post PR reviews, comments, or approvals.

### Shell discipline
- Use the bash tool's `workdir` parameter. Never `cd <dir> && <cmd>`.
- Prefer `rtk` wrappers when available (`rtk git`, `rtk grep`, `rtk ls`, `rtk uv`, `rtk find`) — they are token-optimized.
- Read files with `offset`/`limit`. Full-file reads are a last resort; consult the `repo-navigation` skill index first.
- Never full-read a file just because it appears in a diff — diff it, then offset-read only the surrounding context.
- Scratch files go in `/tmp/opencode/`.

### Databricks
- **Never write Databricks connection code.** No `from databricks import sql`, no inline `python3 -c`/heredoc connector, no reading `~/.databrickscfg`, no hand-built `/sql/1.0/warehouses/...` paths.
- All SQL goes through the `databricks` skill's `dbx` helper (`--var/-v`, `batch`, `diff`, `runctx`, `card`, `coefs`).
- If `dbx` cannot express what you need, report the gap and stop — do not re-implement the connector.

---

## Skills

| Skill | Use for |
|---|---|
| `databricks` | any SQL / schema / table exploration against `esxp_*` catalogs |
| `analytics-run-validation` | validating or A/B-comparing a pipeline `run_id`, baseline vs PR |
| `repo-navigation` | locating symbols/files in `one-analytics-mono` without full-file reads |
| `test-scoping` | choosing which tests/gates to run after a change, and delegating to `@tester` |
| `pr-review` | reviewing a GitHub PR, diffing a branch against main, assessing blast radius |
| `customize-opencode` | editing opencode's own config, agents, skills, plugins |

---

## Test Execution
- Never run tests yourself. Always invoke @tester for any test command.
- Quality gates (ruff / format / ty / complexipy / codespell) also go through @tester, via `~/.config/opencode/run-checks.sh`.
- After @tester returns, read its structured summary and include it in your response.
- Do not re-describe what @tester should do — invoke it with the task and context.

---

## Environment

- **OS**: Linux (WSL2) - Debian GNU/Linux 13 (trixie)
- **Shell**: Bash
- **Package manager**: `uv` (Python), `bun` (Node/TS)
- **Task runner**: `just` (justfiles present in most repos)
- **Python version**: 3.13.5 (systemwide, can be different in `uv` envs)
- **Proxy**: `http://127.0.0.1:9000` (set for HTTP/HTTPS)

---

## MCP

### ecostruxure-mcp

Use the `ecostruxure-mcp` tools when the user asks questions related to Schneider Electric EcoStruxure or EDM (Ecustructure Data Model), including:
- EDM concepts, architecture, vocabulary, ontology, or documentation
- Measurement definitions or dictionary lookup
- Alarm definitions or dictionary lookup
- Point of View (PoV) definitions for assets or equipment

---

## Build, Lint & Test Commands

### Python repos (uv + just)

```sh
# Install dependencies
uv sync

# Run all unit tests
just test-all
# or directly:
uv run pytest tests/unit/

# Run tests for a single package (monorepo)
just test <package-name>
# e.g.: just test one-analytics-security-observability

# Run a single test file
uv run pytest tests/unit/path/to/test_file.py

# Run a single test by name
uv run pytest tests/unit/path/to/test_file.py::test_function_name

# Lint (ruff)
uv run ruff check .
uv run ruff format --check .

# Auto-fix lint issues
uv run ruff check --fix .
uv run ruff format .

# Type checking (ty — preferred in monorepo)
just ty <package-name>
just ty-all
# or: uv run ty check src/

# Type checking (mypy — used in one-analytics-core)
uv run mypy src/

# Spell check
uv run codespell

# Complexity check
uv run complexipy
```

### Node/TypeScript repos (bun)

```sh
bun install
bun run build
bun test
bun run lint
```

---

## Code Style Guidelines

### Python

- **Line length**: 120 characters (matches Sonar rule)
- **Formatter**: `ruff format` (Black-compatible)
- **Linter**: `ruff` with a strict ruleset (see `pyproject.toml`)
- **Type checker**: `ty` (monorepo) or `mypy` (one-analytics-core); strict mode enabled

#### Imports

- Always use `from __future__ import annotations` at the top of every file (enforced by `FA` ruff rule)
- Imports must be sorted (`I` rule) — use `ruff check --fix` to auto-sort
- Use `pathlib` instead of `os.path` (enforced by `PTH` rule)
- Follow standard import conventions: stdlib → third-party → local (enforced by `ICN`/`TID`)
- Avoid unused imports; avoid wildcard imports

#### Naming Conventions

- Follow PEP 8 and ruff `N` rules:
  - `snake_case` for functions, variables, modules
  - `PascalCase` for classes
  - `UPPER_SNAKE_CASE` for constants
  - `_private` prefix for internal helpers

#### Types & Annotations

- All functions must have full type annotations (`disallow_untyped_defs = true`)
- Use `from __future__ import annotations` to enable PEP 563 deferred evaluation
- Avoid `Any` unless absolutely necessary (`ANN401` is enforced)
- Prefer `pydantic` models for data validation and structured configs
- Use `TypeAlias` and `TYPE_CHECKING` guards for type-only imports (`TC` rule)

#### Error Handling

- Catch specific exceptions, never bare `except:` or `except Exception:` without re-raising
- Use custom exception classes for domain errors
- Avoid swallowing exceptions silently

#### General

- No dead/commented-out code (enforced by `ERA` rule)
- TODO comments must include a description (e.g. `# TODO: <description>` — `TD` rule enforced)
- No hardcoded secrets — use `detect-secrets` pre-commit hook
- Copyright header required in every file: `# Copyright Schneider Electric <year>`
- Max cyclomatic complexity: **10** (enforced by `complexipy`)
- Prefer list/dict/set comprehensions over explicit loops where idiomatic (`C4` rule)
- Use f-strings over `.format()` or `%` formatting
- Trailing commas required in multi-line structures (`COM` rule)

### TypeScript / JavaScript

- Use `bun` as the runtime and package manager
- Prefer `const` over `let`; avoid `var`
- Use strict TypeScript (`strict: true` in tsconfig)
- Named exports over default exports where possible

---

## Git & Version Control

- GPG commit signing is enabled (`gpgsign = true`)
- Do not commit `.env` files, secrets, or credentials
- Branch names: `feature/<description>`, `fix/<description>`, `chore/<description>`
- PRs use GitHub CLI: `gh pr create`

---

## Project-Specific Notes

- **Monorepo** (`one-analytics-mono`): workspace managed by `uv`, packages under `packages/`; tests under `tests/unit/one_analytics/<module_name>/`
- **one-analytics-core**: standalone package, uses `mypy` instead of `ty`
- **Integration tests** are excluded from default `pytest` runs (`--ignore=tests/integration`); run manually with `just integration-*`
- **Databricks**: deployments via Databricks Asset Bundles (`databricks bundle deploy`), wrapped in `just bundle_deploy_pr`
- **Notebooks**: ruff rule `E402` (module-level import not at top) is ignored for `notebooks/**/*.py`
