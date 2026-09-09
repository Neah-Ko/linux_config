---
name: analytics-run-validation
description: Validate, compare or debug a One Analytics pipeline run in Databricks. Use whenever the user wants to verify a run_id, compare a PR/ephemeral run against a dev baseline, investigate missing or NULL coefs, check GAF ageing cards, audit execution_context coverage, or fetch job/task logs for an analytics job run. Trigger on "validate run", "compare run", "baseline vs PR", "A/B run", "why is coef missing", "check pr<N> output", "gaf_aging_card", "run_id <digits>", or any request to inspect gold_analytics results of a pipeline execution.
---

# Analytics run validation

Standard, repeatable procedure for answering "did this pipeline run produce correct output?".

All querying goes through the **`databricks` skill's `dbx` helper**. Load that skill for command syntax. **Never write Databricks connection code** — no `from databricks import sql`, no inline `python3 -c` connector, no hand-built warehouse HTTP paths. If `dbx` cannot express the probe, report the gap and stop.

## Hard contract

- **READ-ONLY.** `SELECT` / `SHOW` / `DESCRIBE` only. No `INSERT`, `UPDATE`, `DELETE`, `MERGE`, `DROP`, `CREATE`, no job triggers.
- Spark SQL on Delta — **not** ANSI/Postgres. See `databricks` skill `reference/spark-sql.md`.
- Always fully qualify: `catalog.schema.table`.
- Report findings as facts + numbers, then a short verdict. Do not speculate past the data.

## 1. Resolve the two environments

| Side | Catalog.schema | Notes |
|---|---|---|
| BASELINE | `esxp_dev.gold_analytics` | shared dev base |
| NEW / PR | `esxp_dev_pr.pr<N>_gold_analytics` | ephemeral clone, `{pr}` token resolves `<N>` |
| uat | `esxp_uat.gold_analytics` | default profile |
| prd | `esxp_prd.gold_analytics` | needs `--profile prd` |

Each side also needs a **run_id**. If the user gave only one run_id, find the counterpart:

```bash
dbx "SELECT run_id, MIN(_creation_date) AS started, COUNT(*) AS rows
     FROM esxp_dev.gold_analytics.execution_context
     GROUP BY 1 ORDER BY started DESC" --limit 10
```

## 2. Probe ladder

Run in order and stop as soon as the defect is localized. Steps 1–3 are one command each.

| # | Question | Command |
|---|---|---|
| 1 | Does the run exist and how wide is it? | `dbx runctx <run_id> --schema <S>` |
| 2 | Were coefs produced, and are they NULL? | `dbx coefs <run_id> --schema <S>` |
| 3 | Did GAF emit ageing cards? | `dbx card <run_id> --schema <S>` |
| 4 | What changed vs baseline? | `dbx diff` (see §3) |
| 5 | Why did a task fail? | job logs (see §4) |

Interpreting the probe packs:

- **`runctx`** → `context` (rows/roots/children/first_seen/last_seen), `roots_by_urn` (POV type coverage), `inputs`, `outputs`. Empty `inputs` with non-empty `context` = upstream measure join produced nothing.
- **`coefs`** → per `measurement_urn`: `n`, `povs`, `nulls`, `min_v`/`avg_v`/`max_v` across `coef`, `component_coef`, `global_coef`, `attention_global_coef`, `computed_measures`. A urn present in `component_coef` but absent from `global_coef` = roll-up (`coef_mapping`) gap. High `nulls` = stop-condition or missing input, not necessarily a bug.
- **`card`** → `cards`, `per_asset`. Missing cards for assets present in `runctx.roots_by_urn` = GAF never ran for them.

## 3. A/B comparison

Write a labelled batch file once, then diff it across the two sides. Parameterize with `${SCHEMA}` and `${RUN}`.

```sql
-- @coef_by_urn key=measurement_urn
SELECT measurement_urn, COUNT(*) AS n, COUNT(DISTINCT pov_id) AS povs,
       SUM(CASE WHEN measurement_value IS NULL THEN 1 ELSE 0 END) AS nulls,
       ROUND(AVG(measurement_value), 4) AS avg_v
FROM ${SCHEMA}.coef WHERE run_id = '${RUN}' GROUP BY 1 ORDER BY 1;

-- @coef_by_pov key=pov_id,measurement_urn
SELECT pov_id, measurement_urn, ROUND(measurement_value, 6) AS v
FROM ${SCHEMA}.coef WHERE run_id = '${RUN}' ORDER BY 1, 2;

-- @roots key=root_pov_urn
SELECT root_pov_urn, COUNT(DISTINCT root_pov_id) AS roots
FROM ${SCHEMA}.execution_context WHERE run_id = '${RUN}' GROUP BY 1 ORDER BY 1;
```

```bash
dbx diff probes.sql \
  --a SCHEMA=esxp_dev.gold_analytics            --a RUN=<baseline_run_id> \
  --b SCHEMA='esxp_dev_pr.pr{pr}_gold_analytics' --b RUN=<pr_run_id> --pr auto
```

Read the header line first: `rows: A=.. B=.. | only_A=.. only_B=.. changed=..`. `only_A` = regressions (lost rows), `only_B` = new output, `changed` = value drift. Raise `--max-diff` only when you need the full list.

Keep batch files in `/tmp/opencode/`.

## 4. Job / task logs

```bash
databricks jobs get-run <job_run_id> --profile dev -o json \
  | jq -r '.tasks[] | "\(.task_key)\t\(.run_id)\t\(.state.result_state)"'

databricks jobs get-run-output <task_run_id> --profile dev -o json \
  | jq -r '.notebook_output.result // .error_trace'
```

Note: the analytics **`run_id`** in `gold_analytics` is *not* the Databricks **job run id**. Map them via `execution_context._creation_date` vs the job run's start time, or via the job's returned notebook output.

## 5. Common findings

| Symptom | Likely cause | Next probe |
|---|---|---|
| `coef` rows exist, `measurement_value` all NULL | stop condition triggered (missing required input) | check `execution_context_input` urn coverage for those POVs |
| urn in `component_coef`, absent in `global_coef` | `coef_mapping` has no parent rule | `SELECT * FROM <S>.coef_mapping WHERE child_measurement_urn = '<urn>'` |
| `runctx.inputs` empty | measure join window / `remote_id`+`value_item_id` mismatch | probe `gold_core.normalized_cleaned_measures` for the run's time window |
| fewer roots in PR than baseline | clone drift, or a filter/stop-condition change in the PR | `diff` the `@roots` section |
| `aging_rul` huge/0 | RUL edge case (missing commissioning date) | inspect `gaf_aging_card` for the asset |
| PR schema missing tables | `ci_clone_tables` never ran for that PR | `dbx tables 'esxp_dev_pr.pr{pr}_gold_analytics' --pr auto` |

## 6. Reporting template

```
RUN: <run_id> @ <catalog.schema>   (BASELINE: <run_id> @ <catalog.schema>)
COVERAGE: <rows> ctx rows, <roots> roots, <n> POV types
COEFS: <urn> n=<n> povs=<p> nulls=<x> avg=<v>   (per relevant urn)
DELTA: only_A=<n> only_B=<n> changed=<n>
VERDICT: <ok | regression | inconclusive> — <one sentence>
EVIDENCE: <the 2-3 numbers that drove the verdict>
```
