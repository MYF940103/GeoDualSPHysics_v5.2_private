# P2: two complete endpoint defects using existing kernels ? reuse audit only

2026-11-17. Design/feasibility review only. No source, helper, prepare, build, program,
solver, reader or GPU action is implemented/executed. Base is the original
`outputs/upl_tpi_m0_dt_{CPU,GPU}_r2_source`, **not** the staged-load source. H3 and
half/reflection drafts remain on HOLD and are not imported. Default A/OFF must retain
its exact original path. This is an unadmitted candidate, not a repair/accuracy claim.

## 1. Feasibility conclusion and concrete blockers

The existing GPU spatial kernel can execute two actual endpoint defects without a
new CUDA kernel or changing Observation, DeviceState, View, RowContext or public CTE.
A first-round Observation buffer can be allocated by host-only State and filled by
ordinary D2D memcpy; the same existing endpoint kernel then sees actual p1 on round2.
CPU can copy its first-round vectors. Keeping all CUDA objects byte-for-byte is
therefore feasible in this bounded closure, subject to an exact host-only-source proof.
It is **not** safe to add only another StartEndpoint call:

1. GPU WriteFinal clears descriptor/endpoint but leaves prepared=true; second Prepare
   rejects unless a controlled first-to-second transition clears prepared. CPU
   WriteFinal leaves endpoint=true; current outer code then clears endpoint AND
   temporary. P2 must clear endpoint but retain temporary=true until the second round,
   otherwise CPU Endpoint's pending/temporary guard rejects.
2. First rows.finalP still describes the last committed p_n, not the provisional p1.
   A D2D first-row copy must not relabel that field as the first solution. First raw,
   actual first BC, second actual q and final p2 need an independent two-round schema.
3. Current M0 Record completes a three-phase step after endpoint1; endpoint2 would
   violate expected phase/source-step/completed-count. Four real phases are mandatory.
4. Current Finish requires N endpoint calls/7000N core/2000N HG checks. P2 must expect
   2N/14000N/4000N, not edit old receipts or fabricate old one-round success.
5. CPU Endpoint does not reset seen/rowError (only Begin does); second Row would
   mark a duplicate and seen would become2. Unlike GPU SnapshotKernel, a controlled
   CPU round2 transition must reset per-round seen/rowError after first errors have
   been observed and first records deep-copied. Confirm unexpectedRows==0 before
   any reset; do not erase a failed first round.
6. Every round needs its own Pre/Pos scratch lifetime and full force/rate evaluation.
   Reusing the first R/Ace, retaining live scratch into another Pre allocation, or
   committing/rotating history after round1 changes the intended method.

## 2. Required successful-step transaction

Original predictor, half corrector, material/J/position and HG history updates occur
once exactly as P1. At the resulting full state, scalar TimeStep=t_n/Nstep=n remain
unchanged through both endpoint rounds. Original q(t_n), drainage predicate and
same-stage wall/periodic closure are used in all four forces. No staged-load or
half/endpoint external-clock correction is carried forward from the rejected trial.

For each endpoint round, retain the existing order:
StartEndpoint -> Interaction_Forces(SymCorrector) -> DtVariable(false) -> PrepareFinal
-> PosInteraction_Forces -> WriteFinal -> actual full-geometry pressure BC.
The first round is not a completed time step and produces no native SaveData.

After round1's actual BC, validate provisional p1/J/P0 without history rotation.
GPU can reuse ValidateCommitDevice+Check directly under a new host transaction guard;
this existing kernel records commitDrained and validates exact raw or true +0,
Jfull and core P0. It does not itself rotate history. CPU needs the corresponding
validation-only half of its current Commit loop; it must not call full Commit.
Observe any error before a later MapCheck resets the error packet.

Only after those checks preserve first rows, including first q/S/R/raw/drained and
validated first-BC mask. Keep pn/previous/Jn/Jhalf/Jfull/thetaHalf from this same step.
For GPU, copy the actual row allocation (or its contiguous soil range) to a separately
owned iteration1 buffer using matching layout/extent. No per-ID D2H copy is needed
in the solve loop. A default-stream D2D copy must be ordered before SnapshotKernel
and the second row overwrite; retain actual CUDA API failures, not just an intended
copy count. CPU copies must be deep vector copies, not aliases to reused storage.

Then enter a unique round2 transition: pending stays true; original source step/time,
pre/cor/J counts and history remain unchanged; prepared resets false; endpoint is
false; CPU temporary stays true. Reject duplicate round2/third-round transitions.
Run the original second StartEndpoint on the actual BC-adjusted p1. GPU snapshots p1,
resets seen through the existing kernel (CPU needs the explicit host reset above), and publishes the same DeviceState with the
same native-ID pointer. The second complete force/rate computes R_gamma(p1) and S2;
Prepare/Write obtains p2=p1+R_gamma(p1)/S2 with original RN/FTZ behavior. This is not
p_old+2*R_old/S_old, a rescaled coefficient, or an implicit/converged solution.

Apply actual final BC; validate all final pressure/J/P0 as originally; Commit once.
Only Commit rotates previous=pn, sets finalP=p2 and advances the pressure helper's
lastEnd/commits once. Only the original outer loop advances scalar TimeStep by dt.
A failure after first p1 write may leave an unsaved provisional field in memory;
no rollback, exact restart, saved failure time or automatic retry is promised.

## 3. Scratch, pointers and hidden state touched by each force

Actual GPU references below are from the original M0-r2 flat source:

| Source / state | Effect and required handling |
|---|---|
| JSphGpu.cpp1411-1466 PreInteraction | Reserves fresh Arg/Ace/ViscDt/Rsigma/derivative/raw-load scratch; zeros those arrays, PoroTheta and relevant force accumulators; recomputes VelMax. A new force does not accumulate the previous force. |
| JSphGpu.cpp1473-1485 PosInteraction | Frees/nulls the force scratch. Pair it once per round, even if the pool later returns identical addresses. Never carry an Ace/Rsigma pointer beyond it. |
| Single699-715 | Repeats source-time CTE q, derivative-wall velocity, FS tracking, periodic C extension and real pressure BC before interaction. These are necessary to read p1 and its hydraulic ghosts consistently. |
| JSphGpu.cpp1701-1722 dynamic wall | Refreshes fixed wall samples/C/acceleration from the same stage. These auxiliary/fixed states may be overwritten; they are not a second native soil material/J integration. |
| Single747-766 | Rebuilds force, damping, normalized load, readonly HG addition and full dynamic pore rate; R2 includes new pressure-to-acceleration feedback. All load/damping/HG contributions start from a freshly zeroed Ace. |
| JSphGpu.cpp1866-1895 | PorePressRate is overwritten by round2's full endpoint scaled residual; its shared invalid flag is checked. Constant k keeps optional conductivity-speed path off. |
| DtVariable | AceMax may change with p1, so second force bound must really be recomputed. Wave/viscous results must not be reused merely because native velocity/J stayed fixed. |

PorePressg, PorePressRateg, PoroJg/PoroThetag, main IDs/codes and native state arrays
are persistent; the endpoint View contains those pointers, not the freed Ace/Rsigma
scratch. No extra RunCellDivide is required between the two rounds on unchanged full
geometry. Nevertheless each StartEndpoint/Commit keeps the original owner mapping
and all original row/core checks. Never infer stable slots from unchanged counts.
The actual second View must be reformed from current members, not a stale copied
scratch address. Repeated wall/FS/periodic work must refresh from p1; skipping it can
leave old pressure ghosts even when native p1 is correct.

InterStep, CTE, max reductions, PoroTheta/rate/FS/CorrMat/derivative buffers, timers and
force telemetry are overwritten or accumulated by the additional evaluation. These
are real hidden side effects. Only the permitted force/rate/auxiliary states may
change; original native soil x/v/rho/sigma/kappa/P0/J and committed HG history/rate
must pass the same readonly endpoint checks in **both** rounds. Frozen case qualifiers
exclude moving bodies/DEM/shifting/filters/variable-k etc.; this is not a proof for
arbitrary stateful external-input providers or general boundary cases.

## 4. HG and four-phase signed bounds

Both endpoint forces must use AddReadonlyHG on the already committed full HG history,
with the actual full-J inertia and original add/float-store order. Neither endpoint
calls original PredictorForce/CorrectorForce/EvaluateRate/UpdateHistory. Existing
Stats24/RateInfo15 and history/rate D2D snapshots are captured/checked independently
for each round. First and second readonly force may differ through pore force, but
neither may advance HG memory, sigma, material history or J.

For N successful steps, expected actual totals become:

- total full force evaluations4N: original predictor/corrector N each, endpoint1 N,
  endpoint2 N; endpointCalls=2N and two readonly HG additions per step;
- preCalls=corCalls=jCalls=pressureCommits=N; core checks14000N and HG snapshot checks4000N;
- original physical HG forcecalls2N, predictorupdates/correctorupdates N each,
  ratecalls2N, original cache/tau/spin/work/elastic checks retained.

A new private M0 writer must expose four phases, and only phase3 ends its audit step.
Old final?1:endpoint?2:0 cannot distinguish the rounds and is not reused as if it can.
Keep original force/wave/hydro method bounds and actual FixedDt::GetDt calls for all
four forces. Signed native interval remains max(dt-bound) over all real calls, with
original caching semantics and initial sentinel untouched, not abs/error clipping.
Calling a second real endpoint adds cost but is not an extra physical solid/damping
impulse: no state update is performed in either endpoint pass.

## 5. First/second output schema and native semantics

The new primary policy/CSV must identify P2 with two defect rounds at fixed full
geometry and old source clock. It must not advertise a one-round P1 record or H3
reflection. Keep true same dt/scalar plan and native22 types. Native PorePressRate
is round2's legacy Kw/n-scaled endpoint residual evaluated at actual q2=p1 before
p2 write, not actual dp/dt and not R_gamma(p2). Final LoadAce/FS/CorrMat/PosDiv/theta
also come from the actual last evaluation as before.

Save first and second Observation records separately with original headers/counts.
First raw is p1 before its actual BC; provisional validation proves actual p1 equals
raw or true +0. Its rows.finalP remains the previous accepted final and must be tagged
stale-for-this-round. The second actual q is independently captured by the real
second force; compare it with that validated p1 rule, not a guessed zero/nonzero
mask. Preserve first and second drained/commit masks and all native IDs. First R/S
must survive the second overwrite; new output can copy both buffers in bulk only at
native saves. Do not regenerate/fake an iteration1 finalP field or an unsaved native
state. CPU needs the same distinctions in its first-vector snapshot.

No existing one-round reviewer may silently certify this schema. Original reader's
22-array/IDs/ledger/clock/geometry/drain gates can be retained, but new independent
history/two-round/counter/four-phase signed review is required. Both first and second
checks must pass; second success cannot override a failed first round.

## 6. CUDA-object reuse and admission boundary

No mathematical change requires a new device kernel: existing Map/Snapshot/Prepare/
Write/Validate/Commit kernels operate on the unchanged structs/pointers. Extra buffers
and per-round metadata belong to host-only State. Put any new wrapper declarations
in a separate host-only header; do not alter device-visible types/signatures/tokens.
GPU helper implementation-section changes do not enter the NVCC compilation path,
but the builder must prove that separation, not blindly ignore a changed header.
CPU and GPU each need at most their two affected host TUs rebuilt with their original
flags/link order; all existing CUDA object bytes can be retained under that proof.
No such build is admitted or performed here.

Default A/OFF allocates no iteration buffer and runs no extra force/policy/CSV path;
new feature guards must short-circuit on original A. A genuine default-A unchanged
native regression is still required. Root would first review source transformations,
CPU fixtures/Debug, GPU memory/ownership checks and the new schema before any bounded
physical job. Small-matrix m-to-m-squared reasoning can motivate two defects but does
not establish SPH stability, improved settlement, overall second order or a suitable
long-run timestep. Original accuracy/safety budgets remain unchanged; no solver,
half/reference/full chain or formal merge follows from this note.
