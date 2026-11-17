# P2 GPU static work and diagnostic-cost audit

2026-11-17. Read-only source audit, followed only by creation of this new note.
No profiler, build, program, solver, native reader, analysis main, hash scan or
active-process operation was run. Existing frozen sources/results are unchanged.
Counts below are source-level successful-path calls and requested logical bytes,
not measured time, physical memory traffic, PCIe throughput or a speedup estimate.

## Actual source inspected

`logs/upl_tpi_p2_GPU_r2.prepare.json` is passed and identifies
`outputs/upl_tpi_p2_GPU_r2_source`. References below are relative to that frozen
source: `upl_tpi_gpu_r1.h` (284 lines), `upl_tpi_gpu_r1.cuh`,
`JSphGpuSingle.cpp`, `JSphGpu.cpp`, `JSphHourglassGpu_ker.h/.cu` and `TypesDef.h`.
This is the actual P2 source, not a mutable author helper or staged-load candidate.

The static sizes used here follow these structures and the existing Windows x64 /
CUDA layout: `Error` 8 bytes; `Observation` 104 bytes (six floats, eight doubles,
three unsigneds and trailing alignment); `cuhg::StReduce` 184 bytes (19 doubles,
three unsigneds, alignment, two doubles); `double2` 16 bytes. These are the sizes
of the explicit `sizeof` copy requests, not a newly executed ABI probe.

## Numerical work retained by the method

`JSphGpuSingle.cpp1204,1212–1224` retains one mechanical `ComputeStep`, then two
real full-state endpoint passes. Each endpoint repeats the original force/rate,
stage wall/FS/pressure-ghost/load work, current necessary-step reductions,
`PrepareFinal`, scratch release, float pressure write and actual BC. The four
actual force calls are pre, half corrector, endpoint1 and endpoint2. Pressure
history, J, material state, position and HG history still commit once per update.

Endpoint2 must recompute the complete R_gamma using the actual BC-adjusted p1.
Removing that force, reusing R1/S1, or replacing it by a doubled correction changes
P2. The two endpoint HG additions also change actual acceleration used by R_gamma;
their `KerAddHistory` operation and its original add/store order cannot be dropped
as if they were logging. The original force/AV/wave/hydro/HG safety limits remain
necessary. Reducing diagnosis cannot establish that a larger timestep is stable.

## Per-update private-helper calls, excluding native saves

The table counts only this private TPI/HG-adapter path. It excludes the numerous
original kernels/copies/reductions within the four full force evaluations, normal
mechanical HG updates, cell division, gauges, native SaveData and ordinary console
output; it is not a complete GPU workload count.

| Source-level work | Calls per update | Requested logical bytes |
|---|---:|---:|
| `Check` / `GetError` D2H, `.h148–150`, `.cuh42` | 26 | 26 x 8 = 208 |
| Endpoint readonly-HG reduction result D2H, `.h215–218` | 2 | 2 x 184 = 368 |
| Endpoint HG-history/rate snapshot D2D, `.h205–206` | 4 | 4 x 1000 x 16 = 64,000 |
| First-round entire Observation snapshot D2D, `.h237` | 1 | 1040 x 104 = 108,160 |
| `ResetError` H2D, `.cuh41` | 8 | 8 x 8 = 64 |
| Publish/clear RowContext constant descriptor, `.h207,232` | 4 | 4 x sizeof(RowContext); 352 for the present x64 layout |

Thus this path alone has 28 small D2H calls / 576 requested bytes and five direct
D2D calls / 172,160 requested bytes per successful update. The small D2H copies
observe results of preceding default-stream work; their latency/synchronization
opportunities may matter more than their byte count, but no timing was measured.
Do not call each D2D copy a proven CPU synchronization; CUDA stream/API ordering
and actual runtime behavior are distinct from these source-level counts.

The 26 Error reads are reproducible from the helper call graph:
Begin3 + Corr2 + CaptureJ2 + Guess1 + first Start3 + first Prepare1 + first Write1
+ first Validate3 + SecondEndpoint transition1 + second Start3 + second Prepare1
+ second Write1 + final Commit4. Seven `MapCheck` calls each reset the Error,
memset all 1040 slots and launch MapKernel plus CheckMapKernel. Guess resets Error
once more. The two endpoint HG maps each memset 1000 slots and a separate error.
These give 11 explicit map memsets and 37,128 requested memset bytes per update.

The private wrappers launch 34 kernels per update: 14 mapping/owner-check kernels,
14 Begin/Corr/J/Guess/core/Prepare/Write/Validate/Commit kernels, plus six endpoint
HG Map/AddHistory/Reduce kernels. This excludes CaptureRow, which runs inside the
real pressure-rate kernel, and all other original force kernels. Of these private
kernels, several combine numerical work and checks and are not removable wholesale.

There is no per-update CUDA allocation in this helper. Start/Prepare construct
eight host `std::vector<double>` results per update (24-field Stats and 15-field
RateInfo at both capture and comparison, for each endpoint), totaling 1248 bytes
of explicit double payload. These are host HG telemetry copies, not D2H transfers.
The actual allocator cost has not been measured.

## Saved-state-only output

`.h256–268` adds, per actual save including the initial state:

- three further 8-byte Error D2H reads, one MapCheck and one CollectKernel;
- two full Observation D2H copies: 1000 x 104 plus 1040 x 104 = 212,160 bytes;
- two host vectors holding those records; first/second coherence comparisons;
- 2000 CSV rows, 32 numeric fields per row, precision17, and two stream flushes.

The dt audit separately emits one 21-column row and flush per save; its four-phase
min/max/counter accumulation is host arithmetic per update, without per-update
CSV formatting. Policy JSON is initialization-only and summary JSON is Finish-only.

For the admitted 199996-update / 1263-save plan, the above formulas imply 5,599,888
small per-update D2H calls and 34,431,311,360 requested per-update D2D bytes.
Saved Observation transfers request another 267,958,080 bytes, and the pressure
CSVs contain 2,526,000 rows / 80,832,000 numeric fields. These totals describe
source requests only; no fraction of measured runtime or extrapolated full2Tv
wall time is assigned to them.

## Future optimization boundary, conditional on physical acceptance

It is possible to prepare a distinct reduced-observation variant while retaining
the same pressure/J/four-force arithmetic. This is future work, not an edit or
admission of the active program. A low-risk first target is saved-row formatting
and chosen observation frequency, keeping all physical native saves and necessary
guards. Fixed-size host arrays could also replace allocation of Stats/RateInfo
vectors without changing their exact comparisons.

The firstRows full D2D allocation/copy serves first-round evidence and saved q2
coherence; it is not consumed by the P2 pressure update. A future sampler could
copy it only before genuinely selected saves, with honest new copy counts and
exact actual-clock save selection. It must not claim the present N first-row
copies or retain stale firstRows at an observed save. First validation itself
must still run each update before another MapCheck can reset its error packet.

HG snapshot copies, Core snapshots and their byte comparisons are read-only
coherence diagnostics. Dropping just their captures would make the existing
PrepareKernel compare stale data and reject, so they cannot be individually
deleted from the current host-only source. Any conditional reduced validator
would require separate source/object provenance and an unchanged numerical
path proof; PrepareKernel's real q + R/S solve and RN/FTZ store must remain.

Do not simply delete or reduce all 26 GetError calls. A failed map must be caught
before a dependent kernel dereferences slots. Row/core/finite/S/R/raw errors must
be caught before pressure write; first actual-BC/J/P0 validation before copying
the evidence or resetting Error; final actual-BC validation before CommitDevice
and history rotation. Errors must not be erased by a later ResetError. Any
batching requires a proven error-latch and safe-dependency design, not merely
the observation that copies are small. Original HG/geometry/drainage/ledger and
necessary-step safety gates cannot be removed to gain speed.

Likewise endpoint readonly-HG reduction combines diagnostic totals and real error
reporting. Its force-add kernel is numerical. A future smaller error packet or
less frequent nonessential totals could be considered only while retaining the
finite/mass/owner safety outcome and original force arithmetic. Nothing here
qualifies that optimization or predicts its speedup. Full2Tv planning should
distinguish actual solver cost from the present instrumented qualification cost.
