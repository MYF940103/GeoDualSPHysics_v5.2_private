# CPU P2 helper author: two endpoint defects, one commit

2026-11-17. Only two new author files are this note and
`support/upl_tpi_p2_cpu_r1.h`. The header is a complete clone of the actual frozen
`outputs/upl_tpi_m0_dt_CPU_r2_source/upl_tpi_cpu_r1.h` with narrow host implementation
changes. Namespace remains `upl_tpi_cpu_r1`; original core types/APIs remain, with
additional private round metadata. No CPU View or public class ABI is introduced.
No original file/source tree is changed, no prepare/build/program/solver/reader is
executed, and no numerical or physical acceptance is claimed by this author.

## 1. Scope and selector

P2 retains the original old-source-clock M0-r2/P1 force, pressure and mechanical
paths. Predictor/corrector material/J/HG updates occur once; two actual endpoint
force/residual evaluations follow at unchanged global t_n/Nstep. No staged-load
clock, H3 reflection, half-pressure feedback, new kernel or scalar rescaling is used.
The candidate is only B, alpha=.5, beta0 and original fixed10us/M0 policy scope.

Enabled first checks original A and returns false before parsing any P2 selector.
For a non-A pressure request it requires B and exact private
`UPL_TPI_P2_ROWS_R1=2`; missing/other values reject instead of silently falling back
to a one-round candidate. Original pressure ENV stays `UPL_TPI_CPU_R1=B`; M0 policy
ENV remains `UPL_TPI_M0_DT_R1=EQ40_RH1`. No public XML parameter is added.
A/OFF creates no P2 rows, extra force, history, policy or sidecar path. Its unchanged
native behavior remains a future independent regression requirement.

The separate dt author supplies `upl_tpi_p2_dt_r1.h` under the old
`upl_tpi_m0_dt_r2` namespace. This CPU author neither imports nor edits that file.
Root will overlay the two helper contents onto their original private source names
in a new full267-file CPU tree and patch the two host TUs; this note does not do so.

## 2. Kept code and new state

Author static text comparison confirmed these original blocks are unchanged:
Predict/SolveBeta0 and their finite/overflow guards; IsSoil/Map with native/periodic
role checks; Row/PrepareFinal including seven core-group bit checks; original
HgStats/RateInfo/CaptureHG/CheckHG/AddReadonlyHG arithmetic. No compiler execution
or source-kernel proof is implied by those text comparisons.

New private state tracks endpointRound, firstValidated/secondStarting/roundWritten,
first validation/second start/write counters and a vector of FirstEndpointRecord.
The vector is allocated once with the original native-ID extent; every first record
is copied deeply only after every first BC/J/P0 and readonly check succeeds.
Its priorFinalP records the actual **old committed** field, never relabelled p1.
Its actualBC is read directly from the current CPU p array after validation.
The original pn/previous/half/J vectors and history rotation remain single-step data.

## 3. Exact new APIs for later root-owned Single integration

All APIs are in `upl_tpi_cpu_r1`; use actual CPU arrays, not GPU View:

```cpp
template<class Drained>
void ValidateFirstEndpoint(const void* owner, unsigned np,
  const unsigned* id, const typecode* code,
  const float* p, const float* p0, const double* j, Drained drained);

unsigned EndpointPhase(); // active endpointRound1 ->2, endpointRound2 ->3

template<class HG>
void SecondEndpoint(const void* owner, unsigned np,
  const unsigned* id, const typecode* code,
  const tdouble3* pos, const tfloat4* velrhop,
  const tsymatrix3d* sigma, const float* kappa,
  const float* p0, const float* q, const double* j,
  double time, unsigned long long step, double dt, const HG* hg);
```

ValidateFirstEndpoint expects the first original WriteFinal and actual pressure BC
already completed. It validates every soil value as exact first raw or true +0,
Jfull and initial P0; first core/HG checks must also have completed. Only then does
it deep-copy records, mark firstValidated, clear endpoint, and keep temporary and
prepared true. It does not change pn/previous/finalP, commits, source time or J.
A caller may use a real source-clock predicate such as:
`drain && IsHydroMechDrainedParticle(p,Posc,Codec,FSTypec)`.
No depth-only, ID-only or vacuous mask is substituted.

SecondEndpoint checks that provisional p1/J/P0 still match that validated snapshot.
It rejects missing/duplicated first validation or second entry. Only after those
checks does it clear per-round seen/rowError/drained/commitDrained, set prepared=false,
and enter the original Endpoint with a private secondStarting guard. CPU Endpoint
itself increments the round and records the second actual pressure q. It is still
the original core snapshot operation, not a second material/J update.
**SecondEndpoint internally calls CaptureHG(hg).** Do not add another required outer
CaptureHG for round2. The original first Endpoint still needs its old outer CaptureHG.

unexpectedRows must already be0 before any second-round clearing; first errors are
not reset away. In particular, direct repetition of old Endpoint would leave seen=1
and falsely reuse a prepared row; the new transition explicitly prevents that path.
On any error keep the actual first failure/partials and do not retry the transition.

## 4. Required later glue order, not executable work in this note

Retain original first `Endpoint(...); CaptureHG(HourglassCpu);` and its full force,
DtVariable, CheckHG, PrepareFinal, PosInteraction_Forces and WriteFinal. After the
first WriteFinal, apply original full-geometry pressure BC, then call
ValidateFirstEndpoint with the actual mask. Do **not** execute the old combined
`state.endpoint=false; state.temporary=false;` line at this point; temporary is needed
by the original Endpoint guard. The validation method clears only endpoint.

Then call SecondEndpoint with the actual full state/HG. Run a new complete endpoint
Interaction_Forces+DtVariable, CheckHG, PrepareFinal, PosInteraction_Forces and
WriteFinal. Every force gets its own scratch allocation/reset/free pair. Recompute
R_gamma(p1) including acceleration feedback; do not reuse R1 or add it twice.
Now perform the original endpoint=false/temporary=false line, original pressure BC,
actual final SetCommitDrained loop and original Commit entry exactly once.
Only the existing outer loop advances scalar TimeStep by dt.

The backend DtVariable endpoint branch must obtain pressure helper EndpointPhase()
and pass2/3 to the new four-phase writer. Do not call the old three-phase writer or
increment Nstep between rounds. Original signed dterror still includes all four real
force-bound evaluations and initial diagnostics; no guard is relaxed.

WriteFinal now rejects skipped/duplicated writes and counts actual successful writes.
Final Commit requires round2 written, first validation and second start once, all
expected core/HG checks, exact p2/final BC/J/P0, then rotates original previous=pn once.
Failures after p1 write can leave an unsaved provisional field; this is not a whole
solid rollback or a safe PART-restart mechanism. No saved failure time is invented.

## 5. New independent pressure output

Files are `UplTpiP2CpuR1.csv`, `.policy.json`, `.summary.json` under the new output.
The primary stage is `upl_tpi_p2_cpu_r1`. The CSV has32columns; first initial save
emits one cold round0 record/soil ID (no endpoint observation). Every later actual
save emits round1 then round2 per soil ID, preserving true IDs and scalar clocks.
For F native frames the expected row count is soilCount*(1+2*(F-1)).

Each row has pn/previous prediction, original mechanical half pressure, actual endpoint
q, full S/R, raw candidate, actual BC value, explicitly stale prior committed finalP,
original half/full J and divergence, real source/row/commit masks, and cumulative
counters at the native save. Counter fields are **save-time totals**, not the earlier
moment the round1 record was captured. Round1 actualBC is a direct saved CPU float;
round2 actualBC is the genuinely committed final p2. Saved also checks the second
actual q bits against the validated first p1, with no interpolation or tolerance.
The prior_finalP stale column is old for both round captures; it is never p1/p2.

Native PorePressRate remains the last, second full endpoint's legacy Kw/n-scaled
residual evaluated at p1 before final p2 write, not dp/dt or residual(p2). No H3
half-state rate semantics are imported. The old one-round CSV/reviewer is not reused
as proof of two defects. Original native22/clock/IDs/ledger/FS/drain/HG gates remain;
an independent new dual-round/four-phase review is required later.

For N completed steps the helper enforces pre/cor/J/Commit=N, endpoint calls/writes=2N,
first validations=second starts=N, core checks=14*soilCount*N and HG snapshot checks=
4*soilCount*N. Existing physical HG force/history/rate counts stay original2N/N/N/2N;
only two readonly endpoint additions occur. Both rounds separately retain actual
Stats24/RateInfo15 and HG-history/rate bit checks and original add arithmetic.
Policy/summary explicitly deny physical acceptance, full restart and scalar-fixture
proof of the actual spatial kernel. Both also declare paper_literal_LF=false,
second_order_claimed=false and true_implicit_solution=false; summary retains
theta_endpoint_is_not_J_integration_theta=true. These are metadata limits only;
the32-column pressure CSV and numerical/transaction code are unchanged.
No new source/job is automatically prepared.
