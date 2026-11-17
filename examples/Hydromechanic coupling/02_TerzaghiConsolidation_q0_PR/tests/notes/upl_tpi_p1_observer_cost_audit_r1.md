# P1 GPU observer cost: static audit, no timing or optimization performed

2026-11-17. Author inspected the actual passed private source tree
`outputs/upl_tpi_p1_loadclock_GPU_r1_source`, bound by
`logs/upl_tpi_p1_loadclock_GPU_r1.prepare.json`. No program, GPU command, benchmark,
solver/reader/build, Git, cleanup, or old analysis was executed. The active B10us2s
owner/program/dependencies are unchanged. This note is a production-planning audit,
not a measured overhead, speedup, physical acceptance or optimization admission.

## 1. Numerical work versus observational work

Default A has the original two force evaluations. P1 B has three: predictor at old
state, corrector at half state, and full-state endpoint force/rate. The actual staged
load source has these at `JSphGpuSingle.cpp:893,906,1224`; only the load clock changes.
The third pass supplies the complete endpoint acceleration feedback and R_gamma;
it is part of the selected numerical method, not a removable observer. Keeping only
the old two forces would change the pressure scheme and requires new mathematics.

Keep the ID-owned pn/previous history, actual predictor/guess float/BC values,
leading S and full R_gamma, one pressure write/BC/history commit, original solid/J
updates and original HG force/history arithmetic. Same-stage wall/periodic closure,
current-J mixture inertia and real finite-Kw diffusion reference bounds also remain.
A slot map needed to resolve sorted particles to native history is functional data,
even when repeated validation of that same mapping is observational.

## 2. Precisely identified synchronization/copy sites

The following are **static source-call counts in a successful ordinary P1 step**,
not a complete profiler event count. CUDA synchronous copies can impose host/device
or stream-order waits; they are not all cudaDeviceSynchronize calls. Timers, cell
sorting, lower-level wall closure and other reductions can add work not totaled here.

| Component and actual source | Static calls / character | Meaning |
|---|---|---|
| `upl_tpi_gpu_r1.h:170-211`, `cuh:41-42` | 14 GetError small D2H copies per full step | Begin2, Corr2, CaptureJ2, Guess1, StartEndpoint2, Prepare1, Write1, Commit3. These force host observation of latched device guards. |
| `h:136`, called Begin/Corr/CaptureJ/StartEndpoint/Commit | 5 MapCheck sequences per step | Each resets the error packet H2D, memsets slots, launches MapKernel+CheckMapKernel, then D2H error. A sixth error-reset H2D occurs in Guess. Repeated map/guard synchronization is a candidate for later fusion; ownership itself is not optional. |
| `h:183-185`, `cuh:136-146` | Core snapshot plus2 D2D arrays each step | Endpoint snapshots compare soil x/v/rho/sigma/kappa/P0/p/J and HG history/rate. HG copies are2*1000*sizeof(double2); this is device bandwidth, not per-ID D2H. |
| `cuh:38-39`, h186/208 | 2 cudaMemcpyToSymbol descriptor publications per step | Activate/clear actual endpoint capture. The capture trigger is needed in this implementation; its publication mechanism could later be coalesced without changing rows. |
| `h:188-197` | 1 extra HG reduction D2H per step | The readonly endpoint HG addition is physics-required. Its dedicated host validation/reduction plumbing is separable only if original finite/ID/force invariants remain enforced. |
| `h:137-140,183,201-203` | Host vectors/39 scalar comparisons per endpoint | Stats24+RateInfo15 are host values; these accesses are not hidden per-ID GPU getters. They allocate/copy small host vectors and prove readonly behavior. |
| `JSphGpuSingle.cpp:774` | 3 explicit cudaDeviceSynchronize calls for B,2 for A | One in each Interaction_Forces call. This is existing force-path behavior, repeated by the genuine extra force, not created by the light loadclock helper. |
| `JSphGpu.cpp:1902-1925,1944-1961` | 4 D2H calls per DtVariable, hence12 over3 force states | Original dynamic scale returns2 values together plus invalid; M0 skeleton pass returns skeleton2max plus invalid. Old Kw wave is diagnostic, but the same first pass also supplies mandatory true-Kw hydro/domain guards; deleting the whole call would remove required checks. |
| `JSphGpu.cpp:1867-1895` | at least1 invalid D2H per force here | Original dynamic rate safety. Constant k disables the optional maxspeed D2H; same-stage periodic/wall operations may add their own scalar checks. |
| `JSphGpu.cpp:1796-1812` | 2 original porosity invalid D2H checks per step | Predictor/corrector J integration guards. They are independent of observer snapshots. |

The 14-error count excludes initialization, ordinary saves and failure cleanup.
The direct device-error packet is only two unsigned integers, so its call/ordering
cost may matter more than its bytes; that is a risk, not a measured bottleneck.
Array Reserve/Free in the scale routines uses the existing JArrays pool; it must
not be reported as a new cudaMalloc/cudaFree on every call without tracing the pool.

Other original per-force work includes CTE upload (`JSphGpu_ker.cu:195`), normalized
band reduction (`:1211`), ViscDt/Ace maxima (`ReduMaxFloat :104-124`), and dynamic wall
closure. These serve force/bound semantics. Their additional invocation in F2 follows
from the numerical method; this audit does not count them twice in a grand total.

## 3. Original HG gates and save-time diagnostics

`JSphHourglassGpu.cpp:64-66` reduces/copies its scalar guard packet. EvaluateRate,
AddHistory and UpdateHistory use it to enforce IDs, finite state, density, elastic
scope, rank, tau/spin and virtual-work checks. Predictor/corrector force/history
counts remain2N/N/N with2N ratecalls. Preserve these actual physical guard conditions;
they are not removable merely because some exported maxima look diagnostic.
The endpoint helper adds committed HG force by bulk device pointers; GPU
GetHistory(id)/GetRate(id) D2H getters at HG.cpp182-186 are **not** used in its step loop.

Ordinary `upl_tpi_gpu_r1::Saved` (h213-218) adds2 error-packet D2H checks and one bulk
1000-Observation D2H per saved part, then formats1000 pressure-history CSV lines and
flushes. This is additional validation/output, not the physical pressure integration.
The original native save already transfers the required state arrays to host through
`JSphGpu.cpp:862-880`; native22 schema/actual IDs/clock/signed records remain required.
Do not remove native fields or lower saved cadence merely to advertise speed.

The new loadclock helper contains no CUDA API or per-ID loop. It performs host phase
and q checks, accumulates6 actual site counters per step, and emits only one44-column
row per native save. The M0 interval helper likewise writes one19-column row per save.
Their host guards/flushes are separate from the much larger pressure-observation CSV.
Initial device source/role fixtures, allocations and final cleanup are startup/exit
costs, not per-step observations. No removal is proposed for the current run.

## 4. Minimal future production separation, after accuracy admission

A sensible first optimization candidate would keep the entire three-force numerical
path, real kernels/arithmetic/order, readonly endpoint HG addition, per-ID guards and
all original signed/native/HG safety gates. Separate validation-only core/HG snapshots,
full pressure-observation collection and CSV formatting from the numerical/history
state. Prefer compact per-save/final counters for that audit evidence; no new public
parameter or change is selected by this note.

Next consider fusing error checks into the device stages, reusing the ID map only
across proven no-sort intervals, and joining guard scalars into existing necessary
host reductions. A fused implementation must still reject invalid rows/owners before
any pressure/history commit. It cannot merely postpone a failing host check until
invalid pressure/history has already been accepted. Slot ownership, positive-zero
Dirichlet validation, finite/overflow checks and exact-once commit are mandatory.
The original HG tau/spin/work/elastic checks and method-specific signed dterror stay
active. Any kernel/arithmetic fusion is another numerical-regression candidate,
not an assumed observer-only deletion or an excuse to relax thresholds.

For each such new private candidate, root would need a genuine same-input/same-clock
no-feedback regression against the frozen checked program: actual whole shared saves,
all22 typed native payloads and IDs, actual scalar/Step/dt and **signed** clock records,
with native headers retained. Five derived exports/rounded CSVs or normal exit are
not an all22-bit proof. Compare pressure history/actual BC floats and HG memory/rates
through explicit bounded snapshots as needed, because native22 alone does not expose
all hidden HG/history state; do not claim exact-HG restart from this exercise.
Only observer counters/files intentionally removed may differ, documented separately.
The default-A/OFF path needs its own unchanged native regression as before.

After that evidence and accuracy acceptance, controlled timing could establish whether
removing this work matters on the target GPU. This note supplies no timing estimate,
CPU/GPU speedup claim, automatic production merge, build, new solve or cleanup action.
