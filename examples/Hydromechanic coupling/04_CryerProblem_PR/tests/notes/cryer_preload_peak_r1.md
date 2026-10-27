# Cryer preload: bounded coarse peak window

Static preparation only. The author does not invoke prepare, solver, queue or Git. All old probe/half outputs, scripts, failure receipts and completed runs remain unchanged. This is one new fresh GPU calculation, not a PART restart or a rerun of the old coarse/half workers.

## Inputs and bounded scope

The XML is derived from `cryer_preload_probe_r1` with **only the TimeMax numerical value** changed: `.00830078125 -> .0703125 s = drainage start .0078125 + post-opening tau .0625`. Its description and the TimeOut description's frame count are synchronized to this 577-frame window; TimeOut's numerical value is unchanged. BAT changes only the test tag/output. Fixed dt stays 2^-21 s; ramp=2^-8 s, drainage start=2^-7 s, FixedGrid=1, output interval=2^-13 s stay unchanged. Expected 147456 steps and 577 native saves, including t=0, with nonzero saved step `part*256-1`.

Same canonical GPU Release, original FrDraw sphere R=.05/dp=.0025, k1e-5, raw confinement, grad1, damping coefficient .00004 and original viscosity. HG/SPR/shifting remain off. Float pore pressure/rate and density, double persistent stress and saved positions are unchanged. No production source, formal XML/BAT, geometry, material or boundary operator is edited. The longer time interval is the only physical history extension; no equilibrium state is manually assigned or reset. Expected GPU cost is about 4 h 45 min, not a timeout or forced termination rule.

Explicit preparation requires independently reviewed coarse offline safety/equilibrium and the new `cryer_preload_half_review_r1.check.json`: evidence consistency, original single-run safety, owned exits, original all-69-sample 5 Pa/.005 mm independent half screen and both four-closed-state five-metric diagnostics must pass. Missing/pending/failed prerequisites prevent sealing and execution. The completed coarse output hashes and failed original-analysis receipts remain bound; no old solver is rerun. Canonical executable/build/source/runtime, helpers, native reader and new files are hashed. The current equal CODEX thread/session identity is obtained only when the parent explicitly prepares.

Disk availability is checked read-only at preparation and again before launching. The budget estimates output size from retained coarse bytes scaled by 577/69, then requires twice that estimate plus 2 GiB margin. All raw BI4 files are retained; this is not permission to clean old data.

## Original safety and exact retained prefix

All 577 native frames independently retain finite state, 37173 unique unchanged native IDs, positive rho, no exclusions/plasticity, initial mass/h/dp, double saved position/stress flags, actual inward-load telemetry after t=0, radius<=.0525 m, the original mechanical dterror<=1e-14 and a separate original pore-diffusion dt check. Native time and zero-based saved step must match the binary grid exactly. Stress/pressure are converted to float64 only in temporary arithmetic arrays, avoiding zero-CSV int64 inference without modifying any numeric native value or metadata.

True FSType2/3 masks must be nonempty. Saved Part64 at tD is the verified last pre-opening state. At every saved t>tD, all true drained native pressures must be exactly zero. FSType changes remain recorded. Uniform full-load pressure/stress and displacement targets are used only as closed-initial-state diagnostics, **not** as post-opening uniform-field safety gates.

The complete retained coarse 69-frame prefix has identical dt, cadence and actual time/step. Compare **all 35 native reader columns** through exact little-endian float64 bit identity, including identity, physical fields, flags and **dterror**. There are **no excluded columns or interval-statistic exceptions**. A difference records part, actual time, field, count, first native ID and both values, then fails the prefix gate. No interpolation, nominal-index matching, relabeling or physical-field exception is allowed. The sealed old output hashes are verified before new execution.

Record the same five diagnostics on Parts61–64: pressure target RMS<=100 Pa; total-stress six-component target RMS<=100 Pa; speed maximum<=1e-5 m/s; fixed-origin single-scalar full-vector isotropic-fit RMS<=1e-5 mm; fixed outer-shell per-r0 inward target-error RMS<=1e-5 mm. Reference-volume weights, fixed 18-ID center, finite-Kw uniform targets and conditional content definitions match the qualified short probe. Passing them does not turn post-drain startup into a quasistatic exact solution. No drained theory function or old-peak comparison is included in this worker.

## Outputs and follow-up

Default invocation prints help. After static parent review, `--prepare` seals inputs and `--run` admits just one new GPU solver, refusing existing artifacts or active GPU solvers. New output is `tests/outputs/cryer_preload_peak_r1`; logs/input/run/status/completion/check/prefix receipts remain shallow under tests/logs; 577-row native summary CSV goes under tests/figures. Preserve every startup and tau sample without smoothing/filtering; tD is pre-open, not an already drained tau=0 sample. The summary retains center/whole pressure, stress, radial material response, density, load/moment and conditional-content observations.

Solver output hashes and independent physical completion are sealed before offline analysis. Analysis failure after normal completion requires offline analysis repair, never another solver. Runtime failure preserves actual output/error/traceback and stops only its owned wrapper tree. No timer kill, duplicate solver, overwrite, threshold relaxation or automatic smaller-step search. One terminal same-thread queue attempt is exclusive and nonretrying; do not rearm this or old workers or send connectivity tests.

Normal completion and all-sample safety/prefix identity mean a bounded coarse diagnostic is ready for independent causal/visual/theory review. They do not establish peak-window half convergence, full-cycle convergence, physical acceptance or automatic formal delivery. Root performs subsequent figures and actual-time theory/peak comparisons offline before any separately justified next action.
