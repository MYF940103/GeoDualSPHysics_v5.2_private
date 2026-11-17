# P3 GPU host-only endpoint-defect candidate

Author preparation only: `support/upl_tpi_p3_gpu_r1.h` is a new private candidate.
No prepare, build, program, kernel fixture, solver, reader or plot was executed.
The P2 author and actual `upl_tpi_p2_GPU_r2_source` header were read and found
byte-identical before this author operation. Their files and all results stay unchanged.

The candidate retains alpha=.5, beta=0, the same event/1000 fixed step
1.0000228881835938e-5 s, and original source-time load/Dirichlet policy.
It performs three complete endpoint force/rate row evaluations at the one committed
end geometry/J, while mechanic predictor/corrector, material update, J corrector,
HG predictor/corrector and final history/global-clock update occur once per step.
It is a private Symplectic neighbour-pressure prediction/three leading-LP defects,
not literal paper LF, a global implicit solve, a second-order proof or physical acceptance.
The scalar finite-h audit does not prove stability of the full SPH operator.
This author does not increase dt or relax any physical/accuracy budget.

## Reuse and host-only API

The original namespace, View/Core/Observation/Error/DeviceState, device functions,
CUDA/cuh implementation and external kernel signatures remain unchanged.
Before `UPL_TPI_GPU_R1_IMPLEMENTATION`, only one new host declaration block exists:
`P3_HOST_API_R1_BEGIN` through `P3_HOST_API_R1_END`, protected by `#ifndef __CUDACC__`.
Removing that block yields exactly the original 3850 prefix bytes. This preserves
historical comments too; the host policy/summary specifies the actual three-round scope.
The host implementation retains the original include filename `upl_tpi_m0_dt_r2.h`;
a later reviewed private preparation must place the new five-phase dt helper there.
It must not silently link this host candidate to the old four-phase dt writer.

New host APIs are `ValidateProvisionalEndpoint(owner, View, drain, loadmode)`,
`NextEndpoint(owner, View, time, step, dt, hg)` and `EndpointPhase()`.
The last returns the actual active endpoint phase 2, 3 or 4. Existing StartEndpoint,
PrepareFinal, WriteFinal, Commit, Saved and FreeOwner signatures remain unchanged.
`NextEndpoint` takes the same time/step/dt/HG arguments as StartEndpoint and captures
one new real core/HG snapshot internally. The outer caller must not double-capture.

Default A short-circuits before reading `UPL_TPI_P3_ROWS_R1` or invoking Init;
it allocates no candidate state and creates no candidate sidecar. Only explicit B
with `UPL_TPI_P3_ROWS_R1=3` and the matching M0 policy can initialize.
C and an incomplete B selection are rejected. P2/staged-load selectors are not used;
the eventual independent runner must record them absent along with all actual selectors.

## Three-round transaction and observations

Round 1 writes the actual float result, applies the original physical BC, then
ValidateProvisionalEndpoint runs the original device pressure/J/P0 check and copies
all 1040 Observation records D2D to provisionalRows[0]. It does not CommitDevice.
NextEndpoint enters round 2 only after that real write/validation/copy.
Round 2 repeats the full force/rate/row evaluation, write and BC; validation copies
its distinct records to provisionalRows[1]. Only then can NextEndpoint enter round 3.
Only round 3 can CommitDevice, rotate history and complete one accepted step.
Every write is once-only and independently counted; a missing, duplicate or out-of-order
write/validation/transition prevents the final commit. No failed stage is retried.

The actual q2 is validated p1; q3 is validated p2. At each real save those exact float
relations and common pn/previous/prediction/half/theta-half/J states are checked.
Both provisional finalP fields retain the old committed value; they are never labelled
p1/p2. The validated BC columns are the device-validated rule (raw or true +0),
not extra native saved states. The final round native pressure is p3.
Saved PorePressRate is round-3's scaled residual evaluated at actual p2; it is neither
dp/dt nor R(p3). Provisional lap/rate are not observed or reconstructed.

Two provisional device buffers and the final live Observation array are distinct.
Initialization copies the actual cold state to both buffers; initial rows carry
has_endpoint_observation=0, without inventing endpoint evaluations.
Only Saved bulk-copies the two provisional buffers and final soil records D2H.
FreeOwner is idempotent/noexcept, frees owned buffers before the original context reset,
and never dereferences the HG object that a derived destructor may already have deleted.
The static State destructor only deletes host streams; it calls no CUDA API.

## Evidence schema and exact counts

New sidecars are `UplTpiP3GpuR1.policy.json`, `.summary.json` and independent
`.round1.csv`, `.round2.csv`, `.round3.csv`, stage `upl_tpi_p3_gpu_r1`.
The exact 32 columns are unchanged from the P2 GPU CSV. Rounds 1/2 have a stale
previous-final flag only on noninitial records; round 3 has the actual final field.
Each file has 1000 records per actual saved state, with the original scalar clock.
The saved counters are cumulative after the unique final commit, not per-round counts.

For N accepted updates: pre/cor/J/history commits=N; endpoint calls/writes=3N;
provisional validations/copies/next transitions=2N; initial provisional copies=2;
core checks=21000N; HG history/rate comparisons=6000N. Each endpoint also bit-checks
all 24 HG Stats and 15 RateInfo host fields. Existing HG AddHistory arithmetic,
finite/error checks and the original separate stiffness/spin/cache hard guards remain.
Original physical HG still has 2N force/rate calls and N/N pre/cor updates.
No endpoint advances material, J or HG history; native/source ownership, positive-zero
Dirichlet, ledger, IDs, geometry and signed-clock gates remain required by later review.
