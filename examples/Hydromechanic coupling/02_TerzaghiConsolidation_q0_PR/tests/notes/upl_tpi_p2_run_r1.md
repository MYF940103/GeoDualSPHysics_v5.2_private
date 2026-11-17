# P2 single-job owner r1

Author draft for complete root review. This note and runner do not create admissions, seeds or plans, and the author stage ran no prepare/build/help/GenCase/solver/native/VTK/Git or SHA scan.

New runner: `tests/support/upl_tpi_p2_run_r1.py`. Existing P1/M0 scripts, receipts, failures and intentionally retired long runs remain untouched. H3 remains HOLD. P2 retains the original source clock; it does not use endpoint reflection or the staged-load experiment.

## Profiles and immutable inputs

| mode | configuration / scheme | passed original M0 input/clock tag | updates / native files |
|---|---|---|---|
| `cpu_debug2ms` | DebugCPU / B | `upl_tpi_m0_dt_Bdebug2ms_CPU_r1` | 200 / 18 |
| `debug2` | Debug / B | `upl_tpi_m0_dt_Bdebug2_GPU_r1` | 2 / 2, compute-sanitizer memcheck |
| `Acontrol` | Release / A | `upl_tpi_m0_dt_Acontrol_GPU_r1` | 320 / 18 |
| `window2s` | Release / B | `upl_tpi_m0_dt_B10us_window2s_GPU_r1` | 199996 / 1263 |

B uses actual fixed dt `1.0000228881835938e-5 s = tD/1000`; A retains `6.250143051147461e-6 s`. The runner recomputes each scalar `time += dt` plan from the original XML, actual float TimeMax, nsteps upper cap and special cadence. It compares all eight original CSV fields at every planned save using their actual double bits.

Actual ends: CPU200 `0.002000045776367196 s`; GPU2 `2.0000457763671876e-5 s`; A320 `0.002000045776367195 s`; B2s `2.00000577545594 s`. These values are not rounded into a common CPU/GPU clock. In B2s TimeMax ends the run at 199996 before the 200000 upper cap. Drain event completed step1000 is pre-open; step1001 is post-open. The 1159 post-open saves / 11590 real drained receivers remain independently checked by native review.

The new program reads the original passed run's XML/BI4/NBI4 seed triplet and plan directly. Both original `.run.json` and `.native_review_m0_r1.json` must pass. The actual argv changes only output directory. No seed content or original physical configuration is rewritten, no GenCase is invoked, and no PART restart, preload, half, finer reference or full solve is added.

## P2 source and build binding

`source_build(ad,job,cfg)` retains the prior pure binding interface, returning `(build_stat, prepare_stat, program_stat, runtime_stats)`. It cannot accept a renamed P1 source.

| backend | actual preparation receipt | exact stage | private source root / file count |
|---|---|---|---|
| CPU | `logs/upl_tpi_p2_CPU_r1.prepare.json` | `upl_tpi_p2_r1.prepare` | `outputs/upl_tpi_p2_CPU_r1_source` / 267 |
| GPU | `logs/upl_tpi_p2_GPU_r2.prepare.json` | `upl_tpi_p2_gpu_prepare_r2.prepare` | `outputs/upl_tpi_p2_GPU_r2_source` / 270 |

Each build must be `logs/upl_tpi_p2_<configuration>_r1.build.json`, stage `upl_tpi_p2_build_r1`, matching configuration, actually passed, and `consumed_stats_unchanged=true`. Configurations still waiting for a build are never presumed passed.

The preparation must report exactly two matching host CPP changes plus the existing pressure-helper filename and `upl_tpi_m0_dt_r2.h`. It must retain other base files, spatial operators, CUDA/cuh, original four-phase bound arithmetic, material/J/HG update order, and original source clock. Public class/vtable and shared device/inline ABI changes are false; endpoint defects=2 and complete force calls=4. GPU additionally binds the 3850-byte unchanged device-visible prefix proof.

The runner pins the actual two CPPs, pressure helper, dt helper, prepare/build, program and runtime destinations. It does not rehash full source trees, old objects or raw arrays.

## Admission and explicit environment

Entry: `D:/anaconda3/python.exe -B tests/support/upl_tpi_p2_run_r1.py --admission PATH --execution-authorized`. Only the independently admitted 2s job may also use `--notify-admission PATH`. Each invocation launches at most one solver and never chains a reader or another job.

The run admission must have stage `upl_tpi_p2_run_r1.run_admission`, `passed=true`, `one_job_only=true`; `job={tag,mode,configuration,scheme,build}`, with `memcheck_program` additionally required for GPU Debug. A fresh tag must match `upl_tpi_p2_..._rN`.

`required_passed_checks` includes a real root source/build review. Additional order is CPU native, GPU Debug native, A native, then 2s. Each earlier new native review must have stage `upl_tpi_p2_native_r1.review`; its actual `job.mode`, not filename, supplies the gate. The runner checks already completed gates without starting them.

Before Popen the owner explicitly removes all five inherited prototype selectors, reconstructs the selected values, and records every actual value in start/call/run:

- `UPL_TPI_CPU_R1`, `UPL_TPI_GPU_R1`: only the selected backend is A or B; the other is absent.
- `UPL_TPI_M0_DT_R1`: B=`EQ40_RH1`; A absent.
- `UPL_TPI_P1_LOADCLOCK_R1`: always absent.
- `UPL_TPI_P2_ROWS_R1`: B=`2`; A absent.

CPU also fixes `OMP_NUM_THREADS=1`, `OMP_DYNAMIC=FALSE`; GPU records inherited OMP. A does not enable/parse P2, M0 or staged options and must create no UplTpi sidecar.

## Real ownership and failure preservation

CPU `own_solver`, GPU `run_owned`, and `notification` are literal copies of the reviewed P1 functions, with no monkeypatch. Real Popen handles, Win32 handles, creation FILETIME, exe/argv/parent, waits and exits are retained. GPU Debug separately captures sanitizer tool and genuine target; Release tool is solver. An unknown Debug target cannot be invented as zero solver invocations. An auditing exception waits only for an already created child; it never stops, retries or replaces it.

Another CPU solver rejects CPU launch. GPU only permits an exact root-admitted stopped GPU identity to remain untouched; it never stops/resumes C08 or changes dependencies.

Only new `tests/outputs/<tag>` is writable. Receipts are `logs/<tag>.start/.tool.start/.call/.run/.status.json` plus raw `.log`, and `.memcheck.log` for GPU Debug. Any existing output, partial, terminal or queue attempt rejects overwrite. Seed/plan stats are checked before and after. First actual error and last original console/Run.out PART are retained without inferring unsaved native time or reconstructing arrays.

## Runtime gates and independent native scope

The new checker never calls `old.check_output`. It verifies one normal Run.out completion, actual Steps/Excluded, Run.csv total1040/fixed40/no exclusion and every planned PART filename. CPU mode remains Pos-Double; GPU remains Pos-Cell. SavePosDouble is not an internal mode claim. Printed TimeMax is checked against the original 16-significant-digit formatter; true scalar/native clocks remain exact independently.

Physical HG retains two force calls, one predictor/corrector and two rate calls per complete step; two extra readonly endpoint forces do not advance HG. Original cache N+1/N-1, finite, max(dt/tau)<=0.2 and spin<0.01 gates remain. GPU B requires exactly one actual fresh-console 16-case device-fixture marker; A requires none. The marker is not asserted to reside in Run.out. Debug requires actual memcheck zero errors.

P2 pressure runtime checks are backend-specific policy/summary identities, alpha=.5, beta0, M0 and two rounds: commits=N; endpoint calls/writes=2N; first validations=N; core checks=14000N; readonly HG checks=4000N. CPU adds second starts=N. GPU adds pre/cor/J=N, first-row D2D copies=N, initial copy=1, second transitions=N and 1000*frames saved records per round.

The actual CPU round-count key is `endpoint_defects_per_step`; GPU uses `endpoint_defect_rounds`. CPU writes one 32-column `UplTpiP2CpuR1.csv`; GPU writes 32-column `UplTpiP2GpuR1.round1.csv` and `.round2.csv`. Runtime checks only headers and summary, avoiding a duplicate giant per-ID pressure scan. Independent new native review checks row formulas, first BC, second actual q, previous/history, actual saved data and exact lifecycle.

Round1 old finalP is explicitly stale, not p1. CPU first BC is directly captured; GPU first BC is the genuinely validated raw/+0 rule, not an extra native saved state. PorePressRate is the second-round scaled residual, not actual dp/dt. Metadata must explicitly reject literal-paper-LF, second-order, true-implicit and physical-acceptance claims.

`UplTpiP2DtR1` has an independent 21-column CSV. Every save checks four interval/cumulative phase counts and actual planned saved step/time/dt; summary requires pre/cor/endpoint1/endpoint2=updates=N. Every nonempty interval retains signed method-specific necessary-bound <=1e-14 and a positive finite selected bound. Initial DBL_MAX/-DBL_MAX extrema and unavailable HG reference remain explicit sentinels, not physical values; no native initial diagnostic is zeroed. Independent review still checks native signed bits against the four-phase maximum.

These runtime gates do not replace native all22 typed arrays, all1040 IDs, p0, J/n/rho/k ledger, actual source-clock drainage, scalar clocks, signed intervals or physical accuracy. A runtime pass means pending_native_review only, never full consolidation or long-run acceptance.

## Exact consumed-input collector

The root's deduplicated three-field stat list (path/bytes/mtime_ns) includes:

- This runner/note, imported `upl_tpi_m0_dt_run_r2.py`, actual `gpu.__file__` and `c.__file__`, and actual psutil module.
- Actual passed new build, its source_prepare/prepared, two host CPPs, pressure/dt helpers, program and all runtime.destination files.
- Selected original M0 run, native_review_m0_r1, plan and its three seed stats at their original paths.
- Every required_passed_checks receipt; compute-sanitizer for GPU Debug.
- If notifications are used: notify admission, actual Codex.exe, actual already-successful queue attempt/result proof.

Admission.pin records each consumed stat and checks it before start and seal. No new directory/SHA scan is introduced. The new run preserves source_build/source_prepare/program/runtime/reference_run/reference_native_review/prerequisite_reviews/clock/plan/seed/root_admission/actual_environment for explicit native binding; it never impersonates an old run stage.

## Optional single direct-owner notification

Only the root-admitted window2s owner may queue after sealing run/status. Notify admission binds actual current root thread, run-admission path, Codex executable and prior successful real queue proof; timeout45s, max_attempts1, watcher=false. Message text is fixed ASCII. Terminal, attempt and result are fresh files. Timeout may already have delivered, so no resend, rearm or connectivity test follows. Notification starts no solver/native/VTK/next case and is not a physical observation.
