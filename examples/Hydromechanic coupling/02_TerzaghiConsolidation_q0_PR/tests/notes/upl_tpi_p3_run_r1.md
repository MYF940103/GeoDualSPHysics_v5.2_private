# P3 single-job owner r1

Author-only draft for complete root review. No context/admission evaluation, prepare, build, help, GenCase, solver, reader, VTK, queue, Git or SHA action was executed. Only new `tests/support/upl_tpi_p3_run_r1.py` and this note are authored. Frozen P2 and public source/dependencies remain untouched.

The runner is a local clone of the actually reviewed P2 owner and schema with explicit new P3 source/sidecar identities. CPU own_solver, GPU run_owned and notification functions are literal copies; no runtime monkeypatch or old-stage impersonation is used.

## Four unchanged, independently gated profiles

| mode | configuration / scheme | immutable original seed/clock run tag | actual updates / saves |
|---|---|---|---|
| `cpu_debug2ms` | DebugCPU / B | `upl_tpi_m0_dt_Bdebug2ms_CPU_r1` | 200 / 18 |
| `debug2` | Debug / B | `upl_tpi_m0_dt_Bdebug2_GPU_r1` | 2 / 2; compute-sanitizer memcheck |
| `Acontrol` | Release / A | `upl_tpi_m0_dt_Acontrol_GPU_r1` | 320 / 18 |
| `window2s` | Release / B | `upl_tpi_m0_dt_B10us_window2s_GPU_r1` | 199996 / 1263 |

B actual fixed dt remains `1.0000228881835938e-5 s = tD/1000`; A remains `6.250143051147461e-6 s`. Actual ends remain CPU200 `.002000045776367196 s`, GPU2 `2.0000457763671876e-5 s`, A320 `.002000045776367195 s`, and B2s `2.00000577545594 s`. The B2s nsteps upper cap is200000, but TimeMax stops first at199996. The original special-cadence plan, step1000 pre-open, step1001 post-open and1159 post-open saves/11590 real zero-pressure receivers are unchanged.

No seed or plan is generated/copied/rewritten. XML/BI4/NBI4 triplet, plan and the original passed run/native qualification are consumed at their original stats. The runner independently regenerates the expected scalar `time += dt` plan from the original XML and actual float TimeMax/cap/event, then compares every original eight-column value. It never substitutes n*dt or aligns CPU/GPU near times. Original argv changes only its output directory; only the new actual program changes.

Each action requires its own new root admission. CPU first; GPU Debug additionally requires completed new CPU native review; A requires CPU/GPU Debug native reviews; B2s requires all three. The prerequisite stage is `upl_tpi_p3_native_r1.review` and actual mode comes from its job.mode. Required checks do not launch prerequisites. There is no automatic next job, decode, reference, half or full solve.

## New P3 source/build identity

Pure `source_build(ad,job,cfg)` retains the return `(build_stat,prepare_stat,program_stat,runtime_stats)` for the new native wrapper. Build must be `logs/upl_tpi_p3_<cfg>_r1.build.json`, stage `upl_tpi_p3_build_r1`, actual passed, matching configuration and unchanged consumed stats.

Source preparation must be `logs/upl_tpi_p3_CPU_r1.prepare.json` or `logs/upl_tpi_p3_GPU_r1.prepare.json`, both stage `upl_tpi_p3_source_r1.prepare`, with actual source roots `outputs/upl_tpi_p3_CPU_r1_source` (267 files) / `outputs/upl_tpi_p3_GPU_r1_source` (270 files). It must bind this P3 closure rather than renamed P2 receipts.

Exact changed_sources contains only JSphCpuSingle.cpp or JSphGpuSingle.cpp. Exact recompile_sources contains the corresponding base CPP and Single CPP because both consume new private headers. changed_headers remains old pressure-helper filename and upl_tpi_m0_dt_r2.h. The original base CPP body, spatial/CUDA/cuh/unrelated files, shared device/inline and public/vtable ABI must be unchanged; GPU device-visible prefix proof remains3850 bytes. Preparation must retain material/J/HG order and original source clock, and report endpoint_defect_rounds3 / actual_full_forces5 / five-phase original bound arithmetic.

The owner explicitly pins these four actual source files, prepare/build, program and all runtime destinations. It never scans/hash-checks every raw array or old object. A successful source/build record cannot count as a solver/native/physical pass.

## Admission and selectors

Interface: `D:/anaconda3/python.exe -B tests/support/upl_tpi_p3_run_r1.py --admission PATH --execution-authorized`. Only window2s may add an independently reviewed `--notify-admission PATH`.

Run admission stage is `upl_tpi_p3_run_r1.run_admission`, passed/one_job_only true; job contains tag/mode/configuration/scheme/build and GPU Debug memcheck_program. Tag must be fresh `upl_tpi_p3_..._rN`. Required earlier reviews must already pass.

Before launching the owner clears all six inherited prototype keys and records actual values in start/call/run: UPL_TPI_CPU_R1, UPL_TPI_GPU_R1, UPL_TPI_M0_DT_R1, UPL_TPI_P1_LOADCLOCK_R1, UPL_TPI_P2_ROWS_R1, UPL_TPI_P3_ROWS_R1. B sets only its backend=B, M0=EQ40_RH1, P3_ROWS=3; P1/P2 and other backend remain absent. A sets only backend=A; M0/P1/P2/P3 remain absent and no new sidecar is allowed. The source's A branch short-circuits without parsing P3.

CPU keeps OMP_NUM_THREADS1/OMP_DYNAMICFALSE. GPU records inherited OMP without replacing unrelated environment. No staged-load, reflection, new coefficient, physical dt/space/HG/SPR/AV/damping/material or BC change is introduced by this owner.

## Actual ownership, once-only termination and preservation

The literal P2 ownership functions retain actual Popen and native Win32 handles, creation FILETIME, exe/argv/parent identities, waits and exits. CPU is a direct child; GPU Debug captures both actual compute-sanitizer tool and live solver target before exit. Release tool is solver. Unknown target identity never becomes a fabricated zero invocation. Audit failure only waits for an already created original child; there is no stop, resume, restart, retry or replacement.

CPU rejects another CPU solver. GPU only allows an exact root-admitted stopped GPU identity (including paused C08 where applicable), matching PID/create time/exe/argv and real stopped status. It neither modifies nor touches that dependency. Any other active/unadmitted GPU rejects launch.

Only a new outputs/tag directory, fresh raw log and fresh start/tool.start/call/run/status/memcheck receipts may be written. Existing output/partials/terminal/queue attempts reject. Native files and original failures remain protected. The first actual error and last original console/Run.out PART are reported without inventing an unsaved failure time/state. Input stats are verified before start and final seal.

## Runtime checks and P3 evidence

The standalone checker preserves Run.out normal exit/steps/no exclusion, Run.csv1040/40/noout and exact planned PART presence. CPU is original Pos-Double; GPU is original Pos-Cell, not inferred from SavePosDouble. Printed TimeMax is compared with the original16-significant-digit text rounding; actual clocks remain independently native-checked.

Original physical HG is unchanged: forcecalls2N, predictor/correctorN, ratecalls2N, cache N+1/N-1, finite/max(dt/tau)<=.2/spin<.01. Three readonly endpoint evaluations must not be counted as physical HG updates. Actual GPU B console must contain the unchanged genuine16-case fixture marker exactly once; A none. GPU Debug memcheck must have zero errors.

P3 pressure runtime gate requires the actual backend policy/summary stage, alpha.5/beta0/M0, three defects, commitsN, endpointcalls/writes3N, provisional_validations/endpoint_transitions2N, core checks21000N and readonly HG checks6000N. CPU first/second validations eachN; both provisional BCs are real captures and q2=p1/q3=p2. GPU has pre/cor/J=N, provisional D2D copies2N, initial provisional copies2, saved1000*frames per round and actual q2/q3 metadata. All paper-LF/second-order/true-implicit/physical acceptance flags remain false.

CPU emits one32-column UplTpiP3CpuR1.csv: the validation column is provisional_endpoint_validation_count,0 initially and2 after complete steps. GPU emits three32-column UplTpiP3GpuR1.round1/2/3.csv. Their literal header arrays are exposed as CPU_PRESSURE_HEADER/GPU_PRESSURE_HEADER. First and second old-final fields remain stale prior commits, never fabricated p1/p2. Actual final rate is the original scaled R3 at actual p2, not R(p3) or dp/dt. The owner only checks pressure headers/summary; row formulas and native association are independently reviewed once later.

UplTpiP3DtR1 has23 columns, exposed as DT_HEADER. Each saved row checks five real interval/cumulative counts, actual part/step/time/dt and empty status. Summary requires all five stages=N, actual end, original Rh1 necessary-bound semantics and signed maximum<=1e-14. Original initial empty DBL_MAX/-DBL_MAX and unavailable HG-reference sentinels are retained; raw initial native signed values are not rewritten. The future native reviewer must replay the genuine five-phase signed record. Old P1-loadclock/M0/P2 sidecars are rejected, not accepted under a new label.

No old check_output is delegated. All22 native arrays/1040IDs/P0/J/n/rho/k/ledger/drainage/actual clocks/signed/HG/elastic safety and original pressure/top/bottom/100Pa physical budgets remain independent pending checks. Normal owner success means pending_native_review only.

## Consumed-input collector and output schema

Root inputs are the deduplicated actual path/bytes/mtime_ns entries for this runner/note, imported M0 run_r2 and its actual gpu/c helpers, actual psutil; selected new build/prepare/twoCPP/pressure+dt header/program/runtime; original profile run/native review/plan/three seed stats; required completed new native gates; and compute-sanitizer for GPU Debug. No file is supplied by a guessed stage or historic filename alone.

Result retains source_build/source_prepare/program/runtime/reference_run/reference_native_review/prerequisite_reviews/clock/plan/seed/root_admission and all six actual selectors for the new native get_job. It includes new five-phase runtime flags rather than fake four-phase/one-row acceptance. New sidecar stat collection does not duplicate full pressure CSV numerical analysis or native decode.

For the separately admitted2s action only, after run/status sealing the same direct owner may queue once using the verified current root thread, actual Codex program and prior successful queue attempt/result proof. Notify stage upl_tpi_p3_run_r1.notify_admission requires max_attempts1, timeout45s, watcherfalse and matching run admission. The actual message is ASCII. Terminal/attempt/result are new; timeout may have delivered and is never resent/rearmed/self-tested. Queueing launches no reader, solver, half, full, other case or Git action.
