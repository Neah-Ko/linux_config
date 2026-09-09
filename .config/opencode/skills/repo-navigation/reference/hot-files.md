# Full symbol map — one-analytics-mono hot files

`EDM/` = `packages/one-analytics-edm-coefs-computation/src/one_analytics/edm_coefs_computation/`
`T/` = `tests/unit/one_analytics/edm_coefs_computation/`

Read the indicated line window instead of the file.

---

## EDM/analytics_pipeline.py — 135 LOC
Base framework for analytics pipelines with stop-condition filtering and metric logging.

- 24-30 `AnalyticsPipelineConfig` — dataclass config base
- 33-43 `StopConditionRule` (frozen) — one stop rule: `missing_condition` + `reason`
- 46-78 `AnalyticsPipeline(ABC)`
  - 49-51 `.__init__(config, spark)`
  - 53-55 `.run_job()` — abstract
  - 57-58 `.read_table(path)` — Delta read by path
  - 60-77 `.write_table(df, output_table_path)` — write + log row count from Delta history
  - 79-135 `._drop_groups_matching_stop_conditions(df, group_key_columns, stop_condition_rules, prevented_action)`

Deps: `DeltaTable`, `get_spark`, `persist_if_supported`.

---

## EDM/ageing_pipeline.py — 609 LOC
GAF (Generalized Ageing Framework) degradation pipeline base.

- 32-42 constants `AGEING_THRESHOLD`, `RUL_LIFETIME_CAP_FACTOR`, `CONST_AGING_REF_DATE_URN`, other `CONST_*_URN`
- 44-56 `GAF_OUTPUT_SCHEMA`
- 59-71 `AgeingConfig(AnalyticsPipelineConfig)`
- 73-609 `AgeingPipeline(AnalyticsPipeline)`
  - 84-117 `._drop_measures_predating_card(measures_df, gaf_aging_card, measure_root_pov_id_col, measure_timestamp_col)`
  - 119-142 `._prepare_exec_context_and_card(exec_context_df, exec_context_input_df, gaf_aging_card_df)`
  - 144-176 `._build_commissioning_df(exec_context_input_df)` — commissioning / aging reference dates
  - 178-216 `.reduce_unindexed_to_first_index(df, group_cols, unindexed_flag_col, index_col)`
  - 218-297 `.compute_rul(df, commissioning_df)` — RUL per component + edge cases
  - 299-366 `.get_apply_gaf()` — pandas UDF for GAF inference, status-aware errors
  - 368-383 `.compute_gaf(df, run_id)` — `applyInPandas` + materialize
  - 385-393 `.log_and_filter_successful_gaf(gaf_output_df)`
  - 395-409 `.write_ageing_card(gaf_output_df, ageing_card_path)`
  - 411-549 `.compute_ageing_maintenance_coef(df, analytics_settings_df, exec_context_input_df)`
  - 551-593 `.prepare_output_for_coef_table(df, exec_context_output)` — URN resolution
  - 595-599 `.split_component_coefs(df)` — component-level vs aggregate
  - 601-609 `.write_coef_tables(df)`

Deps: `gaf` (`InitializeAgeingRequest`, `UpdateAgeingRequest`, `initialize_ageing`, `update_ageing`), `StopConditionRule`.

---

## EDM/ups_global_score/ups_ageing.py — 872 LOC
UPS ageing: battery temperature, SOC and state GAF inputs.

- 37-61 `*_URN` constants: `UPS_BRAND_URN`, `UPS_MODEL_URN`, `BATTERY_MODEL_URN`, `IOT_TEMP_URN`, `IOT_SOC_URN`, `AMBIENT_POV_URN`
- 60 `UPS_OPERATING_MODE` — battery discharge states; `GAF_STATE_CHARGING`
- 70 `UPS_REQUIRED_GAF_INPUTS`
- 73-832 `UpsAgeingPipeline(AgeingPipeline)`
  - 76 `ROOT_POV_URN` — UPS equipment POV URN
  - 79-104 `.get_asset_type_ref()` (cached)
  - 108-130 `.get_battery_type_ref()` (cached)
  - 133-162 `.get_battery_model_mapping()` (cached) — battery model URN → type
  - 164-189 `._filter_missing_required_inputs(df, required_cols, root_pov_id_col)`
  - 191-465 `.prepare_gaf_computation(execution_context_input_df, normalized_measures_df, gaf_aging_card_df, exec_context_df)`
  - 467-530 `.get_gaf_component_mapping()` — GAF component hierarchy → EDM urn
  - 532-613 `._parse_gaf_sub_component(df)` — parse GAF sub_component names
  - 615-790 `.map_gaf_output(df, exec_context)` — two-pass (single-level then nested) → `child_pov_id`
  - 792-832 `.run_job()`
- 835-872 `main()`

---

## EDM/circuit_breakers/lvcb_ageing.py — 674 LOC
Low-voltage circuit breaker ageing with GAF component mapping.

- 23-53 `LVCB_*_URN` (`LVCB_BRAND_URN`, `LVCB_RATED_CURRENT_URN`, …), `IOT_*_URN`, `IOT_URN_LIST`
- 59-65 `GAF_STATE_*` codes; `ANALYTICS_SETTING_CGL_ID`, `ANALYTICS_SETTING_SAL_ID`
- 68-632 `LvcbAgeingPipeline(AgeingPipeline)`
  - 71 `ROOT_POV_URN` — `lv_breaker_system`
  - 74-143 `.get_asset_type_ref()` — brand/range/model → asset_type
  - 145-170 `._log_gaf_input_coverage(pivoted_measures_df)` — warn on all-NaN inputs
  - 172-483 `.prepare_gaf_computation(execution_context_input_df, normalized_measures_df, gaf_aging_card_df, exec_context_df, analytics_settings_df)`
  - 485-510 `.get_gaf_component_mapping()` — GAF sub_component → EDM urn_key
  - 512-573 `.map_gaf_output(df, exec_context)`
  - 575-632 `.run_job()`
- 635-674 `main()`

---

## EDM/cooling/cipp_computation.py — 1074 LOC
CIPP compressor-performance pipeline; MLflow inference on cooling measurements.

- 48 `COOLING_COEF_EDM` · 51 `PARENT_POV_URN` (hvac root) · 54 `_INTERP_MAX_PERIOD_SECONDS` (2100 s)
- 57-87 `CippComputationConfig(AnalyticsPipelineConfig)`
  - 77-86 `.__post_init__()` — validates `end_date > start_date`
- 89-1074 `CippComputation(AnalyticsPipeline)`
  - 123-146 `.read_cipp_reference()` — None on first run
  - 148-189 `._build_pov_start_times(execution_context_df, cipp_reference_df)`
  - 191-203 `._get_global_measure_start(pov_start_times)`
  - 205-242 `._write_cipp_reference(inference_results)` — upsert
  - 245-620 `._sample_measures(df_measures, input_mappings, pov_start_times, inference_start, sampling_period_minutes)` — fixed-interval interpolation
  - 359-620 `.prepare_cipp_df(cipp_reference_df, normalized_measures_df, inference_start, input_mappings)`
  - 620-760 `.get_apply_cipp(pov_start_times, cipp_reference_df, inference_results)` — per-POV UDF
  - 760+ `.run_job()`

Deps: `InterpolationConfig`, `InterpolationType`, `interpolate_spark`, `cipp_paths`, `cipp_worker`.

---

## EDM/cooling/climacheck_computation.py — 548 LOC
Climacheck Azure Function integration; writes computed KPI results.

- constants: `_HVAC_ROOT_POV_URN`, `_REFRIGERANT_CIRCUIT_POV_URN`, `_INPUT_URN_ALLOWLIST`, `_CIRCUIT_CONFIG_NUMERIC_KEYS`, `_CIRCUIT_CONFIG_STRING_KEYS`, `COMPUTED_MEASURES_SCHEMA`
- 83-151 `build_pov_paths(ctx_df)` — HVAC sub-POV → ClimaCheck `edmPovPath` from chiller root
- 170-187 `ClimacheckConfig(AnalyticsPipelineConfig)`
- 190-548 `ClimacheckPipeline(AnalyticsPipeline)`
  - 204-210 `._read_execution_context_input()`
  - 212-220 `._read_pov_path_map()` — (chiller_id, edm_pov_path, resolved_pov_id)
  - 222-253 `._build_configuration()` — shared `circuits[].configuration` from analytics_settings
  - 255-277 `._build_circuit_configs()`
  - 279-307 `._resolve_sub_pov_ids(ok_df, path_map_df)` — chiller root pov_id → physical `child_pov_id`
  - 307-371 `._log_and_filter_on_status(df, status_col)`
  - 371-427 `._filter_by_measurement_urns(df)`
  - 427-497 `.transform(df)`
  - 497-548 `.run_job()`

Deps: `climacheck_worker` (`get_apply_climacheck`, `CLIMACHECK_WORKER_SCHEMA`).

---

## EDM/cooling/climacheck_worker.py — 277 LOC
Executor-side UDF helpers.

- 30-35 `__all__` · 39 `_EDM_POV_PATH_COL` · 43-52 `CLIMACHECK_WORKER_SCHEMA` · 54 `_WORKER_COLS` · 77-86 `_EMPTY_RESULT`
- 57-74 `_dump_climacheck_debug(dump_path, chiller_id, payload, response)`
- 89-244 `_apply_climacheck_on_group(pdf, run_id, last_compute_date, api_url, api_key, circuit_configs, debug_dump_path, debug_target_chiller_id)`
- 247-277 `get_apply_climacheck(...)` — per-chiller `applyInPandas` UDF with status-row errors

Deps: `ClimacheckClient`, `build_status_row`, `status_aware_udf` (`common.utils.spark_utils`).

---

## EDM/ups_global_score/battery_availability_coef.py — 312 LOC
- 47-52 `URN_VA`, `POV_URN_BAT`, `POV_URN_OUTPUT`, `SETTING_ID`, `OUT_MEAS_URN`, `URN_RATED_POWER`
- 46-90 `BatteryAvailabilityMonitoringPipeline(UpsDataPipeline)`
  - 54-58 `.__init__(config, spark)`
  - 60-90 `._drop_rows_missing_required_columns(df, requirements)`
  - 92-283 `.transform(df)`
- 286-312 `main()`

## EDM/ups_global_score/environmental_coef.py — 368 LOC
- 46-49 `POV_URN_UPS`, `POV_URN_UPS_UNIT`, `POV_URN_UPS_POWER`, `POV_URN_UPS_FRAME`
- 52-66 `INPUT_MEAS_URN`, `OUTPUT_MEAS_URN`, `HIGH_TEMPERATURE_COEF`, `LOW_TEMPERATURE_COEF`, `MAX_ACCEPTABLE_TEMPERATURE`, `MIN_ACCEPTABLE_TEMPERATURE`
- 40-339 `TempAmbientMonitoringCoefPipeline(UpsDataPipeline)`; `.__init__` 68-72; `.transform(df)` 74-339 (11 stages)
- 342-368 `main()`

---

## EDM/mock/measurements_mock.py — 2381 LOC
Synthetic UPS / CIPP(HVAC) / LVCB / Climacheck measurement generator driven by bundled CSV specs.

- 45-54 `_CIPP_*_POV_URN` (HVAC-1)
- 72-90 `_UPS_MISSING_PER_PHASE_DELEGATIONS` (76)
- 107-120 `_POV_TYPE_TO_POV_URN` (107)
- 135-139 `_UPS_AD_CONSTANT_SIGNALS`
- 156-245 `_LVCB_MOCK_PROFILES` (177), `_LVCB_SUBCOMPONENT_DEFS` (245)
- 248-300 `_MOCK_HVAC_ASSETS`, `_MOCK_HVAC2_ASSETS`
- other constants: `_CIPP_DAYS`, `_CIPP_SPACING_MINUTES`, `_UPS_DAYS`, `_UPS_SPACING_MINUTES`, `_LVCB_MOCK_ROOT_COUNT`, `_UPS_DISCHARGE_POINTS`
- 874-954 `generate_value(urn, pov_type, base_value)`
- 955-998 `_load_iot_delegations()`
- 999-1063 `_ups_value(urn, pov_type, base_value, discharge_active)`
- 1064-1159 `_build_missing_per_phase_rows(delegations, measurement_values)`
- 1160-1223 `_insert_lvcb_execution_context(...)`
- 1224-1362 `_insert_lvcb_execution_context_input(...)`
- 1447-1469 `_insert_hvac2_execution_context(...)`
- 1470-1603 `_insert_hvac2_execution_context_input(...)`
- 1604-1661 `_insert_hvac2_normalized_measures(...)`
- 1662-1677 `_insert_hvac1_execution_context_and_input()`
- 1678-2035 `_insert_hvac1_normalized_measures(...)`
- 2036-2072 `_generate_ope_ups_measurements(...)`
- 2073-2381 `generate(spark, run_id, start_date, end_date)` — orchestrator

Self-contained (no internal deps).

---

## EDM/publishing/publishing_pipeline.py — 305 LOC
Publishes coefs + computed measures to Azure Event Hub.

- 37-42 datamodel column aliases `CC`, `CMC`, `EC`, `GCC`, `ACC`, `CCC`
- 48-64 `_build_coef_with_offset(coef_context_df)`
- 67-79 `_aggregate_records_on_asset_and_measurements(with_offsets)`
- 82-97 `_build_time_series_per_asset(records_agg)`
- 100-119 `_build_entries(timeseries_per_asset)`
- 122-128 `_add_batch_id(coef_context_df, batch_size)`
- 131-147 `_collect_entries_as_json(entries)`, `build_bodies_from_context_df(coef_context_df)` (140-147)
- 150-281 `PublishPipeline`
  - 153-171 `.__init__(coef_table_name, computed_measures_table_name, cc_table_name, gc_table_name, ac_table_name, ec_table_name, run_id, spark)`
  - 173-183 `.connection_string`, `.dp_subscription_id` (cached properties, Azure secrets)
  - 185-203 `.select_coefs_and_measures_for_run()`
  - 205-224 `.join_with_exec_context(coef_df)` — adds `virtual_asset_id`
  - 226-249 `.write_batch(event_bodies)`
  - 251-281 `.run()`
- 283-305 `run_pipeline()`, `main()`

Deps: `azure.eventhub` (`EventData`, `EventHubProducerClient`), `databricks.sdk.WorkspaceClient`.

---

# Test files

## T/ups_global_score/test_ups_ageing.py — 3228 LOC
Local fixtures: `exec_context_galaxy` (70-271), `exec_context_battery` (272-330). Helper `sort_internal_arrays` (57-69).

- 331-609 `test_prepared_gaf_input`
- 610-707 `test_prepare_gaf_filters_measures_by_card_date`
- 708-816 `test_prepare_gaf_classifies_ta_by_ambient_pov_not_value_item_id`
- 817-919 `test_prepare_gaf_classifies_tbb_by_ups_bat_pov_not_value_item_id`
- 920-1308 `test_apply_gaf`
- 1309-1531 `test_mapping_gaf_output`
- 1532-1676 `test_compute_rul_ups`
- 1677-1715 `test__when_no_commissioning_date__compute_rul__should_drop_component`
- 1716-1821 `test_compute_ageing_maintenance_coef`
- 1822-1848 `test_build_commissioning_df_ups_custom_wins_and_fallback`
- 1849-1898 `test_compute_ageing_maintenance_coef_ups_custom_next_mnt_date_wins`
- 1899-1962 `test_compute_ageing_maintenance_coef_battery_system`
- 1963-2021 `test_compute_ageing_maintenance_coef_collapses_multi_parent_rows`
- 2022-2048 `test_prepare_output_for_coef_table_deduplicates_multi_parent_outputs`
- 2049-2089 `test_prepare_output_for_coef_table`
- 2090-2108 `test_split_component_coefs`
- 2109-2229 `test_battery_model_resolves_from_cabinet`
- 2230-2350 `test_battery_model_resolves_from_module`
- 2351-2410 `test_map_gaf_output_galaxy_vs_synthetic`
- 2411-2466 `test_map_gaf_output_battery_block_maps_to_both_battery_povs`
- 2467-2496 `test_map_gaf_output_new_power_module_children`
- 2497-2522 `test_map_gaf_output_standalone_dcfan`
- 2523-2642 `test_map_gaf_output_unindexed_gaf_matches_single_element_indexed_collection`
- 2643-2693 `test_map_gaf_output_unindexed_gaf_saves_first_index_of_multi_element_collection`
- 2694-2744 `test_map_gaf_output_unindexed_gaf_saves_first_index_powermodules`
- 2745-2795 `test_map_gaf_output_unindexed_gaf_stable_pick_among_null_index_siblings`
- 2796-3055 `test_map_gaf_output_easy_ups_3m_synthetic`
- 3056-3123 `test_ups_prepare_gaf_does_not_read_foreign_card`
- 3124-3155 `test_filter_missing_required_inputs_drops_groups_without_any_required_timeseries`
- 3156-3188 `test_filter_missing_required_inputs_checks_all_required_columns`
- 3189-3228 `test_prepare_output_for_coef_table_does_not_emit_battery_monitoring_urns`

Shared fixtures used: `spark`, `gaf_prepared_schema`, `gaf_output_schema`, `exec_context_schema`, `exec_context_input_schema`, `exec_context_output_schema`, `gaf_ageing_card_schema`.

## T/circuit_breakers/test_lvcb_ageing.py — 2577 LOC
Helpers `sort_internal_arrays` (43-62), `_lvcb_extra_required_rows` (63-81), `_battery_asset_constants` (430-481).

- 82-429 `test_prepared_gaf_input`
- 482-568 `test_prepare_gaf_abrasion_multi_phase_uses_max`
- 569-681 `test_prepare_gaf_logs_all_nan_input_coverage`
- 682-844 `test_prepare_gaf_filters_measures_by_card_date`
- 845-997 `test_lvcb_prepare_gaf_excludes_ups_root`
- 998-1140 `test_lvcb_prepare_gaf_drops_asset_over_max_rated_voltage`
- 1141-1268 `test_prepare_gaf_survives_child_pov_id_mismatch`
- 1269-1536 `test_apply_gaf`
- 1537-1952 `test_gaf_output_mapping`
- 1953-2024 `test_map_gaf_output_saves_first_index_of_multi_element_collection`
- 2025-2193 `test_compute_rul_lvcb`
- 2194-2341 `test_compute_ageing_maintenance_coef`
- 2342-2368 `test_build_commissioning_df_lvcb_custom_wins_and_fallback`
- 2369-2431 `test_compute_ageing_maintenance_coef_lvcb_custom_next_mnt_date_wins`
- 2432-2475 `test_prepare_output_for_coef_table`
- 2476-2497 `test_split_component_coefs`
- 2498-2577 `test_lvcb_prepare_gaf_shall_not_read_foreign_card`

Shared fixtures used: `spark`, `gaf_prepared_lvcb_schema`, `gaf_output_schema`, `exec_context_schema`, `exec_context_input_schema`, `exec_context_output_schema`, `gaf_ageing_card_schema`.

## T/cooling/test_cooling_cipp_computation.py — 3981 LOC
Local fixtures (55-536): `cipp_execution_context_schema` (55), `execution_context_input_schema` (71), `cipp_coef_setting_schema` (86), `normalized_cleaned_measures_schema` (98), `cipp_input_schema` (116), `cipp_output_schema` (129), `cipp_config` (140), `cipp_output_mock_df` (160), `exec_context_df` (190), `exec_context_input_df` (305), `exec_context_input_df_no_motor_speed` (369), `execution_context_output_schema` (417), `execution_context_output_df` (427), `measures_df` (458), `default_cipp_params` (536).

- 540-564 `test_prepare_cipp_df`
- 565-751 `test_prepare_cipp_df_ignores_incomplete_refrigerant_circuit`
- 752-1026 `test_prepare_cipp_df_prefers_primary_branches_over_null_fallback`
- 1027-1074 `test_prepare_cipp_df_hvac1_golden_snapshot`
- 1242-1279 `test_prepare_cipp_df_hvac2_only`
- 1280-1330 `test_prepare_cipp_df_mixed_hvac_and_hvac2_no_cross_contamination`
- 1331-1387 `test_prepare_cipp_df_hvac2_has_motor_speed_true/false`
- 1388-1421 `test_prepare_cipp_df_hvac2_ignores_incomplete_circuit`
- 1422-1469 `test_build_monitoring_coef_table_hvac2_output_routing`
- 1471-1489 `test_build_coef_table`
- 1490-1537 `test_build_coef_table_skip_rows_with_bad_inference`, `..._inference_raises_value_error`
- 1538-1637 `test_apply_cipp_on_group_runs`, `..._raises_value_error_on_group_with_no_matching_hvac_pov_id`
- 1639-1741 `test_compute_monitoring_coef` family (empty input, unsuccessful filter, max across components, dedup)
- 1712-1741 `test_compute_cipp_monitoring_coef_execution_context[_input]_validation`
- 1742-1968 `test_compute_cipp_monitoring_coef_end_to_end_hvac1`
- 3153-3190 `test_prepare_cipp_df_infer_model_files_variable_speed` / `_fixed_speed` / `_raises_on_mixed_speed`

## T/cooling/test_cooling_climacheck_computation.py — 1007 LOC
Helpers: `_make_config` (31-44), `_ConcretePipeline` (47-52), `_make_input_pdf` (55-79), `_pov_ctx_schema` (439), `_pov_path_map_schema` (453), `_worker_out_schema` (461), `_sample_configuration` (857), `_settings_schema` (921), `_make_settings_df` (929).

- 87-145 client tests: correct payload, empty items, HTTP error → `ClimacheckApiError`, chunking 150→2×100
- 153-349 worker tests: group-by-minute, response flattening, null filtering, pov_id uppercasing, empty input, empty API response → status row, API error → status row
- 314-438 `test_build_enriched_measures_*`: chiller-id grouping, urn allowlist filtering, wet-bulb precedence
- 467-524 `test_build_pov_paths_*`: dotted relation/index chain, verbatim index base, bare relation for unindexed
- 525-590 `test_resolve_sub_pov_ids_*`: child mapping + root fallback, no collision on same urn at different depth
- 591-630 `test_log_and_filter_successful_filters_diagnostic_rows_and_logs`
- 631-725 `test_run_job_returns_cleanly_when_no_inputs`, `..._writes_nothing_when_no_measures`, `test_warn_on_duplicate_keys_*`
- 726-856 `test_apply_climacheck_on_group_*`: direct EDM urn, logs errors but emits measurements, object-shaped errors, empty measurements list, pov_id == sent chiller_id
- 872-920 `test_apply_climacheck_on_group_circuits_*`: attaches circuits block, empty when chiller absent / no configs
- 945-1007 `test_build_configuration_maps_settings_to_api_keys`, `..._raises_on_missing_setting`, `test_build_circuit_configs_derives_circuit_ids_per_chiller`

Uses only the shared `spark` fixture.

## tests/mixins/fixtures.py — 793 LOC
- 26-28 `parse_timestamp(s)` — ISO → datetime
- 62-97 `spark` (session scope) — local[1], UTC, Arrow enabled, 1 partition, no UI
- Schema fixtures (line): `iot_msg_schema` 32 · `iot_msg_headers_decoded_schema` 47 · `load_factor_schema` 128 · `pme_measures_schema` 146 · `normalized_silver_schema` 226 · `flattened_pas_silver_schema` 257 · `panel_server_measures_bronze_schema` 278 · `measures_normalized_schema` 370 · `execution_context_schema` 399 · `exec_context_schema` 427 · `exec_context_output_schema` 444 · `coef_mapping_schema` 455 · `global_coef_schema` 466 · `attention_global_coef_schema` 478 · `coef_schema` 490 · `component_coef_schema` 502 · `gaf_prepared_schema` 514 · `gaf_prepared_lvcb_schema` 541 · `gaf_output_schema` 578 · `gaf_output_mapping_schema` 592 · `coef_computation_schema` 606 · `chiller_ctx_schema` 621 · `exec_context_input_schema` 630 · `normalized_mes_schema` 645 · `analytics_settings_schema` 658 · `gaf_ageing_card_schema` 667
- Utility fixtures: `delta_table` 101 · `catalog` 113 · `make_random` 118
- Databricks factories with cleanup finalizers: `make_schema` 677 · `make_table` 717 · `make_volume` 759
