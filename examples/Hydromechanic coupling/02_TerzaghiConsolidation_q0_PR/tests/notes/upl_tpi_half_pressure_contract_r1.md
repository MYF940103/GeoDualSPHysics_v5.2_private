# H3 half-pressure contract: design only, not an admitted implementation

2026-11-17. This is a new review draft. No source patch, prepare, build, program,
reader, physical solve or automatic follow-up is authorized by this note.
The existing P1/M0-r2 source, failed physical budgets, native receipts and retained
results remain unchanged. H3 is a new private numerical candidate, not literal
paper LF, a proven repair, a converged implicit solve or overall second order.

## 1. Frozen scope and reference anchors

Use the actual flat private sources in
`outputs/upl_tpi_m0_dt_CPU_r2_source` and `outputs/upl_tpi_m0_dt_GPU_r2_source`.
These paths are references, not new writable targets. Retain M0 beta0, alpha=.5,
constant k, original real Kw, fixed dt=tD/1000=10.00022888183594us,
tD=ramp=.0100002288818359375s, original geometry/material, FreeSlip/SPR1/grad1,
AV.1, soil damping.04, HGxi.1, kernel, eta and load normalization. No AS, filter,
shifting, beta, parameter tuning, extra half/reference or full-run chain is added.
A/default-OFF must remain on its original code path without H3 allocation,
sidecars, repeated forces, changed BC calls or timing. No public XML is proposed.

| Existing source anchor | Current meaning / future private hook location |
|---|---|
| CPU `JSphCpuSingle.cpp:966-994` | Original predictor/corrector; insert half source pass between cell division and unique mechanical corrector force. |
| CPU `JSphCpu.cpp:4564-4606,4950` | Pressure half/guess hooks and unique full-J capture; replace semantics in a new private helper only. |
| CPU `JSphCpuSingle.cpp:811-821,1403-1429` | HG/rate order and old post-mechanics endpoint; remove only the H3 extra endpoint branch. |
| GPU `JSphGpuSingle.cpp:885-914,1209-1223` | Same three-force reorder; global scalar clock advances only after pressure commit. |
| GPU `JSphGpu.cpp:1559-1565,1595-1618` | Begin/half/J/full-guess hooks; H3 must not write the old endpoint guess after full mechanics. |
| GPU `JSphGpuSingle.cpp:708-766` | BC/load/force/readonly-HG/rate order within a force call. |
| GPU `JSphGpu_ker.cu:1575-1656` | Original complete pressure row, leading S, real-Kw rate; retain one spatial body. |
| GPU `JSphHourglassGpu.cpp:154-174` | Original HG phase transitions; only one CorrectorForce is legal. |
| CPU `JSphHourglassCpu.cpp:224-255` | Exact history addition and half-history integration arithmetic. |
| CPU `JSphCpu.cpp:4996-5064`; GPU `JSphGpu.cpp:1931-2006` | Necessary timestep bounds and fixed-dt rejection. |
| `upl_tpi_m0_dt_r2.h:62-96` | Current pre/cor/endpoint writer is incompatible with H3 labels/order; do not relabel old records. |

The approved algebra source is separately reviewed
`support/upl_tpi_paper_time_layers_r1.py` and its note. Its tiny-h Fourier examples
are not measured SPH eigenvalues or an admission for this 10us candidate.

## 2. Selected clock contract and the optional load-time alternative

For an initial H3-Z0 implementation, **retain the old force source clock**.
All three force calls evaluate the original external ramp at scalar `TimeStep=t_n`.
Half geometry is not a declaration of half-time external loading. This choice
isolates pressure-to-force feedback; forced/ramp behavior remains generally first
order even if the homogeneous autonomous leading lag cancels. It may therefore
fail to repair the observed top bias. This draft does not authorize H3-Z0 execution.

Never temporarily write `TimeStep=t_n+h/2` or `Nstep` to obtain another load value.
That would also affect drainage, fixed-grid roundoff handling, saved signed
intervals, fixed-dt state, history guards, output scheduling and other source clocks.
Keep all lifecycle/ledger time checks on the true scalar t_n and actual step n.

A later, separately selected H3-Z05 could evaluate only the two half-state load
calls at t_n+h/2, with Force0 at t_n, using the same physical q(t), ramp duration and
resultant. The narrow host-only route appears technically feasible in this bounded
C02 closure: a new private owner/phase context supplies an explicit `load_time`,
passed into a free `EvaluateRamp(load_time,q0,tramp)` function at each existing load
calculation. No public class signature, CTE layout, CUDA signature or global clock
needs to change. Mandatory paired sites are:

- CPU `JSphCpu.cpp:1264-1265` direct top acceleration and `2343-2345` pair/raw-band pressure;
- GPU `JSphGpu.cpp:801-804` CTE raw-band/confinement pressure and `1204-1205` direct acceleration.

Both calculations within each force must use the exact same admitted load_time,
including the normalization target. Pressure source R uses that stage's actual
acceleration and does not introduce another independently timed load. Drainage
continues to use its original source-clock predicate, not load_time. With no H3,
the original ramp expressions must remain untouched. Root must separately review
this host context, validate its canonical owner lifetime/default-A branch and
choose Z05 explicitly; it is not silently part of H3-Z0 or an accepted second-order
boundary closure. Other time-dependent cases remain outside this contract.

## 3. Three forces, one material/J/position commit

Use true ID-owned p_n and p_previous. Preserve the original saved previous endpoint
and record any authorized source Dirichlet projection separately as `pn_used`.
Pressure history rotates only after the whole new step and final BC validate.

1. **F0 old_full**: original BC/load and original PredictorForce at x_n/y_n/J_n/pn_used.
   Evaluate the original necessary bound. Original solid and J predictors run once;
   original HG PredictorUpdate runs once, producing the real half history H_h.
   Store the actual predicted half geometry/material/J/velocity and native ID map.
2. **F1 half_guess_source**: at that half state install
   g_h=float(pn_used+.5*(pn_used-p_previous)), preserving CPU arithmetic / GPU RN+FTZ
   and genuine source/half BC. Run a force/rate pass with readonly H_h addition.
   Capture actual q1 after real BC, full R1_gamma and leading S1 from the original
   row; p_h_double=q1+R1_gamma/S1 and p_h_raw is its actual float conversion.
   Apply the real half-state Dirichlet rule to obtain p_h_actual. This is one defect
   correction, not a solved new-acceleration row or an implicit iteration.
   Check the F1 necessary bound before any full solid update.
3. **F2 half_corrected_feedback**: at the same half geometry/material/J/velocity,
   install p_h_actual, refresh hydraulic ghost/periodic data through the original
   same-stage closure, then compute the real force and rates again. Use the unique
   original HG CorrectorForce here. Check the F2 necessary bound and require that
   actual pressure read by the force equals the declared corrected half field,
   apart from independently recorded genuine Dirichlet projection.
   Original full mechanical/material corrector, J corrector and position update
   run exactly once using F2. Original HG CorrectorUpdate runs exactly once at the
   resulting full state. No old fourth/full endpoint force follows.

F1/F2 may overwrite derivative work buffers, boundary ghosts and accelerations, but
must not change native soil x/v/rho/sigma/kappa/J/P0 or HG histories before the
unique full corrector. Map/sort changes must preserve ID ownership. Capture and
compare these core fields explicitly; do not assert equality of derivative buffers
which are intentionally recomputed. The fixed-point S is still only leading-LP;
full Taylor and acceleration feedback remain in R1.

## 4. HG history and counters

H_h is the actual history **after the original PredictorUpdate and before any
CorrectorUpdate**. GetHistory returns Q/Mref, not a ready-to-add current acceleration.
F1 adds it with the exact existing current-half-J particle-mass factor and original
double-add/float-store order. GPU uses device bulk pointers/D2D snapshots and the
original cuhg AddHistory; no per-ID D2H force reconstruction. CPU uses the frozen
ParticleMass/AddHistory arithmetic, not an algebraically simplified substitute.

F1 must not call original CorrectorForce: GPU lines165-167 advance its phase, so a
second call would be invalid. F1 needs a new readonly-half mode with explicit
history/rate and every Stats/RateInfo field snapshotted before/after. It does not
invoke HG EvaluateRate/UpdateHistory or change cache readiness. F2 uses the sole
original CorrectorForce, followed once by the original endpoint CorrectorUpdate.
The old full-endpoint helper cannot be reused under its old `Jfull captured` guard.

For N successfully completed updates, intended observed counts are:

- main force evaluations 3N: old_full=N, half_guess_source=N, half_corrected_feedback=N;
- pressure correction row captures N per native soil ID; reflected pressure commits N;
- full material/J/position correctors N; original predictor updates N;
- original HG forcecalls 2N, predictorupdates=N, correctorupdates=N, ratecalls=2N;
- new readonly-half HG additions N, independently counted and proved nonmutating;
- HG ratecalculations/cachehits must follow the actual original cache state; the
  former N+1/N-1 pattern is checked only if that reuse is actually retained/proven.

Preserve original tau/spin/work/geometry gates. A diagnostic extra readonly addition
must not be counted as a physical HG history update or hidden from its own counter.
No exact-HG restart, plastic HG or general boundary qualification is implied.

## 5. Reflection, genuine BC and failure transaction

Reflect the **actual float half pressure used in F2**, not an unrounded scratch:
`p1_raw=float_RN(2*double(p_h_actual)-double(pn_used))`, with GPU FTZ exactly as compiled.
Record the double intermediate and actual float result. Then apply the original
full-geometry endpoint BC and validate all native soil values: true final drained
receivers must be positive zero; every other value must equal its own raw reflected
float bitwise. Ordinary negative pressure is not a Dirichlet condition and is not clipped.

At tD, completed1000/part103 remains the saved pre-open state. The next update has
source step1000 and completes1001; it uses the real open source-clock predicate.
There is no half-time retiming of this event. Source, F1, F2 and endpoint masks are
separate per-ID observations using their actual geometry/FS data, never copied from
one another or inferred only from depth/ID. In this fixed profile every saved
post-open true receiver count must remain10. Verify the event/pre-open nonzero
pressure and every post-open positive-zero receiver through the new actual plan.

Important source distinction: the previous pre-open native save can be nonzero,
while the next F0 BC legitimately projects `pn_used` to +0 before force/prediction.
Do not rewrite that old save or P0. Record `previous_saved_final`, `pn_used` and
`source_drained`; only true source Dirichlet may explain their difference. If a
particle first becomes constrained later at half/end geometry, unrestricted
reflection can be negative (for p_h=0 and nonzero pn_used); only its actual endpoint
Dirichlet mask may replace it with +0. A released/non-Dirichlet particle is not zeroed.

Hold pn_used/previous until all S/R/float/core/BC checks succeed, then rotate history
once. On failure no accepted pressure-history rotation or completed-step record is
made. This is not a whole-physics rollback promise: a failure after the full solid
corrector may leave an unsaved in-memory state, which must not be reconstructed as
a saved native state. Preserve the actual exception/partials without retry or overwrite.

## 6. Signed necessary-bound contract

Retain the M0 Eq40/Rh1 bound, actual current-J skeleton wave/AV scale, original
force bound and original true-Kw explicit hydro reference; physical Kw is unchanged.
Each of F0/F1/F2 calls the original rejection path before its associated state advance.
New sidecar phases must be explicitly `old_full,half_guess_source,half_corrected_feedback`;
existing pre/cor/endpoint records and the old native reviewer are not relabelled.

The existing M0 Record requires 0/1/2 and infers phase through `final`/EndpointActive;
it cannot accept H3 unchanged. A new private phase selector/writer must preserve
three real calls in that order while leaving global TimeStep/Nstep untouched.
DtVariable final=false for F0/F1 and final=true only for F2 preserves one final
PartDt/SaveDt accounting action. Include all three returned bounds when choosing
an unlocked next dt; this profile remains locked at the exact admitted 10us value.
No clipped step or increased DtMin is allowed.

Per real nonempty output interval retain
`max_over_all_F0_F1_F2(dt-min(forceCFL,skeletonWaveAVCFL,RhHydro))`.
`JDsFixedDt.cpp:128-139` and `JSph.cpp:2917` remain the actual signed native writer;
new interval reconstruction must match those saved bits and enforce the unchanged
<=1e-14 guard. Preserve the native initial diagnostic and explicit empty sentinels;
do not substitute zero, drop an interval, take abs(error), or call this pressure
constraint convergence. HG reference DBL_MAX remains unavailable, not a measured bound.

## 7. New output semantics and reader qualification

Keep native22 fields, IDs, P0 and ledger unchanged in type. Their last-stage derivative
meaning changes and must be explicitly tagged in a new H3 sidecar/schema. Do not run
an old endpoint-formula checker and call its success H3 certification.

Natural minimal choice: retain the real last F2 output in native PorePressRate,
PoroThetaLastStage and PosDiv. PorePressRate is then the old real-Kw/n-scaled residual
at **half-corrected** geometry/J/velocity/pressure/acceleration, not dp/dt, not an
endpoint residual, and not the F1 residual used to form p_h. R1/S1/q1 and actual p_h
are separate source observations. Restoring F1 rate into native would be an additional
explicit output-schema decision and is not selected here. Never fabricate either rate.

Required new per-ID evidence includes source/half/F2/end clocks and masks, true saved
final and pn_used/previous, q1/S1/R1_gamma, half raw/BC/actual-force float pressure,
F2 actual pressure and residual/rate, theta used by the single J corrector,
Jn/Jhalf/Jfull, raw reflection/final pressure, and transaction/force/HG counters.
The true full R scalar ingredients and actual stored legacy rate should be retained
for rate replay: use the original `Kw/n*(-theta+k/gamma*lap)` arithmetic, not an
algebraically regrouped R_gamma/gamma to claim bit equality. GPU FMA/RN/FTZ scope
remains the compiled original scope; no new ULP/absolute allowance is implied.

Native PoroTheta/PosDiv at the final save describe F2 half-state rates although
positions/J/sigma/v are full-step fields; this is declared staggered diagnostic
storage, not a new full-state force evaluation. New J replay uses actual F2 theta
and Jhalf with original scalar/CUDA arithmetic. Saved pressure is the reflected
full-time pressure after real endpoint BC. No residual R_gamma(p_saved) was evaluated.
An optional future endpoint residual observation would be a fourth force state,
requiring its own admission and counters, not hidden in this three-force algorithm.

## 8. Implementation/review boundary

A future author patch would need new private CPU/GPU pressure helpers and narrowly
updated private three-force hooks, a new phase-aware M0 interval schema and H3-specific
reader/reviewer. Existing public headers/spatial kernels/ABIs should remain unchanged
where possible; capture-only row metadata may require an explicitly isolated device
rebuild. Default-A exactness, actual CPU fixtures and GPU Debug/memcheck must precede
any bounded physical admission. Those actions are not initiated by this note.

GPU-only physical implementation would leave this new time-layer transaction without
the project's CPU-first debug path. Prefer a matching minimal CPU helper and the same
private three-force schedule in the two existing CPU TUs, not a second independent
algorithm. A future small CPU component should exercise the actual H3 helper's ID
reorder/periodic roles, corrected-half float reflection, newly drained source versus
half/endpoint masks, positive/negative zero, overflow/invalid S or R, no-commit failure,
commit-once history and old/half-guess/half-corrected signed-interval phases. It should
also check readonly-half HG arithmetic and unchanged histories/Stats/RateInfo. Pure
fixtures do not replace a genuine bounded CPU Debug stage through the original force,
material and J paths. The already used 200-update/approximately2ms 10us CPU profile is
a possible small starting shape, only after separate root admission; no new run is
selected here. GPU Debug/memcheck then checks actual device ownership, reflection and
memory behavior. Neither component nor short smoke certifies physical repair.

Root must first select Z0 versus a separately reviewed Z05 load clock, approve the
new half HG/BC/rate/clock schema and pressure-history stability evidence, then decide
whether the old B2s/new10us evidence warrants one private candidate. No automatic
20us, full2Tv, extra reference/half, C08, other-psi or solver follows. Original top
noninferiority, pressure, bottom, stress, ledger, signed and geometry budgets stand.
