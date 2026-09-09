---
name: databricks
description: Query and explore Databricks tables in the dev environment (Schneider Electric). Use this skill whenever the user wants to run SQL against Databricks, describe table schemas, fetch sample data, discover tables, or write algorithms grounded in real data from the esxp_dev / esxp_dev_pr / esxp_uat / esxp_prd catalogs. Trigger on any mention of Databricks, esxp_dev, esxp_dev_pr, esxp_uat, esxp_prd, ephemeral / PR environments, gold_analytics, gold_core, POV, run_id, coef, execution_context, or normalized_cleaned_measures.
---

# Databricks Data Assistant

Explore and query Databricks (catalogs `esxp_dev`, `esxp_dev_pr`, `esxp_uat`, `esxp_prd`) via the `dbx` helper. Never re-write connection boilerplate — the helper handles auth, interpreter, and formatting.

## Run queries with `dbx`

Invoke the helper in this skill directory (resolve `SKILL_DIR` from this file's path):

```bash
"$SKILL_DIR/dbx" <command> [args] [flags]
```

It reads `~/.databrickscfg` (profile `dev` by default). The default warehouse reads `esxp_dev`, `esxp_dev_pr` and `esxp_uat` (one workspace/metastore). `esxp_prd` is a **separate** workspace — query it with `--profile prd` (its warehouse is selected automatically). Always fully qualify tables as `catalog.schema.table`.

| Command | Purpose |
|---|---|
| `dbx "SELECT ..."` | raw SQL (`;`-separated multi-statement); bare `SELECT` gets `LIMIT 100` unless `--no-limit` |
| `dbx schemas <catalog>` | list schemas |
| `dbx tables <catalog.schema> [like]` | list tables, optional substring filter |
| `dbx desc <catalog.schema.table>` | columns + types (authoritative — prefer over memory) |
| `dbx sample <catalog.schema.table> [N]` | first N rows (default 10) |
| `dbx count <catalog.schema.table> ["where"]` | row count |
| `dbx pr` | print resolved PR number |
| `dbx batch <file.sql>` | run a labelled multi-query script (see below) |
| `dbx diff <file.sql\|SQL> --a K=V --b K=V` | run the same script twice with two variable sets and diff the rows |
| `dbx runctx <run_id>` | execution-context probe pack (context, roots_by_urn, inputs, outputs) |
| `dbx card <run_id>` | GAF ageing-card probe pack (cards, per_asset) |
| `dbx coefs <run_id>` | coef probe pack (coef, component_coef, global_coef, attention_global_coef, computed_measures) |

Flags (anywhere): `--json` `--csv` `--limit N` `--no-limit` `--max-col N` `--profile P` `--warehouse ID` `--pr N|auto` `--repo DIR` `--var/-v K=V` (repeatable) `--schema catalog.schema` `--key c1,c2` `--max-diff N` `--sql-a SQL` `--sql-b SQL`.

### Variables — `--var/-v K=V`

Any `${KEY}` in SQL (raw, batch or diff) is substituted. Repeatable. An undefined `${KEY}` is a hard error, never a silent empty string.

```bash
dbx -v S=esxp_dev.gold_analytics -v RUN=63883032058341 \
  "SELECT COUNT(*) FROM \${S}.execution_context WHERE run_id='\${RUN}'"
```

### `batch` — labelled query packs

A batch file is plain SQL split by `-- @label` markers (optional `key=` for diffing):

```sql
-- @counts
SELECT COUNT(*) AS n FROM ${SCHEMA}.execution_context WHERE run_id = '${RUN}';

-- @roots key=root_pov_urn
SELECT root_pov_urn, COUNT(DISTINCT root_pov_id) AS roots
FROM ${SCHEMA}.execution_context WHERE run_id = '${RUN}'
GROUP BY 1 ORDER BY 1;
```

```bash
dbx batch probes.sql -v SCHEMA=esxp_dev.gold_analytics -v RUN=63883032058341
```

Each section prints under a `== label ==` header.

### `diff` — baseline vs PR A/B comparison

Runs the *same* script under two variable sets and reports the delta per label:

```bash
dbx diff probes.sql \
  --a SCHEMA=esxp_dev.gold_analytics    --a RUN=63883032058341 \
  --b SCHEMA=esxp_dev_pr.pr271_gold_analytics --b RUN=988418113258792
```

Output per label: `rows: A=.. B=.. | only_A=.. only_B=.. changed=..` then `-A …` / `+B …` / `~ <key> <col>: a -> b` lines (capped at `--max-diff`, default 20). Rows align on the section's `key=` columns; without a key it degrades to a set diff. `--key c1,c2` overrides the file. `--sql-a` / `--sql-b` compare two *different* queries instead.

### Probe packs — `runctx` / `card` / `coefs`

Pre-baked labelled batches for the standard run-validation ladder. Target schema comes from `--schema` (or `DBX_SCHEMA`, default `esxp_dev.gold_analytics`); `{pr}` works inside it.

```bash
dbx runctx 63883032058341
dbx coefs  988418113258792 --schema 'esxp_dev_pr.pr{pr}_gold_analytics' --pr auto
```

## Environment model (catalogs & schemas)

Environments map to Unity Catalog catalogs. Every environment holds the **same 6 schemas**: `operational`, `bronze_core`, `silver_core`, `gold_core`, `gold_analytics`, `gold_observability`.

| Environment | Catalog | Profile | Schema pattern | Example |
|---|---|---|---|---|
| dev (shared base) | `esxp_dev` | default (`dev`) | `<schema>` | `esxp_dev.gold_analytics.coef` |
| uat | `esxp_uat` | default (`dev`) | `<schema>` | `esxp_uat.gold_analytics.coef` |
| prd | `esxp_prd` | `--profile prd` | `<schema>` | `esxp_prd.gold_core.normalized_cleaned_measures` |
| PR ephemeral | `esxp_dev_pr` | default (`dev`) | `pr<N>_<schema>` | `esxp_dev_pr.pr233_gold_analytics.coef` |

**Only `esxp_prd` needs `--profile prd`** (it lives in a separate workspace); `esxp_dev`, `esxp_dev_pr` and `esxp_uat` are all served by the default `dev` warehouse:

```bash
dbx sample esxp_uat.gold_core.normalized_cleaned_measures 5           # default profile
dbx --profile prd schemas esxp_prd                                    # prd workspace
dbx --profile prd sample esxp_prd.gold_core.normalized_cleaned_measures 5
```

Key facts (source: `one-analytics-mono/dabs/{variables,targets}.yml`, `dabs/eph_env/*.yml`):

- **PR/ephemeral data lives in its own catalog `esxp_dev_pr`, never in `esxp_dev`.** All PRs share that one catalog; they are isolated by the `pr<N>_` **schema prefix**, not by catalog.
- PR schemas are **clones** of the `esxp_dev` base, produced at env-creation by the `ci_clone_tables` job (`esxp_dev.<schema>` → `esxp_dev_pr.pr<N>_<schema>`). So `esxp_dev_pr.pr<N>_gold_analytics` mirrors `esxp_dev.gold_analytics`.
- Column layout is identical across environments — use the base `esxp_dev` schemas or `dbx desc` to learn columns without needing a live PR.

### The `{pr}` token

`{pr}` in any SQL/table arg expands to the current PR number, resolved from cwd via `gh pr view` → branch name → `--pr`/`DBX_PR`. **PR schemas always resolve against `esxp_dev_pr`:**

```bash
dbx --pr auto tables 'esxp_dev_pr.pr{pr}_gold_analytics'
dbx --pr auto count  'esxp_dev_pr.pr{pr}_gold_analytics.coef' "measurement_value IS NULL"
```

Run PR-scoped commands from inside the relevant repo checkout so `{pr}` resolves (or pass `--pr N` / set `DBX_PR`).

## Inspect job / task run output

The `dbx` helper is for SQL only. To read notebook task outputs from a job run, use the `databricks` CLI directly (profile `dev`).

1. List all task run IDs (and keys) for a job run:

    ```bash
    databricks jobs get-run <job_run_id> --profile dev -o json \
      | jq -r '.tasks[] | "\(.task_key)\t\(.run_id)"'
    ```

2. Get the output of a single task from its task run ID:

    ```bash
    databricks jobs get-run-output <task_run_id> --profile dev -o json \
      | jq -r '.notebook_output.result // .error_trace'
    ```

`.notebook_output.result` holds a successful task's returned value; `.error_trace` is the fallback shown when the task failed.

Dump every task's output in one pass:

```bash
for rid in $(databricks jobs get-run <job_run_id> --profile dev -o json \
    | jq -r '.tasks[].run_id'); do
  echo "=== task run $rid ==="
  databricks jobs get-run-output "$rid" --profile dev -o json \
    | jq -r '.notebook_output.result // .error_trace'
done
```

**SQL dialect:** queries are Spark SQL on Delta (not ANSI/Postgres). See `reference/spark-sql.md` for gotchas (`explode` aliasing, `VALUES`, typed literals, casts).

## Behavior

- **Never write Databricks connection code.** Do not `from databricks import sql`, do not read `~/.databrickscfg` yourself, do not build `/sql/1.0/warehouses/...` HTTP paths, do not define ad-hoc `def q(cur, s)` helpers in an inline `python3 -c` / heredoc. Every SQL need is covered by `dbx` (`batch` for multi-query, `--var` for interpolation, `diff` for A/B, probe packs for run validation). **If `dbx` genuinely cannot express what you need, say so explicitly and stop — do not re-implement the connector.**
- **Always run queries** for data/schema — never guess. Use `dbx desc` before writing algorithms.
- **Discover first** for unknown tables: `dbx schemas` → `dbx tables` → `dbx desc`.
- Keep result sets small (default LIMIT / `sample` / `count`); widen only when asked.
- READ-ONLY by default: `SELECT` / `SHOW` / `DESCRIBE` only. Never `INSERT`, `UPDATE`, `DELETE`, `MERGE`, `DROP`, `CREATE` unless the user explicitly asks.
- On connection error: surface the exact message and check `~/.databrickscfg` (profile `dev`) and warehouse reachability.

## Domain glossary

- **Data flow:** raw device messages → bronze → silver → `gold_core` (normalized measures) → `gold_analytics` (coefficients, execution contexts, scores).
- **POV** (Point of View): hierarchical analytics computation node.
- **run_id**: key for one analytics computation batch.
- **remote_id + value_item_id**: identifies a device measurement channel.
- **measurement_urn**: semantic URN of what is measured.
- **coef**: analytics score (0..1) for a POV/measurement (may be NULL).

Detailed column snapshots for the `gold_analytics` / `gold_core` tables: see `reference/tables.md` (load only when needed; `dbx desc` is authoritative for live/PR schemas).

**Validating a pipeline run (baseline vs PR)?** Use the `analytics-run-validation` skill — it wraps these primitives into a standard probe ladder.
