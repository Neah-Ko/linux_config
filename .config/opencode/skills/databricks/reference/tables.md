# Core table reference (`esxp_dev` / `esxp_uat` / `esxp_prd` / `esxp_dev_pr`)

Load on demand. Columns are identical across environments; PR ephemeral schemas live in `esxp_dev_pr` as `pr<N>_<schema>` (clones of the `esxp_dev` base). For live/PR schemas always prefer `dbx desc <catalog.schema.table>` — this file is a convenience snapshot, not authoritative.

## gold_analytics.execution_context
Analytics runs and their POV hierarchy.

| Column | Type | Notes |
|---|---|---|
| run_id | string | run key |
| root_pov_id / parent_pov_id / child_pov_id | string | POV hierarchy ids |
| root_pov_urn / parent_pov_urn / child_pov_urn | string | POV hierarchy urns |
| virtual_asset_id | string | |
| pov_index | integer | index in hierarchy |
| pov_relation_name | string | relation between POVs |
| _creation_date | timestamp | |

## gold_analytics.execution_context_input
Inputs consumed by a run.

| Column | Type | Notes |
|---|---|---|
| run_id | string | |
| root_pov_id / parent_pov_id / child_pov_id | string | |
| input_type | string | e.g. measurement, config |
| measurement_urn | string | |
| remote_id | string | device id |
| value_item_id | string | topic |
| value | string/double | |

## gold_analytics.execution_context_output
Outputs produced by a run.

| Column | Type |
|---|---|
| run_id | string |
| root_pov_id / parent_pov_id / child_pov_id | string |
| measurement_urn | string |

## gold_analytics.coef
Computed coefficients per POV/measurement (UPS Global Score).

| Column | Type | Notes |
|---|---|---|
| run_id | string | |
| pov_id | string | |
| measurement_urn | string | |
| measurement_value | double | coefficient (0..1); may be NULL |
| last_compute_date | timestamp | |
| measurement_timestamp | timestamp | source measure ts |

## gold_core.normalized_cleaned_measures
Main time-series table (cleaned/normalized device measures).

| Column | Type | Notes |
|---|---|---|
| id | string | row id |
| remote_id | string | device id |
| value_item_id | string | topic/channel |
| value_numeric | double | |
| value_string | string | |
| timestamp | timestamp | |
| quality | string | quality flag |
| _annotations | struct | processing metadata |

`_annotations` fields: publication_timestamp, kafka_timestamp, raw_timestamp, silver_timestamp, bronze_timestamp, gold_timestamp, message_id, comment, source, value_date, applied_scaling_factor.

---

## Coef family (all share the same 6-column shape)

`gold_analytics.component_coef`, `global_coef`, `attention_global_coef`, `computed_measures` have **exactly the same columns as `coef`**: `run_id`, `pov_id`, `measurement_urn`, `measurement_value` (double), `last_compute_date`, `measurement_timestamp`.

| Table | Clustered by | Typical `measurement_urn` |
|---|---|---|
| `coef` | pov_id, measurement_urn, run_id | `…:me:aging_rul`, `…:me:health_coef`, `…:me:bat_availability_monitoring_coef`, `…:me:cipp_monitoring_coef`, `…:me:load_ratio_monitoring_coef`, `…:me:ope_mode_monitoring_coef`, `…:me:temp_ambient_monitoring_coef` |
| `component_coef` | pov_id, measurement_urn, run_id | `…:me:aging_coef`, `…:me:maint_coef`, `…:me:health_coef`, `…:me:env_monitoring_coef`, `…:me:io_monitoring_coef`, `…:me:usage_monitoring_coef` |
| `global_coef` | pov_id, measurement_urn, run_id | `…:me:aging_global_coef`, `…:me:maint_global_coef`, `…:me:health_global_coef`, `…:me:env_global_monitoring_coef`, `…:me:io_global_monitoring_coef`, `…:me:usage_global_monitoring_coef` |
| `attention_global_coef` | pov_id, measurement_urn, run_id | `…:me:attention_global_coef` (single urn) |
| `computed_measures` | — | pipeline-computed physical measures (e.g. Climacheck KPIs) |

URN prefix is always `edm:def:core:me:`. Values are usually 0..1 except `aging_rul` (days, up to ~10950).

## gold_analytics.gaf_aging_card
Ageing card blobs returned by the GAF model, one per asset per run.

| Column | Type | Notes |
|---|---|---|
| run_id | string | execution context instance |
| asset_id | string | POV the card is calculated on |
| aging_card | string | serialized card returned from GAF |
| _creation_date | timestamp | |

## gold_analytics.analytics_settings
Tunable thresholds, keyed by POV definition. Clustered by `pov_urn`, `id`.

| Column | Type | Example |
|---|---|---|
| id | string | `aging_rul_0.25`, `maint_rul_min`, `ups_availability_min` |
| value | string | stored as string — cast on read |
| pov_urn | string | `edm:def:core:sys_pov:esx:eqt:elec:ups` |

## gold_analytics.coef_mapping
Declares how child coefs roll up into parent coefs. Clustered by `pov_urn`, `measurement_urn`.

| Column | Type | Notes |
|---|---|---|
| pov_urn | string | parent POV definition |
| measurement_urn | string | e.g. `edm:def:core:me:health_global_coef` |
| child_pov_urn | string | |
| child_measurement_urn | string | |
| computation_type | string | `global`, `attention_global`, … |

## gold_analytics.mv_structured_pov
Materialized POV catalogue.

| Column | Type |
|---|---|
| pov_id | char(36) |
| pov_facet_id | char(36) |
| pov_definition_urn | string |
| pov_name | string |
| pov_virtual_asset_id | string |

## gold_analytics.mv_pov_specific_relation
Instance-level POV edges.

| Column | Type |
|---|---|
| id | char(36) |
| source_pov_facet_id | char(36) |
| component_relation_id | char(36) |
| target_pov_facet_id | char(36) |
| target_pov_facet_index | int |

## gold_analytics.mv_component_relation
Definition-level relation metadata (cardinality rules).

| Column | Type |
|---|---|
| id | char(36) |
| pov_definition_urn / pov_urn | string |
| relation / type / description | string |
| required / multiple | boolean |
| min_items / max_items | int |
| requirement_id | char(36) |

## gold_analytics.v_pov_hierarchy
Recursive view flattening the POV tree. Each `*_pov` column is a struct — access with dot notation (`root_pov.pov_urn`).

| Column | Type |
|---|---|
| root_pov / parent_pov / child_pov | struct<pov_id, pov_urn, pov_name, pov_virtual_asset_id> |
| pov_relation_name | string |
| pov_index | int |
| level_from_root | bigint |

## gold_analytics.analysis_runs
Job-level run tracking (security-observability flow). Clustered by `parameters.site_id`.

| Column | Type | Notes |
|---|---|---|
| job_id / run_id | string | |
| current_status | string | |
| started_at | timestamp | |
| parameters | struct<site_id, period_start, period_end> | |
| error_ui_message / error_description | string | |
| error_context | map<string,string> | |

> `gold_analytics.reference_date` **does not exist** — do not query it.
