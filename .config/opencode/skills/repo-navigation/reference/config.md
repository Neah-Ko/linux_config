# Config & infrastructure map — one-analytics-mono

Line numbers are for targeted `read` with `offset`/`limit`. Never read these files whole.

## `.github/workflows/[reusable].ci.yml` (39 LOC)

Reusable CI called per package by PR workflows.

| Lines | Content |
|---|---|
| 6-12 | `on.workflow_call.inputs.package_name` (string, **required**) |
| 14-15 | `permissions: contents: read` |
| 18-27 | job `validate_dabs` → `uses: ./.github/actions/validate-dabs` (L24) |
| 29-39 | job `run_unit_tests` → `uses: ./.github/actions/run-unit-tests` (L37) |

Runner label: `linux`. Both jobs run in parallel.

## `.github/actions/deploy-eph-env/action.yml` (78 LOC)

Composite action deploying the ephemeral PR environment.

| Lines | Step |
|---|---|
| 7-9 | input `package_name` (required) |
| 10-12 | input `ecoOs_devices_metadata_catalog` (required, from workflow vars) |
| 16-18 | checkout |
| 20-24 | setup uv + Databricks CLI |
| 26-35 | deploy shared `eph_env` bundle — `databricks bundle deploy -t dev-pr` |
| 37-53 | clone tables + copy checkpoints, guarded by a secrets-scope idempotency flag |
| 55-67 | deploy the package bundle, then set the secret flag |
| 69-78 | `liquibase-update` action with catalog/schema params |

Hardcoded values: catalog `esxp_dev_pr`, schema prefix `pr${PR_NUMBER}_`, warehouse
`esxp_dev_serverless_warehouse`, federated catalog `esxp_dev_metadata_federated`.
`PR_NUMBER` comes from `github.event.number`.

## `dabs/targets.yml` (45 LOC)

| Lines | Content |
|---|---|
| 7-13 | permissions — `CAN_MANAGE` owner group + service principal (L8-9), `CAN_VIEW` users (L12-13) |
| 15-26 | presets — tags (L16-24): project, target, git_branch, git_commit, env_*, is_monorepo_resource; `name_prefix: [${var.env_name}]` (L26) |
| 29-33 | target `dev` — host `https://adb-4440216167848243.3.azuredatabricks.net` |
| 35-39 | target `uat` — host `https://adb-4055073927002171.11.azuredatabricks.net` |
| 41-45 | target `prd` — host `https://adb-3829340242502612.12.azuredatabricks.net` |

All three targets use `mode: production`. `root_path` is built from bundle name +
target + `env_level` + `env_key` + `env_name`.

## `dabs/variables.yml` (44 LOC)

| Lines | Variable | Value / lookup |
|---|---|---|
| 7-9 | `env_level` | defaults to `bundle.target` (dev/uat/prd) |
| 11-13 | `env_name` | defaults to `bundle.target` (pr666/dev/uat/prd) |
| 15-17 | `env_key` | defaults to `bundle.target` |
| 19-21 | `catalog_name` | `esxp_${var.env_level}` |
| 23-26 | `dedicated_cluster_id` | lookup `esxp_${env_level}_dedicated_cluster` |
| 28-30 | `analytics_cluster_pool_id` | default `""` (ephemeral dev-pr only) |
| 32-35 | `warehouse_id` | lookup `esxp_${env_level}_serverless_warehouse` |
| 37-40 | `service_principal_uuid` | lookup `esxp-${env_level}-databricks` |
| 42-44 | `service_credential_name` | default `esxp_${env_level}_databricks_svc` |

## `packages/one-analytics-iot-observability/databricks.yml` (103 LOC)

The only Spark **Declarative Pipeline** package (excluded from the uv workspace).

| Lines | Content |
|---|---|
| 5-8 | bundle `one_analytics_iot_observability`, uuid `b37bc903-d743-4313-9edb-6e23521e2ea9`, CLI `0.299.1` |
| 10-14 | `include` shared dabs configs |
| 19-20 | `experimental.use_legacy_run_as: true` |
| 22-25 | `sync` from monorepo root |
| 27-31 | presets.tags — `flow: analytics`, `analytics_type: iot_observability` |
| 33-45 | dashboard — embed_credentials, warehouse_id, dataset catalog/schema, `CAN_READ` for `SG_esxp-dataviz-reader` |
| 47-60 | pipeline — run_as SP (L51-52), catalog + `schema_prefix: gold_observability` (L53-54), configuration passthrough (L55-57), notebook library (L59-60) |
| 62-86 | job — run_as SP (L65-66), parameters env_name/env_level/env_key/git_branch_name/git_hash (L68-78), quartz cron `0 0 1 * * ?` (L80-82), pipeline refresh task (L83-86) |
| 88-103 | targets uat (L90-95) / prd (L97-103) — failure email `esxp.one.analytics.alert.and.notification@se.com` |

## `pyproject.toml` (root, 231 LOC)

| Lines | Content |
|---|---|
| 19-29 | dev group — codespell, complexipy, detect-secrets, pip, prek, pytest, ruff, rust-just, ty |
| 32 | `local-spark` group — pyspark 4.1.3 (conflicts with the `databricks` extra) |
| 44-48 | workspace members `packages/*`, **excludes** `one-analytics-iot-observability` |
| 57-64 | uv `required-version >=0.9.30,<1.0.0`, `default-groups = [dev, local-spark]` |
| 65-80 | indexes — JFrog Artifactory default, aihub-common / aihub-externaloffers explicit |
| 87 | ruff `line-length = 120` |
| 92-122 | ruff select: `N CPY F W E I UP C4 FA ISC ICN SIM TID PTH TD TC NPY ERA COM S ANN PLR0124 RUF069 B006 PLE PLR0133 PLW1510 PLW1514` |
| 123-133 | per-file ignores — notebooks `E402 S608 ERA001`; mocks add `F821 E501 N806 S311`; `pr_config.py` `S404 S607 ANN401`; tests `S101` |
| 134-142 | global ignores `TD002 TC002 N812 N814 N817 S403 S301` |
| 145-146 | copyright regex `Copyright (Schneider Electric <year>|<year> Schneider Electric)` |
| 148-150 | isort first-party `one_analytics`, 2 lines after imports |
| 158-188 | `tool.ty` — silences `missing-argument` / `invalid-argument-type` for iot, usage, edm-coefs and tests; mock notebooks ignore `unresolved-reference` |
| 194-200 | codespell — skips `uv.lock`, `requirements.txt`; allows `persistance` |
| 205-217 | complexipy — `max-complexity-allowed = 10` over `[packages, tests, notebooks]` |
| 226-230 | pytest — `--import-mode=importlib`, marker `databricks` |

## `justfile` (root, 231 LOC, shell = **pwsh**)

| Lines | Target | Effect |
|---|---|---|
| 19-28 | `default` | Azure identity check (`az whoami` / `account show` / `ad signed-in-user`) |
| 30-35 | `ty <pkg>` | `uv run --package one-analytics-<pkg> ty check packages/one-analytics-<pkg>/src` |
| 37-43 | `test <pkg>` | `uv run --package one-analytics-<pkg> pytest tests/unit/one_analytics/<snake>` |
| 45-90 | `bundle_dabs <pkg> <validate\|deploy\|destroy>` | resolves PR via `gh pr view`, self-heals lineage mismatch, calls `refresh_settings` for edm-coefs |
| 92-169 | `partial_run` | flags `--deploy --dry-run --auto --with-downstream --include-optional --no-prereq --help`; task keys from `partial_run_select.py` |
| 171-173 | `agents` | team AI catalog (list / add / doctor) |
| 175-178 | `run_liquibase` | wraps `run_liquibase.ps1` with `schema_base` |
| 180-183 | `init_pkg` | `init_pkg.py` |
| 185-230 | `refresh_settings` | MD5-gated refresh of `coef_mapping.csv` / `analytics_settings.csv`; runs `refresh_configuration_tables` job only on checksum mismatch |

Also present: `test-all` (`uv run pytest tests/unit/`) and `ty-all`.

## `liquibase/gold_analytics.changelog.sql` (1498 LOC, 125 changesets)

**Never read whole.** Jump with `offset`/`limit`.

| Lines | Content |
|---|---|
| 1-2 | copyright header |
| 4-26 | boris.perevalov:1-8 — create analysis_results, analysis_runs, analysis_runs_logs, devices, element_stats, issue_types, issues, timeseries |
| 28-43 | david.lanckman — drop constraints |
| 45-127 | `*2 → *` table swap migrations (devices2→devices, etc.), column additions, transformer_metadata refactors |
| 186-307 | mohammed.haitof — create execution_context, execution_context_input, execution_context_output, coef, global_coef, attention_global_coef, coef_mapping, analytics_settings (Delta + CLUSTER BY + CDF) |
| 324-415 | add `computation_type` to coef_mapping; `measurement_timestamp` to coef/global_coef/attention_global_coef; coef INT→STRING migration |
| 418-500+ | lamine.aboubacar — mv_structured_pov, mv_pov_specific_relation, recursive view v_pov_hierarchy (needs `${FEDERATED_CATALOG}` substitution, references the `.advisor` schema) |

All changesets use `splitStatements:false`.

## `tests/conftest.py` (45 LOC)

Sets `ONE_ANALYTICS_ENV_LEVEL`, `SPARK_MODE`, `AZURE_APP_CONFIG`, `STREAMING_MONITOR`;
injects the workspace and package `src` dirs into `sys.path`;
`from mixins.fixtures import *`;
`pytest_collection_modifyitems` skips `@pytest.mark.databricks` unless
`ONE_ANALYTICS_SPARK_MODE=connect`.
