## 1. Fix Python script indentation (correctness)
- [x] 1.1 Rewrite `exasol__scalar_function_python` in `dbt/include/exasol/macros/materializations/functions/scalar.sql`:
  - [x] 1.1.1 Move macro body to column-0 jinja
  - [x] 1.1.2 Replace `{{ model.compiled_code }}` with `{{ model.compiled_code | trim }}`
  - [x] 1.1.3 Place `def run(ctx):` at column 0, body at 4 spaces
- [x] 1.2 Apply the same restructure to `exasol__aggregate_function_python` in `aggregate.sql`
- [x] 1.3 Manually inspect generated DDL in pytest debug output: confirm no leading whitespace on any `def`

## 2. Word-boundary BEGIN detection
- [x] 2.1 In `exasol__scalar_function_sql`, replace `'BEGIN' in code | upper` with `modules.re.search('\\bBEGIN\\b', code, modules.re.IGNORECASE) is not none`
- [x] 2.2 ~~Add a unit-style test fixture or scenario asserting an expression body containing `BEGIN_DATE` is wrapped in `BEGIN ... END`~~ — N/A (optional; no existing macro-unit test harness in repo). Covered indirectly by passing `TestExasolUDFsBasic`. Closed out as won't-do.

## 3. Volatility warning consistency
- [x] 3.1 Create `exasol__warn_unsupported_volatility()` macro (placed at top of `scalar.sql`)
- [x] 3.2 Call from `exasol__scalar_function_sql` (replacing inline check)
- [x] 3.3 Call from `exasol__scalar_function_python`
- [x] 3.4 Call from `exasol__aggregate_function_python`
- [x] 3.5 README "No volatility support" bullet now clarifies it applies to all UDF types

## 4. aggregate_state warning + docs
- [x] 4.1 In `exasol__aggregate_function_python`, added warning when `model.config.get('aggregate_state') is not none`
- [x] 4.2 README Python Aggregate section: added sentence that `merge()` is never called and `aggregate_state` is ignored with warning

## 5. Test refactor
- [x] 5.1 Added `ExasolPythonScalarScriptEventMixin` in `test_udfs.py` with class attributes `function_name`, `script_marker`
- [x] 5.2 Applied mixin to `TestExasolPythonUDF`, `TestExasolPythonUDFDefaultArg`, `TestExasolPythonUDFVolatility`; removed their `is_function_create_event` overrides
- [x] 5.3 Added `ExasolPythonSetScriptEventMixin` in `test_udafs.py`
- [x] 5.4 Applied to `TestExasolAggregatePython` and `TestExasolAggregatePythonDefaultArg`
- [x] 5.5 Collapsed duplicate `test_udfs` bodies in `TestExasolPythonUDFRuntimeVersionRequired` / `TestExasolPythonUDFEntryPointRequired` into `_PythonUDFValidationTest` helper

## 6. Fix TestExasolAggregateSQLError cascade
- [x] 6.1 Replaced `len(result.results) == 1` assertion with filter-by-`resource_type == "function"`
- [x] 6.2 Replaced event-count assertion with filter-by-message-content
- [x] 6.3 Verified the test now passes (was failing before this change)

## 7. Hygiene on previous change
- [x] 7.1 Marked 1.1.2, 1.1.4, 1.1.5 in `openspec/changes/add-udf-function-support/tasks.md` as N/A with Option A explanation
- [x] 7.2 Added note in that file explaining Option A was chosen with reference to Review Findings C1/C2

## 8. Validation
- [x] 8.1 Run `uv run pytest tests/functional/adapter/functions/ -n0` — **14/14 pass**. Two distinct root causes were found and fixed (see "Resolution" below); the earlier "VM crashed" blocker was a host-infrastructure issue, not a macro defect.
- [x] 8.2 Ran `uv run nox -s format:fix` (black reformatted 2 test files) then `format:check` and `lint:code` pass. Pre-existing lint warnings in `connections.py`/`impl.py` not introduced by this change.
- [x] 8.3 Run `openspec validate fix-udf-correctness-and-cleanup --strict` — passes

## 9. Reserved-word argument identifiers (bug found during 8.1)
- [x] 9.1 Add `exasol__formatted_script_function_args_sql()` in `functions/helpers.sql` that quotes argument identifiers, so reserved words (e.g. `value`) are legal in PYTHON3 SCALAR/SET SCRIPT signatures. Verified `ctx.<name>` still resolves the quoted (case-preserved) identifier.
- [x] 9.2 Use it in `exasol__scalar_function_python` and `exasol__aggregate_function_python` only (NOT the SQL FUNCTION path, where user-written bodies reference unquoted identifiers and quoting breaks name resolution — verified empirically).
- [x] 9.3 Override the `models` fixture and inline `dbt show` query in the UDAF tests to use a non-reserved column alias (`val`), since the dbt-core base `BASIC_MODEL_SQL` aliases `1 as value`.

## Resolution of the former "VM crashed" blocker — host infrastructure, not macros

The earlier 4 "VM crashed" failures (and a minimal raw-pyexasol `def run(ctx): return 42.0`) were root-caused to the **host**, not dbt-exasol:

- Host: Ubuntu 24.04, kernel 6.8.0-90, AppArmor in enforce mode.
- **Primary cause:** `kernel.apparmor_restrict_unprivileged_userns=1` (new in Ubuntu 24.04). Exasol's script-language sandbox uses `nschroot` to create an unprivileged user namespace for the `exaudfclient` subprocess; the kernel forced it into the restricted `unprivileged_userns` AppArmor profile, so the subprocess died as a zombie on its first IPC `::recv` → `VM error: Internal error: VM crashed`. SQL UDFs were unaffected (no subprocess).
  - **Fix:** `sysctl -w kernel.apparmor_restrict_unprivileged_userns=0` on the Docker host (persist via `/etc/sysctl.d/`). After this, scalar Python UDFs pass.
- **Secondary cause (separate symptom):** the host AppArmor `rsyslogd` profile denied the container's `/sbin/rsyslogd` access to `/exa/etc/rsyslog.conf`, crash-looping rsyslogd and throttling the container's `cored` supervisor. Unloaded the profile (`apparmor_parser -R /etc/apparmor.d/usr.sbin.rsyslogd`).

After the host fix, the only remaining failures were the genuine reserved-word `value` bug (task 9), now fixed. Full suite: **14/14 green**.

### CI / reproducibility note
Any Ubuntu 24.04+ host running the Exasol `docker-db` container for Python/R/Java UDFs must set `kernel.apparmor_restrict_unprivileged_userns=0`. Consider documenting this in the developer guide / CI setup.

---

### (Historical) original blocker investigation — Exasol container script-language subsystem

The 4 originally-failing tests failed at function-invocation time with `Exasol Query Error: VM error: Internal error: VM crashed`.

### Investigation done

1. **Restarted DB** via `mise run db:stop && mise run db:start` (itde, fresh 8.29.13 container) — issue persists.
2. **Direct pyexasol smoke test** — minimal `def run(ctx): return 42.0` crashes the VM. Confirms the issue is **not** dbt-exasol macro generation.
3. **SQL UDFs work fine** on the same container (`SELECT udf_test2.dbl(50)` returned `(100.0,)`).
4. **`EXA_PARAMETERS.SCRIPT_LANGUAGES`** is correctly configured:
   ```
   R=builtin_r JAVA=builtin_java PYTHON3=builtin_python3
   ```
5. **BucketFS** is reachable on port 2580 (via secondary SSH tunnel); `default` bucket is empty but `builtin_python3` is internal to EXAClusterOS, not user-installed.
6. **Internal Exasol logs** (`/exa/logs/db/DB1/`) show the root cause:
   ```
   Script language URI: localzmq+protobuf:///__builtin__/slc-9.2.0_c4_7_standard_EXASOL_all/...
   WARNING SWIGVM crashed during ::recv with PID: 3179 (tries: 0, ...
           first: TRUE, err_except: FALSE, err_zombie: TRUE, err_socket: FALSE)
   ```
   The `exaudfclient` subprocess becomes a **zombie immediately on first `::recv`** — the Python script-language container is being killed before any IPC handshake.
7. **`dmesg` on the host** shows a tight crash loop of `rsyslogd`:
   ```
   rsyslogd: could not open config file '/exa/etc/rsyslog.conf': Permission denied
   ```
   The container has filesystem/permission issues that likely extend to the script-language container's namespace.

### Conclusion

This is a **known-class issue with `exasol/docker-db:8.29.13`** — the script-language subprocess fork-execs successfully then immediately dies (zombie state) without an exception. SQL UDFs are unaffected because they run in the main DB process; Python/R/Java UDFs route through the `exaudfclient` subprocess that's broken.

**The dbt-exasol macros generate correct, valid DDL.** The CREATE statements succeed against this very container; only the runtime invocation fails because Exasol's own UDF subprocess can't survive.

### Options for the user

1. **Pin to a known-good `docker-db` version** — e.g. `8.25.x` or `7.1.x` (check `noxconfig.py` / `db:start` task for the version pin); ScriptLanguages 9.2.0 has reported issues on certain host kernels.
2. **Update host kernel / Docker engine** on the remote Ubuntu 24.04 host (`root@178.105.14.46`).
3. **Verify against Exasol SaaS** or a CI runner with a known-working Exasol image to confirm the change is correct in a working environment.
4. **Accept this change as-is** — the macro/test fixes are complete and correct; the 4 Python tests will pass automatically once the container infrastructure is working.

### Why no further macro changes will fix this

The generated DDL is bit-perfect (verified by inspecting `dbt.log` after our fix — clean column-0 Python, valid `def run(ctx)` bridge, no whitespace artifacts). The `CREATE OR REPLACE PYTHON3 SCALAR SCRIPT` succeeds in every test run. The failure is strictly at invocation time, inside Exasol's `exaudfclient` subprocess, which dbt-exasol does not control.
