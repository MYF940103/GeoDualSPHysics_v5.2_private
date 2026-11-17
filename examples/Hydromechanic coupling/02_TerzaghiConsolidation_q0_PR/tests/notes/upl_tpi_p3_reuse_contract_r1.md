# P3 CPU reuse contract r1

Private author contract only; no implementation is wired into a source tree and no prepare/build/help/solver/native is executed. This contract concerns only `upl_tpi_p3_cpu_r1.h` and `upl_tpi_p3_dt_r1.h` plus the future minimum CPU glue. The independently owned GPU helper/contract is a separate author asset. Frozen P2, public source, accepted case files and paused C08 remain unchanged.

## Read source and unchanged hooks

Read final P2 CPU/dt headers completely and confirmed their actual `outputs/upl_tpi_p2_CPU_r1_source` copies identical. The relevant real source anchors are:

- JSphCpu.cpp4567-4574: original Begin/half actual-BC capture, once.
- JSphCpu.cpp4598-4604 and4950: original Corr/Guess and sole full-J capture, once.
- JSphCpu.cpp4411-4499: original actual row/R/S capture from full pressure kernel; no operator edit.
- JSphCpu.cpp4997-5042: original current-J skeleton-wave/hydro necessary-bound arithmetic and rejection; Record already asks pressure-helper EndpointPhase.
- JSphCpuSingle.cpp811-812: exact readonly endpoint HG add; preserve this branch and all original mechanical HG phases.
- JSphCpuSingle.cpp1345-1371: original bounded qualification/init; replace only private diagnostic label, not material/geometry/clock/space policy.
- JSphCpuSingle.cpp1403-1433: P2 outer pressure loop, scratch/BC/commit/error handling; local P3 glue must be limited here.
- JSphCpuSingle.cpp1434 onward,1461-1462,1583-1584: original one scalar time advance, helper completion and actual saved-field hooks; retain positions.

The destination include filenames and namespaces remain old names. This allows new host objects to use a new isolated copy without class/vtable or CUDA ABI changes. It does not authorize reusing a CPU object compiled against an older private State. Any later builder must compile both consuming host CPPs together and explicitly bind the private source closure.

## Minimum future glue, not yet applied

The intended single local change is round<2 to round<3, with `NextEndpoint(...)` on rounds1/2 and `ValidateProvisionalEndpoint(...)` after rounds0/1 real BC. Round index is zero-based in the host loop; pressure evidence rounds are1/2/3.

1. Original ComputeStep/RunCellDivide has already committed the solid endpoint/J/material once.
2. Call first Endpoint and CaptureHG once. Keep all load/force source evaluations at original TimeStep.
3. For each round: actual Interaction_Forces, DtVariable(false), CheckHG, PrepareFinal, PosInteraction_Forces, WriteFinal.
4. For first two rounds keep endpoint/temporary true through ApplyPorePressureBoundaries; call ValidateProvisionalEndpoint. It validates/deep-copies actual p1/p2 before clearing endpoint. NextEndpoint then validates p/J/P0, resets only already-observed row scratch and captures next core/HG internally once.
5. Only before the third final BC clear endpoint and temporary; apply real BC, set original per-ID drained mask and Commit once.
6. Preserve the existing catch: clear endpoint/temporary and release a genuinely allocated force scratch once; rethrow the first error, never retry or rotate history.
7. Leave global TimeStep+=stepdt, Nstep, SaveData/clock/cadence and final Finish in their original outer positions.

The helper's PrepareFinal/WriteFinal names are retained for source reuse but mean this round's provisional candidate, not a pressure-history commit. Commit only accepts the third written/BC-validated round after two successful seals/transitions. Native R3/PorePressRate remains at actual p2, not at newly written p3.

## Observable evidence and guard contract

For each completed N: five actual force/necessary-bound evaluations; one Begin/Corr/J/material/solid/global-time/history update; three endpoint calls/writes; two validated/deep-copied provisional records; two transitions;21kN core and6kN readonly HG checks for1000soil. The original physical HG two-force/two-rate/cache/dt/spin lifecycle must remain unchanged. Both provisional old-final fields stay stale prior-step values; p1/p2 are proved by actual BC captures, and subsequent q must exactly match them.

Pressure evidence uses a new32-column three-round schema, and timestep evidence a new23-column five-phase schema. Existing one-/two-round sidecar reviewers cannot certify this by relabeling. All22 typed native arrays,1040 native IDs, actual clocks/Step/dt/signed intervals, P0/J/n/rho/k ledger, active drainage and original source-clock event1000preopen/1001postopen remain mandatory. A remains default with no P3 allocations/sidecars or extra forces, but actual unchanged-A native regression is still needed.

No pressure relaxation, residual blending, fitted coefficient/time, spatial change, staged load, half reflection, extra half/reference chain or full solve is part of this candidate. P3's finite-h algebra review can reject a candidate but cannot prove SPH stability or physical accuracy. Same10us and the original pressure/top/bottom/all100Pa budgets are retained; no20us escalation is admitted.
