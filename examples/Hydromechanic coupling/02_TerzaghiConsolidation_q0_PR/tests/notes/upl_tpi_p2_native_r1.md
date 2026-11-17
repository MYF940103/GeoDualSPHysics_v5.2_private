# P2 independent native read and two-round review

Status: author preparation only. This file and `support/upl_tpi_p2_native_r1.py`
introduce no solver, build, decoder invocation, numerical change or acceptance.
The root must separately review and admit each `read` or `review` action.
All old sources, programs, runs, raw particle files and derived attempts stay unchanged.

## Reused implementation and exact profiles

The only reader implementation is the already built
`outputs/upl_tpi_m0_dt_native_r1_build/upl_tpi_m0_dt_native_r1.exe`.
Its actual build, runtime dependencies and genuine tool exits are pinned through
`upl_tpi_m0_dt_native_identity_root_r1.review.json` and the existing `pin_reader`
functions. There is no new C++ copy or reader build. The original completion stage,
22 typed arrays, 1040 original IDs, fixed markers, ledger, P0/J/n/rho, FS drainage,
geometry, clock and signed dterror checks are unchanged.

The exact four reader profiles remain: CPU Debug B 200 updates / 18 frames;
GPU Debug B 2 updates / 2 frames under actual memcheck; GPU Release default A
320 updates / 18 frames; and one GPU Release B 199996 updates / 1263 frames.
B uses event/1000, A event/1600, with the original immutable seed and eight-column
scalar-accumulated clock plan. Event 1000 or 1600 is pre-open. No interpolated time,
renumbered step, extra reference, half-step chain or automatic full run is introduced.

`get_job` consumes the real P2 runner stage `upl_tpi_p2_run_r1.run`, original
start/call/root admission, owned creation time, executable/argv, actual Win32/Popen
exits, source preparation/build, program, runtimes and seed/plan stats.
It delegates exact CPU-r1/GPU-r2 P2 build provenance to that runner's `source_build`.
All five tracked selectors and CPU thread selectors must match the real call/start.
B requires its backend selector B, `UPL_TPI_M0_DT_R1=EQ40_RH1` and
`UPL_TPI_P2_ROWS_R1=2`; the staged P1 load-clock selector stays absent.
A has no pressure/P2/method sidecar and does not enter the new branch.
The runner's real output, HG, fixture and memcheck checks are repeated read-only.

## Separate actions and products

Each action requires `--execution-authorized --admission PATH`.
The admission has stage `upl_tpi_p2_native_r1.read_admission` or
`upl_tpi_p2_native_r1.review_admission`, `passed=true`, `action_only=true`,
`job.tag`, and unique stat-bound `inputs` for every actually consumed file.
Imports and shared identity/helper notes are explicit inputs, not invented receipts.

A unique read creates `<tag>_native_p2_r1` under `tests/outputs` and
`logs/<tag>.native_p2_r1.json`. Its real tool call/log retain the implementation's
`<tag>.native_m0_r1.call.json` and `.native_m0_r1.log` names. Existing output,
call, log, failed or partial records prohibit a repeated read. A real active-reader
check precedes the tool. No VTK or next action is invoked.
A separately admitted review consumes that successful actual read and creates
`logs/<tag>.native_review_p2_r1.json`. It launches no reader or other program.
Failures preserve the original first error and all partial products.

## Pressure row transaction review

CPU owns one actual 32-column CSV: initial round 0 has one row per material ID;
noninitial rows are interleaved round 1 then round 2 per ID. Initial round 0 is
not an endpoint observation. GPU owns two 32-column files; both initial records
have `has_endpoint_observation=0`. Column names come directly from the P2 runner.
GPU first `final_field` remains the previous committed value; it is never relabelled
as p1. GPU `validated_BC_value` is the value whose real device BC predicate passed,
not an extra native save. CPU first actual p1 is captured directly after BC validation.

For all saved pairs and all 1000 soil IDs, the reviewer checks actual clocks and
round counts; one shared pn/previous/prediction/half/Jn/Jhalf/Jfull/theta-half state;
q1 from the original alpha=.5 history prediction and actual endpoint BC;
raw1 = RN-float(q1 + R1/S1), then true BC; q2 bit-equal to this actual validated p1;
raw2 = RN-float(q2 + R2/S2), then true BC; and native final pressure bit-equal to p2.
A true drained row has S=R=0 and positive zero. No row is removed or regularized.
R1 and R2 remain independently observed complete endpoint residuals, not a doubled
first correction. No condition assumes the second correction must shrink.

CPU float conversion follows the original RN-f32 arithmetic. GPU float input/output
casts reproduce the retained CUDA object's actual RN plus signed subnormal FTZ;
PTX and its real tool/compile/source-object/link evidence are reused without another
dump, hash scan or CUDA execution. Double division/addition are unchanged.
The original J formula is checked exactly once from dt, Jhalf and theta-half.
Only its two already qualified final CUDA multiply/add contraction paths are allowed,
with no ULP or Pa tolerance. Endpoint theta2 is not substituted for theta-half.
First lap/rate are not observed or reconstructed. Saved PorePressRate is the final
endpoint's legacy scaled residual diagnostic, not actual dp/dt.
Saved history is checked where observed; no unsaved history oracle is claimed.

## Independent counts, method intervals and default A

The pressure summaries require N unique history commits, 2N actual endpoint calls
and writes, N first validations and second transitions, 14000N core comparisons,
and 4000N read-only HG history/rate comparisons. GPU additionally checks its actual
first-row D2D counts, one initial D2D copy and saved records per round.
The original physical HG 2N force/rate counts, N/N predictor/corrector updates,
cache, finite, dt/tau and spin guards stay unchanged; extra endpoint HG is read-only.

The independent 21-column P2 method CSV has four real force phases per update.
Every noninitial interval count and all cumulative counts, actual clock/step/dt,
selected minimum and signed dt-minus-bound are replayed exactly against native.
The initial empty interval and native signed diagnostic remain untouched.
DBL_MAX HG-reference is an explicitly unavailable sentinel, not an observed HG limit.
Original separate HG hard guards still apply. All true drained receivers are counted
in source, endpoint1/BC1 and endpoint2/BC2 at every saved state.

Default A compares all 18 real records of the five existing binary exports, including
actual clock, forced final step 320 and signed diagnostics, byte for byte with the
retained M0 A control. Original headers remain intact. This is not a claim that all
22 raw arrays are bit-identical. B-versus-old-B is a different method comparison,
not a half-step or 5 Pa equivalence gate. Successful implementation/native review
never grants theory, complete consolidation, paper accuracy or physical acceptance.
