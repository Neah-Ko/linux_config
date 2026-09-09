---
name: repo-navigation
description: Navigate the one-analytics-mono monorepo without full-file reads. Use this skill whenever you need to locate, read, or edit code in one-analytics-mono — especially the ageing/GAF pipelines (ups_ageing, lvcb_ageing), cooling pipelines (cipp, climacheck), measurements_mock, analytics/ageing/publishing pipelines, their unit tests, shared test fixtures, or the CI/DABs/liquibase/pyproject/justfile configuration. Trigger on any mention of one-analytics-mono, edm_coefs_computation, GAF, ageing card, CIPP, climacheck, measurements mock, dabs, eph env, reusable.ci, or "where is X defined".
---

# one-analytics-mono navigation

Repo root: `/home/ejodry/Repositories/one-analytics-mono` (alt checkouts: `_2`, `_3`).

> `one-analytics-core` is **deprecated and being unplugged**. Do not port to it, do not read it, do not maintain parity with it.

## Read discipline (mandatory)

Half of all historical reads were whole-file reads of 500–4000-line files. Do not repeat that.

1. **Consult the index below first** — it gives line ranges for every hot symbol.
2. `read` with `offset`/`limit` around the target range (+/- 30 lines of slack). Never full-read a file over 300 LOC.
3. If the symbol is not indexed: `grep -n '^class |^def |^    def '` on the file, then read the window.
4. Use `workdir` on the bash tool. **Never** `cd X && cmd` (604 historical violations of this rule).
5. Prefer `rtk grep` / `rtk ls` / `rtk git` over raw equivalents — they are token-optimized.

## Package layout

| Package | src module path | unit tests |
|---|---|---|
| one-analytics-common | `packages/one-analytics-common/src/one_analytics/common/` | `tests/unit/one_analytics/common/` |
| one-analytics-edm-coefs-computation | `packages/one-analytics-edm-coefs-computation/src/one_analytics/edm_coefs_computation/` | `tests/unit/one_analytics/edm_coefs_computation/` |
| one-analytics-iot-observability | `packages/one-analytics-iot-observability/src/one_analytics/iot_observability/` | `tests/unit/one_analytics/iot_observability/` |
| one-analytics-security-observability | `packages/one-analytics-security-observability/src/one_analytics/security_observability/` | `tests/unit/one_analytics/security_observability/` |
| one-analytics-usage-analytics | `packages/one-analytics-usage-analytics/src/one_analytics/usage_analytics/` | `tests/unit/one_analytics/usage_analytics/` |

`iot-observability` is **excluded from the uv workspace** (it is a Spark Declarative Pipeline).

Below, `EDM/` abbreviates `packages/one-analytics-edm-coefs-computation/src/one_analytics/edm_coefs_computation/`
and `T/` abbreviates `tests/unit/one_analytics/edm_coefs_computation/`.

## Source index

Line ranges are the authoritative read targets. Load `reference/hot-files.md` for the full per-symbol map; the table below is the fast lookup.

| File | LOC | What it is |
|---|---|---|
| `EDM/analytics_pipeline.py` | 135 | Base framework: `AnalyticsPipelineConfig` (24), `StopConditionRule` (33), `AnalyticsPipeline` ABC (46) with `read_table`/`write_table`/`_drop_groups_matching_stop_conditions` (79) |
| `EDM/ageing_pipeline.py` | 609 | GAF ageing framework: `AgeingConfig` (59), `AgeingPipeline` (73) |
| `EDM/ups_global_score/ups_ageing.py` | 872 | `UpsAgeingPipeline` (73) |
| `EDM/circuit_breakers/lvcb_ageing.py` | 674 | `LvcbAgeingPipeline` (68) |
| `EDM/cooling/cipp_computation.py` | 1074 | `CippComputationConfig` (57), `CippComputation` (89) |
| `EDM/cooling/climacheck_computation.py` | 548 | `build_pov_paths` (83), `ClimacheckConfig` (170), `ClimacheckPipeline` (190) |
| `EDM/cooling/climacheck_worker.py` | 277 | executor-side UDF helpers, `get_apply_climacheck` (247) |
| `EDM/ups_global_score/battery_availability_coef.py` | 312 | `BatteryAvailabilityMonitoringPipeline` (46), `main` (286) |
| `EDM/ups_global_score/environmental_coef.py` | 368 | `TempAmbientMonitoringCoefPipeline` (40), `main` (342) |
| `EDM/mock/measurements_mock.py` | 2381 | synthetic UPS/CIPP/LVCB/Climacheck data generator, `generate` (2073) |
| `EDM/publishing/publishing_pipeline.py` | 305 | `PublishPipeline` (150) → Azure Event Hub |

### Most-used entry points

- `AgeingPipeline` (`ageing_pipeline.py`): `compute_rul` 218-297, `get_apply_gaf` 299-366, `compute_gaf` 368-383, `compute_ageing_maintenance_coef` 411-549, `prepare_output_for_coef_table` 551-593, `split_component_coefs` 595-599, `write_coef_tables` 601-609, `_build_commissioning_df` 144-176, `_drop_measures_predating_card` 84-117, `reduce_unindexed_to_first_index` 178-216. Constants 32-56 (`AGEING_THRESHOLD`, `RUL_LIFETIME_CAP_FACTOR`, `GAF_OUTPUT_SCHEMA` at 44).
- `UpsAgeingPipeline`: `prepare_gaf_computation` 191-465, `get_gaf_component_mapping` 467-530, `_parse_gaf_sub_component` 532-613, `map_gaf_output` 615-790 (two-pass), `run_job` 792-832. URN constants 37-61, `UPS_REQUIRED_GAF_INPUTS` 70.
- `LvcbAgeingPipeline`: `get_asset_type_ref` 74-143, `prepare_gaf_computation` 172-483, `get_gaf_component_mapping` 485-510, `map_gaf_output` 512-573, `run_job` 575-632. URN constants 23-53, `GAF_STATE_*` 59-65.
- `CippComputation`: `_sample_measures` 245-620, `prepare_cipp_df` 359-620, `get_apply_cipp` 620-760, `run_job` 760+, `_build_pov_start_times` 148-189, `_write_cipp_reference` 205-242.
- `ClimacheckPipeline`: `_build_configuration` 222-253, `_build_circuit_configs` 255-277, `_resolve_sub_pov_ids` 279-307, `transform` 427-497, `run_job` 497-548.
- `PublishPipeline`: `select_coefs_and_measures_for_run` 185-203, `join_with_exec_context` 205-224, `write_batch` 226-249, `run` 251-281.

## Test index

| File | LOC | Notes |
|---|---|---|
| `T/ups_global_score/test_ups_ageing.py` | 3228 | fixtures `exec_context_galaxy` (71), `exec_context_battery` (273); `test_prepared_gaf_input` 331-609, `test_apply_gaf` 920-1308, `test_mapping_gaf_output` 1309-1531, `test_compute_rul_ups` 1532-1676, `map_gaf_output` variants 2351-3055 |
| `T/circuit_breakers/test_lvcb_ageing.py` | 2577 | `test_prepared_gaf_input` 82-429, `test_apply_gaf` 1269-1536, `test_gaf_output_mapping` 1537-1952, `test_compute_rul_lvcb` 2025-2193 |
| `T/cooling/test_cooling_cipp_computation.py` | 3981 | 15 local fixtures at 55-536; `test_prepare_cipp_df*` 540-1469, `test_build_coef_table*` 1471-1550, `test_compute_monitoring_coef*` 1639-1741, e2e HVAC1 1742-1968 |
| `T/cooling/test_cooling_climacheck_computation.py` | 1007 | `_make_config` 31, `_ConcretePipeline` 47, `_make_input_pdf` 55; client tests 87-145, worker tests 153-349, pov-path tests 467-590, run_job tests 631-725, config tests 921-1007 |
| `tests/mixins/fixtures.py` | 793 | 33 schema fixtures + `spark` (62) + `make_schema`/`make_table`/`make_volume` (677/717/759) |

### Shared fixtures (from `tests/mixins/fixtures.py`, auto-imported by `tests/conftest.py`)

`spark` (62, session scope, local[1] UTC Arrow) · `exec_context_schema` (427) · `execution_context_schema` (399) · `exec_context_input_schema` (630) · `exec_context_output_schema` (444) · `coef_schema` (490) · `component_coef_schema` (502) · `global_coef_schema` (466) · `attention_global_coef_schema` (478) · `coef_mapping_schema` (455) · `coef_computation_schema` (606) · `gaf_prepared_schema` (514) · `gaf_prepared_lvcb_schema` (541) · `gaf_output_schema` (578) · `gaf_output_mapping_schema` (592) · `gaf_ageing_card_schema` (667) · `analytics_settings_schema` (658) · `normalized_mes_schema` (645) · `measures_normalized_schema` (370) · `normalized_silver_schema` (226) · `chiller_ctx_schema` (621) · `iot_msg_schema` (32) · `pme_measures_schema` (146) · `panel_server_measures_bronze_schema` (278) · `load_factor_schema` (128) · `delta_table` (101) · `catalog` (113) · `make_random` (118).

`tests/conftest.py` (45 LOC): sets `ONE_ANALYTICS_ENV_LEVEL`/`SPARK_MODE`/`AZURE_APP_CONFIG`/`STREAMING_MONITOR`, injects src dirs into `sys.path`, `from mixins.fixtures import *`, and skips `@pytest.mark.databricks` unless `ONE_ANALYTICS_SPARK_MODE=connect`.

**Never re-derive a schema by reading a test file — take the fixture from the list above.**

## Config cheatsheet

Load `reference/config.md` for full structure. Highlights:

- **`.github/workflows/[reusable].ci.yml`** (39 LOC) — `workflow_call` with one required input `package_name`; jobs `validate_dabs` (uses `./.github/actions/validate-dabs`) and `run_unit_tests` (uses `./.github/actions/run-unit-tests`), both on `linux` runner.
- **`.github/actions/deploy-eph-env/action.yml`** (78 LOC) — composite: checkout → setup uv + databricks CLI → `databricks bundle deploy -t dev-pr` (shared `eph_env`) → clone tables + copy checkpoints (idempotency flag stored in a secrets scope) → deploy package bundle → `liquibase-update`. Hardcoded: catalog `esxp_dev_pr`, schema prefix `pr${PR_NUMBER}_`, warehouse `esxp_dev_serverless_warehouse`, federated catalog `esxp_dev_metadata_federated`. `PR_NUMBER` from `github.event.number`.
- **`dabs/targets.yml`** (45 LOC) — permissions (CAN_MANAGE owner group + SP, CAN_VIEW users), presets tags + `name_prefix: [${var.env_name}]`, three production-mode targets: `dev` / `uat` / `prd` with distinct Azure workspace hosts.
- **`dabs/variables.yml`** (44 LOC) — `env_level`, `env_name`, `env_key` (all default `bundle.target`), `catalog_name` = `esxp_${var.env_level}`, `dedicated_cluster_id` (lookup `esxp_${env_level}_dedicated_cluster`), `analytics_cluster_pool_id`, `warehouse_id` (lookup `esxp_${env_level}_serverless_warehouse`), `service_principal_uuid` (`esxp-${env_level}-databricks`), `service_credential_name` (`esxp_${env_level}_databricks_svc`).
- **`packages/one-analytics-iot-observability/databricks.yml`** (103 LOC) — bundle `one_analytics_iot_observability`, CLI 0.299.1, legacy `run_as`, syncs monorepo root; 1 dashboard (CAN_READ `SG_esxp-dataviz-reader`), 1 Spark Declarative Pipeline (target schema `gold_observability`), 1 job on cron `0 0 1 * * ?`; uat/prd add failure email to `esxp.one.analytics.alert.and.notification@se.com`.
- **`pyproject.toml`** (231 LOC) — root is workspace-only. line-length 120; ruff selects 31 families (`N CPY F W E I UP C4 FA ISC ICN SIM TID PTH TD TC NPY ERA COM S ANN` + specific PL/B/RUF), ignores `TD002 TC002 N812 N814 N817 S403 S301`; per-file ignores for notebooks (`E402 S608 ERA001`), mock files (+`F821 E501 N806 S311`), tests (`S101`); copyright regex `Copyright (Schneider Electric <year>|<year> Schneider Electric)`; isort first-party `one_analytics`. `tool.ty` overrides silence `missing-argument`/`invalid-argument-type` for iot/usage/edm-coefs + tests. `tool.complexipy` max 10 over `packages, tests, notebooks`. `tool.codespell` ignores `persistance`. pytest `addopts = --import-mode=importlib`, marker `databricks`. dev group: codespell, complexipy, detect-secrets, pip, prek, pytest, ruff, rust-just, ty; `local-spark` group pins pyspark 4.1.3 (conflicts with the `databricks` extra).
- **`justfile`** (231 LOC, shell = pwsh) — `default` (az identity check), `ty <pkg>`, `test <pkg>`, `bundle_dabs <pkg> <validate|deploy|destroy>` (resolves PR via `gh pr view`, self-heals lineage mismatch, then `refresh_settings` for edm-coefs), `partial_run` (flags `--deploy --dry-run --auto --with-downstream --include-optional --no-prereq --help`, task keys resolved by `partial_run_select.py`), `agents`, `run_liquibase`, `init_pkg`, `refresh_settings` (MD5-gated refresh of `coef_mapping.csv` / `analytics_settings.csv`).
- **`liquibase/gold_analytics.changelog.sql`** (1498 LOC, 125 changesets) — do not read it whole. Order: 1-26 initial analysis/devices/timeseries tables; 28-127 constraint drops + `*2 → *` table swap migrations; 186-307 EDM coef tables (`execution_context`, `execution_context_input`, `execution_context_output`, `coef`, `global_coef`, `attention_global_coef`, `coef_mapping`, `analytics_settings`, all Delta + CLUSTER BY + CDF); 324-415 `computation_type` / `measurement_timestamp` additions + coef INT→STRING migration; 418+ materialized views `mv_structured_pov`, `mv_pov_specific_relation` and recursive view `v_pov_hierarchy` (needs `${FEDERATED_CATALOG}` substitution).

## Related skills

- `databricks` — query the data (`dbx`).
- `test-scoping` — pick the right tests for a diff and delegate to `@tester`.
