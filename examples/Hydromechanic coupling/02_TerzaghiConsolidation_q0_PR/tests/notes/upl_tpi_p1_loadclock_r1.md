# P1 staged external-load clock: private author draft only

2026-11-17. Three new author assets: `support/upl_tpi_p1_loadclock_r1.h`,
`support/upl_tpi_p1_loadclock_r1_prepare.py`, and this note. They prepare no source,
program or physical result until root separately reads and admits an action.
No prepare/build/help/solver/native/VTK/Git/hash has been executed by this author.
H3 drafts remain on HOLD, are not imported, and are not part of this candidate.

## 1. Numerical change and fixed scope

Keep the existing private M0-r2/P1 Symplectic sequence:

| Force call | Actual mechanical/pressure state | Load evaluation time | BC/history/ledger source time |
|---|---|---|---|
| F0 | old full state; original predictor force | scalar t_n | original scalar t_n / Nstep n |
| F1 | predicted half state; original corrector force | t_n+dt/2 | original scalar t_n / Nstep n |
| F2 | committed full state; existing readonly endpoint force/pressure row | t_n+dt | original scalar t_n / Nstep n |

Only the host evaluation time of the original q(t) ramp changes. The physical q0,
ramp duration, normalized resultant, support band and spatial formulas do not change.
The temporal forcing does change the numerical trajectory during the ramp; this is
not output-only instrumentation. It might remove part of the nonautonomous forcing
lag, but the original pressure history and leading-LP single defect remain first
order in general. No second-order, paper-LF, repair or physical acceptance is claimed.

Retain dt=tD/1000=10.00022888183594us, alpha=.5, beta0, real finite Kw in existing
physical diagnostics, constant k, original M0 Eq40/Rh1 necessary policy, FreeSlip,
SPR1, grad1, AV.1, damping.04, HGxi.1, kernel/eta/material/geometry and all safety gates.
The original three force order, material/J/position update counts, pressure scratch,
actual pressure BC, full endpoint residual, ID-owned history and existing 28-column
pressure sidecar are untouched. No force, material/J update, iteration, reference,
half chain, filter, AS, shifting or other parameter is added.

Private selector: `UPL_TPI_P1_LOADCLOCK_R1=STAGED`, in addition to original
`UPL_TPI_CPU_R1=B` or `UPL_TPI_GPU_R1=B` and `UPL_TPI_M0_DT_R1=EQ40_RH1`.
The new Init rejects C, non10us or nonfresh owners. No public XML is introduced.
When original pressure mode is A/OFF, Enabled returns false before inspecting the
new selector or touching context; the old q expression is the literal false branch.
With B and absent new selector the original source-clock P1 path remains selected.
These are implementation intentions, pending actual CPU Debug and default-A regression.

## 2. Source closure and exact patch sites

Prepare each backend separately from the already passed full frozen r2 tree:

| Backend | Complete base | Actual passed build ancestry | New output |
|---|---|---|---|
| CPU | `logs/upl_tpi_m0_dt_CPU_r2.prepare.json`,267files | `logs/upl_tpi_m0_dt_DebugCPU_r3.build.json` | `outputs/upl_tpi_p1_loadclock_CPU_r1_source` |
| GPU | `logs/upl_tpi_m0_dt_GPU_r2.prepare.json`,270files | `logs/upl_tpi_m0_dt_Release_r2.build.json` | `outputs/upl_tpi_p1_loadclock_GPU_r1_source` |

New trees contain268/271files respectively, adding only the new host header.
Exactly two old host sources change per backend: `JSphCpu.cpp`/`JSphCpuSingle.cpp`
or `JSphGpu.cpp`/`JSphGpuSingle.cpp`. Old class headers, old TPI helpers, M0 header,
CUDA source/private cuh/device structures, HG classes and all other source bytes
are copied identically. No C08/old active or retired process dependency is modified.
GPU therefore requires no CUDA/object rebuild for this candidate; later builder
must prove only the two new host objects replace their exact base objects and must
retain actual old flags/link order. This note performs no compilation/object reuse.

The q0/tramp source sites, read directly from actual r2 sources, are:

- CPU `JSphCpu.cpp:1264-1265`: direct top acceleration;
- CPU `JSphCpu.cpp:2343-2345`: pair/raw kernel-band pressure;
- GPU `JSphGpu.cpp:801-804`: ConstantDataUp raw-band CTE pressure;
- GPU `JSphGpu.cpp:1204-1205`: direct top acceleration.

The prepare script checks exactly two occurrences in each base TU and changes them
in their actual source order (CPU direct/raw; GPU raw/direct). Each new true branch
calls Evaluate(this,TimeStep,q0,tramp,site); the false branch retains the old expression.
Evaluate receives the real source time but computes q using the explicit force context.
The same returned double q and original float/acceleration conversion feed the existing
force paths; recorded q is that actual returned double, not a new force estimator.
Raw-band CTE pressure and direct-load target use the same stage time/q, preserving
normalization pairing. No temporary write to global TimeStep/Nstep is used.

The two Single TUs add Enter/Leave around the existing force+DtVariable calls:

- CPU `ComputeStep_Sym` at972-973 and983-984; endpoint1409-1410;
- GPU `ComputeStep_Sym` at891-892 and902-903; endpoint1213-1214.

Existing force/pressure/HG/J calls remain in place; no old block is reordered.
Enter precedes the actual force, Leave follows its actual DtVariable check.
An exception leaves an incomplete context and the original failed run/partials;
there is no retry, fake completion, native save or pressure-history recovery.
The original Init/Saved/Finish hooks at CPU1370/1579/1457 and GPU1177/1350/1251
are followed by separate load-clock hooks, without modifying the old receipts/schema.

## 3. Context lifecycle and initial configuration exception

The new host-only context is owned by the same canonical JSphCpu/JSphGpu base owner.
Enter rejects duplicated/open force calls, wrong phase/owner/step, changed fixed dt,
and a scalar source time differing from the actual +=dt history. The phase order
is exactly F0/F1/F2. Leave requires one real DirectTop and one real RawBand evaluation
for the bounded C02 closure, increments actual force/site counts, and advances its
own audit completion only after F2. It never changes global solver state.

Read-only source review confirms CPU's raw evaluation is inside the !boundp2 guard;
the two template calls do not mean two raw q evaluations. GPU ConstantDataUp is called
once within each force. Thus each site is actually expected once per force here.
All recorded counts are actual Evaluate/Leave observations, not inferred only from
solver exit or a nominal step count.

GPU LoadCaseParticles calls ConstantDataUp before InitRun/new Init (Single.cpp383).
The helper explicitly permits nonforce configuration evaluation only at true TimeStep0,
before any completed update and before Finish, using the original t=0 ramp. Such calls
are counted separately as cold configuration evaluations, never physical stage calls.
Initial SaveData occurs after Init; SaveData/FS tracking itself does not evaluate q.
A nonzero-time out-of-force evaluation rejects rather than silently borrowing an old
phase. The admitted frozen case has no DDTRamp/ViscoTime/moving-load schedule; extension
of those clock users is outside this candidate.

## 4. Low-cost sidecar semantics

`UplTpiP1LoadClockR1.policy.json` declares selector/backend, fractions[0,.5,1], fixed dt,
original BC/global-clock and pressure/HG/J retention, with physical_acceptance=false.
`UplTpiP1LoadClockR1.csv` has44columns and exactly one line per real saved native part,
including initial state. No per-step/per-ID pressure CSV is added. It stores:

- true part/time/saved-step/completed updates/dt and last true source time;
- the last actual three evaluation times and returned q doubles;
- actual interval/cumulative three force calls and six phase/site evaluation counts;
- interval min/max evaluation time/q and explicit initial empty sentinels;
- separate initial configuration evaluation count.

The existing large P1 pressure sidecar is not duplicated or changed by this patch.
At completion `UplTpiP1LoadClockR1.summary.json` seals actual counts/end clock. For N
complete updates all three force counts and each of the six site counts must equalN.
These are implementation observations only; they are not an applied-force budget,
M0 residual convergence, pressure accuracy or full-cycle acceptance. Actual LoadAce
and original same-stage checks remain separate evidence. DBL_MAX/-DBL_MAX in the
empty initial interval are declared sentinels, not physical extrema or dterror.

Original native22 fields, scalar clock, signed dterror/M0 interval, ID/ledger/P0,
FS/true drainage, HG tau/spin/work and pressure/J arithmetic gates remain mandatory.
The initial signed native diagnostic is untouched. Existing P1 endpoint pressure
replay remains meaningful because it is still a genuine full endpoint residual;
the new load-clock sidecar needs its own narrow independent review. There is no H3
reflection/half-residual schema in this candidate.

The saved event completed1000 is still pre-open; completed1001 is post-open.
At F2 of source step999, q may reach q0 at its endpoint time while source-clock
Dirichlet remains closed. That is the explicitly chosen load-versus-BC stage contract,
not a shifted drainage event. Record/verify both meanings without relabelling an old save.

## 5. Independent source preparation and future actions

The prepare script accepts only a new root admission with
stage=`upl_tpi_p1_loadclock_r1.prepare_admission`, passed/prepare_only=true,
backend CPU or GPU, and exact stat inputs. Required collector inputs are the three
author files, that backend's base prepare and actual passed build receipt, and every
file listed by the base prepare. No raw BI4/native array/object/EXE hash is needed.
It pins consumed metadata, copies only to a new absent directory, writes a unified
diff and new receipt, and retains any failure/partial without overwrite/retry.

Expected receipts: `logs/upl_tpi_p1_loadclock_CPU_r1.prepare.json` and GPU counterpart;
stage=`upl_tpi_p1_loadclock_r1.prepare`. Their files/base_source_entries/source_diff
bind the complete new closure; original/pinned_snapshot point to old/new stat records.
changed_sources/recompile_sources are the two host TUs; changed_headers is only the
new free host header; class/device ABI flags remain false. Other source, pressure
schema, M0 policy and CUDA/cuh byte-identical flags are checked by direct byte equality,
not assumed from path labels or asserted by compilation.

After root's full read only, a separately admitted source-only action could be:
`python -B tests/support/upl_tpi_p1_loadclock_r1_prepare.py --backend CPU --admission NEW.json --execution-authorized`.
This note does not authorize that action. No program/help/solver/native/Git follows.
Subsequent actual CPU Debug, new selector/component checks, default-A/OFF native
regression and one bounded physical window require root's independent admissions.
Public TPI/XML,20us/full2Tv and all changed physical budgets remain unaccepted.
