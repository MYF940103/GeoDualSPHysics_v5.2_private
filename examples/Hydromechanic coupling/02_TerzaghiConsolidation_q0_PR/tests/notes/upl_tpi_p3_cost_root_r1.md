# P3 cost probe: root result and next scope

2026-11-17. The single2000-step/210-save performance probe used the unchanged passed P3 program. Its independent Nsight Popen/tool Win32 and solver Win32 exits are all0. Solver loop52.946587s; whole profiler call382.5107098s includes report generation/export/statistics. No process was stopped, replayed, retried or rearmed.

The original probe run remains failed: its reused postcheck expected one fixture stdout marker, while Nsight's captured target stdout/stderr streams are both empty. We did not insert a marker or change that old run. A separate offline review verified real targetPID31932, encoded process identity, nonempty CUDA events, one SourceRoleFixtureKernelR2 launch and the compiled-source checked16 rejection chain with successful actual program exit. The original console observation remains unavailable. The new check validates only performance evidence, never native/physical accuracy.

The protobuf UTF8 diagnostic is preserved. Read-only SQLite analysis retains invalid bytes losslessly; the observed invalid metadata is localized time-zone text. The only nonzero raw API return is cuCtxSynchronize709, after a successful cudaDeviceReset. The used local CUDA11.7 header defines709 as destroyed/uninitialized current context. This sequence is consistent with a teardown context query; no caller stack was captured, so no exact caller is asserted. It is not evidence requiring a new numerical patch.

| Actual scope | Calls/instances | Sum of recorded duration(s) |
|---|---:|---:|
| Host cudaMemcpy API |456300|33.779186856|
| Host cudaLaunchKernel API |723944|5.072882843|
| All device kernels |723944|22.484548197|
| Dynamic hydraulic wall kernels |50422|5.854777377|
| Fluid-force kernels |10000|5.563717770|
| Complete dynamic pore-rate kernels |10000|5.152101941|
| Free-surface computation kernels |20211|2.941137417|

API waiting can include preceding GPU work: these sums overlap and must not be added or interpreted as disjoint application-wall fractions. For example4B D2H has152638 associated API calls/16.462279194s, but device-copy duration.129235183s. This indicates many small synchronization points, not proof of slow pure transfer bandwidth. The short startup saves16.6 times more densely per step than the2s run, so its total runtime is not a long-run cost estimate.

Source attribution explains all8B copies:70632 private GetError calls,10000 M0 skeleton-wave results,16004 cell-domain limits and4001 CellSize values. Only part is private observation. The24B copies are exactly10000 physical top-band reductions, one for each of five force calls per update. They return zmax, target force and raw band force and are used by actual load normalization/sign checks. Their existing physics cannot simply be removed. Of4B copies142635 have identified physical/domain/maxima/periodic/J callers;10003 remain unattributed rather than being assigned by guess.

Within three pressure endpoints there is no new divide, geometry/J/material/HG-history advance. Exact full-generation reuse of geometry, FS/C/fit geometry or top-band totals is a future candidate; pressure ghosts, acceleration ghosts, complete LP/gp/Da/Neumann residual and AceMax remain fresh. No speedup is proven and no necessary safety gate is waived.

The qualified2s P3 result remains accepted within its original window budgets. To avoid indefinite optimization before late-cycle evidence, the next preparation is a minimal exact full2Tv host-scope and honest native-profile extension. It changes time-domain admission only; current physical equations/CUDA/pressure iteration remain the existing ones. There is still no full solver launch or production-source release in this result. The full readiness plan is7288262updates/1653frames/end72.88428815806371s, with1262 genuinely shared early clock records; actual later byte equality remains to be measured.
