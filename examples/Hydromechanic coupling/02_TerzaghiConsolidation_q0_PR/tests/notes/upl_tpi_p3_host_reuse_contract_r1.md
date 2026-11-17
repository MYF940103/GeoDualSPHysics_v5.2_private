# P3 private CPU/GPU host reuse contract

Status: author contract only, not prepare/build/run/native or physics admission.
P2 remains frozen. P3 is an independent three-defect candidate under the existing
controlled diagnosis; no production/XML option or long run is authorized by this note.
The same 10 us-class step and original budgets apply; the finite-h algebra alone
is not an SPH stability certificate and does not authorize 20 us.

## Complete rows and a single physical update

Let q1 be the existing alpha=.5 history predictor after the real endpoint BC.
For r=1,2,3, one full endpoint evaluation produces the original complete residual
Rgamma_r and leading-LP diagonal S_r at q_r, with the original current-J geometry,
load/source clock, boundary refresh, all acceleration terms and read-only HG force.
The actual provisional/final value is
`p_r = BC(RN_float(q_r + Rgamma_r/S_r))`, with true drained rows positive zero.
The next round uses actual float p_r, including the real BC, never the unrounded double
and never q1 plus a multiple of the first correction. GPU retains its already-qualified
RN/FTZ float conversion chain and exact device LP/Rgamma arithmetic.
S is a leading LP diagonal, not a complete nonlinear Jacobian or global implicit solve.

q2=p1 and q3=p2 must be real state flow, followed by a new full force/rate evaluation.
All three rounds share one source pn/previous predictor, actual mechanical half state,
Jn/Jhalf/Jfull and theta-half used by the one original J corrector. Endpoint theta3
must not replace theta-half. The mechanics/material/HG/global-clock update is once.
Only the final p3 commit rotates pressure history. PorePressRate remains the scaled
third-row residual at p2, not a new dp/dt or an independently recomputed R(p3).
No negative-pressure clipping, load tuning, changed kernel, dt, geometry or guard is added.

## Host-only splice and force phases

CPU and GPU pressure namespaces/includes retain their old private API names.
New helpers use explicit `UPL_TPI_P3_ROWS_R1=3` only for B; A first short-circuits
without reading the new selector, allocating history or executing an endpoint.
The new five-phase dt writer keeps its old namespace/include filename, but has a new
P3 policy/sidecar. It must record pre/cor/endpoint1/endpoint2/endpoint3 phases
0/1/2/3/4, with phase 4 alone incrementing its completed-update audit counter.
Pressure helper EndpointPhase returns the real active 2/3/4 phase for the outer call.
TimeStep, source time, tD, ramp and scalar `+=dt` clocks are not changed between rounds.
No staged-load-clock intervention is carried into this candidate.

Required glue after the original single mechanical/J/position correction is:
start round 1; full force/rate + necessary dt; prepare/write; original BC;
ValidateProvisionalEndpoint; NextEndpoint; full round 2 force/rate + dt;
prepare/write; original BC; ValidateProvisionalEndpoint; NextEndpoint;
full round 3 force/rate + dt; prepare/write; original BC; final Commit.
NextEndpoint internally takes the new core/HG snapshot. It is not a third mechanical
corrector, J call, HG history update, output save or global clock increment.
The original force scratch cleanup and RunCellDivide/output sequence remain intact.

CPU deep-copies the actual first/second BC records before reusing its row arrays.
GPU D2D-copies independent Observation records after the existing device BC validator;
there is no new CUDA structure, parameter, inline token or kernel implementation.
GPU host declarations are enclosed in one P3_HOST_API_R1_BEGIN/END block under
`#ifndef __CUDACC__`. Removing it restores the exact original 3850-byte prefix.
The private preparation must separately prove original CUDA/cuh bytes and all public
class headers unchanged before adopting any retained device/other host objects.
The expected changed implementation closure is the two pressure host TUs per backend;
actual object/library/runtime bindings and tool exits remain build-review obligations.

## Evidence and limits

For N complete steps require exactly N pre/cor/J/pressure-history commits;
3N endpoint starts and actual writes; 2N provisional BC validations and transitions;
21000N core field checks and 6000N read-only HG history/rate comparisons.
Original physical HG is still 2N force/rate and N/N predictor/corrector, including
its original cache, finite, dt/tau and spin conditions. All actual force phases
receive the necessary timestep checks; an unavailable HG reference remains a sentinel,
not a measured bound. Native signed/initial diagnostics are not masked or rewritten.

Three saved observation sets retain their real clock/IDs/layout. Provisional finalP
stays the old committed value; it is not p1 or p2. GPU validated BC columns are
successful device rule evidence, not an extra native save; CPU can directly capture
the actual BC float. Initial observations are explicitly unobserved endpoints.
J and P0 must persist exactly; the final native pressure is p3. Provisional lap/rate
are outside the current Observation structure and cannot be fabricated.
No summary, normal exit, scalar fixture or successful implementation regression alone
accepts physical accuracy or a full cycle. Existing target/reference and 100 Pa budgets
are unchanged. Default A byte controls concern their actual five exports, not all
22 raw arrays. Different-method comparisons are not half-step/5 Pa equivalence gates.
Every prepare/build/short run/read/review/science action needs its own reviewed root
admission. Failures and partials are retained; no retry, extra reference, half chain,
source restart, other case or long solve follows automatically.
