---
name: test-scoping
description: Decide which tests and quality gates to run in the one-analytics-mono repo after a code change, and delegate the run to the @tester subagent. Use whenever the user asks to run tests, run affected tests, run ruff/ty/complexipy/codespell, verify a change, or asks "which tests cover this file". Trigger on "run tests", "affected tests", "unit tests", "pytest", "ruff", "ty check", "lint", "quality gate", "pre-push", or after editing any file under packages/.
---

# Test scoping (one-analytics-mono)

Pick the **narrowest** test/lint target that still covers the change, then hand it to `@tester`. Never run tests yourself.

## 1. Map source → test

```
packages/<pkg>/src/one_analytics/<module>/<sub>/X.py
        →  tests/unit/one_analytics/<module>/<sub>/test_X.py
```

| Package | `<module>` | tests root |
|---|---|---|
| one-analytics-common | `common` | `tests/unit/one_analytics/common/` |
| one-analytics-edm-coefs-computation | `edm_coefs_computation` | `tests/unit/one_analytics/edm_coefs_computation/` |
| one-analytics-iot-observability | `iot_observability` | `tests/unit/one_analytics/iot_observability/` |
| one-analytics-security-observability | `security_observability` | `tests/unit/one_analytics/security_observability/` |
| one-analytics-usage-analytics | `usage_analytics` | `tests/unit/one_analytics/usage_analytics/` |

**Exceptions**

- Cooling tests carry a `cooling_` infix:
  - `cooling/cipp_computation.py` → `.../cooling/test_cooling_cipp_computation.py`
  - `cooling/climacheck_computation.py` → `.../cooling/test_cooling_climacheck_computation.py`
- `tests/mixins/fixtures.py` is **shared** — a change there affects *every* package → run `tests/unit/`.
- `tests/conftest.py` change → run `tests/unit/`.
- `one-analytics-iot-observability` is excluded from the uv workspace (Spark Declarative Pipeline).
- Worker modules pair with their pipeline's test file (e.g. `cooling/climacheck_worker.py` is covered by `test_cooling_climacheck_computation.py`).

If the mapping is uncertain, locate the covering test by symbol instead of guessing:

```bash
rtk grep -n "FunctionOrClassName" tests/unit
```

## 2. Choose the scope

| Change | Target |
|---|---|
| one source file | its single test file |
| one subpackage (e.g. `ups_global_score/`) | `tests/unit/one_analytics/<module>/<sub>/` |
| base class / framework (`ageing_pipeline.py`, `analytics_pipeline.py`) | all subclasses' test files (ups, lvcb, cooling) |
| shared fixtures / conftest / pyproject | `tests/unit/` |
| docs, yml, md only | no tests — run lint gates only |

Prefer `-k <expr>` over a whole file when a single behaviour changed.

## 3. Delegate to `@tester`

`@tester` runs `$HOME/.config/opencode/run-tests.sh` **exactly once** with the args you supply, and returns a fixed STATUS/PASSED/FAILED/LOG/FAILURES summary.

Template:

```
@tester run: tests/unit/one_analytics/edm_coefs_computation/ups_global_score/test_ups_ageing.py -k "map_gaf_output"
Context: changed UpsAgeingPipeline.map_gaf_output in packages/one-analytics-edm-coefs-computation/src/one_analytics/edm_coefs_computation/ups_global_score/ups_ageing.py
```

Rules:
- Pass **paths and flags only** — `run-tests.sh` already supplies `-q --no-header --tb=line -rf -p no:cacheprovider`.
- One invocation per request. If it fails, fix the code, then delegate a fresh run.
- Never add `-x`/`-v`/`--cov` unless the user asked.

## 4. Quality gates

`$HOME/.config/opencode/run-checks.sh` wraps ruff / ruff-format / ty / complexipy / codespell with the same log+tail contract.

```bash
run-checks.sh                  # all gates, whole repo
run-checks.sh --changed        # only .py changed vs origin/main
run-checks.sh --changed ruff format
run-checks.sh ty
```

Also delegate these to `@tester`. Run gates **before** asking for a review or a PR.

Repo config that drives the gates (`pyproject.toml`): line-length 120; ruff selects `N CPY F W E I UP C4 FA ISC ICN SIM TID PTH TD TC NPY ERA COM S ANN …`; copyright header required (`Copyright Schneider Electric <year>`); `from __future__ import annotations` mandatory (FA); `pathlib` over `os.path` (PTH); full type annotations (ANN); complexipy max complexity **10**; tests are exempt from `S101`.

## 5. Native runners (only when `@tester` is unavailable)

```bash
just test <package-name>     # uv run --package one-analytics-<pkg> pytest tests/unit/one_analytics/<module>
just ty   <package-name>
just test-all                # uv run pytest tests/unit/
```

`@pytest.mark.databricks` tests are auto-skipped unless `ONE_ANALYTICS_SPARK_MODE=connect`.
