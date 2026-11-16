# P1 actual-helper CPU component author draft

2026-11-17, Asia/Tokyo. Authoring only; this file and its new C++ source have not
been compiled or executed by this author. No solver, native reader, VTK,
previous component, build, Git or SHA scan is launched here. The already
prepared/frozen three main author assets are not modified by this component.

`tests/support/upl_tpi_cpu_component_r1.cpp` includes the actual
`upl_tpi_cpu_r1.h` and the final-A frozen `DualSphDef.h`/
`JSphHourglassCpu.h`. Compilation must resolve those two frozen base headers
from `outputs/upl_spr_av_ReleaseCPU_r1_source`, not a live C08/current-public
class ABI. The runner is a separate root-reviewed task. The component needs no
real HG object or library: its fake observer uses the actual public
`JSphHourglassCpu::StStats` and `StRateInfo` types, public-accessor shape, and
explicit fixture values. It does not invoke or qualify the real HG solver.

## Process and filesystem contract

The selector is cached by the actual helper. B and C must be separate process
invocations. The command shape for a separately authorized runner is:

`component.exe --scheme B --output FRESH_DIRECTORY_B`

`component.exe --scheme C --output FRESH_DIRECTORY_C`

The process sets its private `UPL_TPI_CPU_R1` value before the helper first reads
it. A new output root and new fixture subdirectories are required; existing
directories are rejected. Only real-helper policy/CSV/summary sidecars for
constructed fixtures and `component.summary.json` are written there. All are
component evidence, not particle/native simulation output. The parent output
directory must already exist. No retry/overwrite behavior is included.

Each fixture destructs and placement-reconstructs the one global `State`,
closing its previous CSV before the next fixture. This resets only a fresh
test-local object, never a running simulation. The process selector remains
unchanged. The final JSON reports actual assertion/rejection/fixture counts;
these numbers are not predicted or claimed passed in this author note.

## Coverage

- Actual B extrapolation and actual C alpha0 path with NaN previous; B must
  reject that NaN. Nonfinite pn, unsupported alpha and extrapolation overflow
  are rejected. C's history buffer remains auditable but contributes nothing
  to its pressure prediction.
- Actual `SolveBeta0`: single defect correction and nonzero-S/R=0 fixed point;
  zero/negative/NaN S, nonfinite residual/q and float-output overflow reject.
  True Dirichlet returns positive zero before inactive q/S/R checks. This
  verifies the selected leading-LP preconditioned row arithmetic, not a full
  Jacobian or a converged implicit solve.
- Sparse real ID ownership, slot permutation and a periodic soil copy;
  original-owner history follows IDs. Lost/duplicated native owner, changed
  native role, unowned copy, soil-to-fixed copy and fixed-to-soil copy reject.
  A correctly typed periodic fixed copy remains a copy, not another owner.
- A complete actual-helper transaction: Init, initial Saved, Begin, Corr,
  CaptureJ, Endpoint, Rows, PrepareFinal, WriteFinal, declared pressure BC,
  Commit, Saved and Finish. Two constructed complete steps include a sort
  between steps, a single history rotation per complete step and unchanged P0.
  A duplicate Commit must fail without incrementing commits or rotating
  history. Fixture position/stress/J values are declared test inputs; this is
  not a second solid/material/porosity integrator or an SPH trajectory.
- Failed/missing/duplicate/nonfinite/overflow row validation occurs before
  final pressure write. Physical pressure at the endpoint guess, previous
  history and commits must remain unchanged. Premature WriteFinal rejects.
  Altered P0 rejects preparation. After a valid row write, an arbitrary finite
  pressure replacement rejects Commit, leaving history/commits unchanged;
  this does not claim that the deliberately corrupted test buffer is rolled
  back. True-Dirichlet minus-zero is rejected because Commit requires +0 bits.
- Source-clock BC: a separately declared fixture predicate labels t=tD as
  pre-open and strictly later FS2/FS3 as drained. A new FS3 identity and its
  actual zero projection at the next source step are accepted. Previously
  saved final pressure, previous history and P0 are not retroactively changed;
  only the successful next whole-step commit rotates the actual post-BC pn.
  An arbitrary non-Dirichlet source pressure change rejects. This tests the
  helper's callback/lifecycle; it does not independently prove the production
  `IsHydroMechDrainageActive` clock-tolerance implementation.
- Read-only HG: expected acceleration is produced by an independent literal
  transcription of frozen `ParticleMass`/`AddHistory` operation order with
  current J, double ax/az and the final float write. It is compared bitwise
  with the actual adapter. The fixture must distinguish current J from unit J;
  fixed particles, periodic copies and y components remain unchanged.
  Actual CaptureHG/CheckHG must leave/check each ID's history/rate, all 11
  unsigned plus 13 double Stats fields and all 15 RateInfo doubles. Separate
  single-field mutations must be caught for every explicit field and both
  history/rate vectors. No structure-padding comparison is used.

## What this does not establish

This component does not test the real neighbor rows, whole force sequence,
original native clock/22-array decoder, nonuniform pressure BC geometry,
CPU/GPU agreement, M0 physical theory, SPH stability, real HG correctness,
exact pressure/HG restart or any benchmark. In particular native
`PorePressRate` remains the original Kw/n-scaled endpoint-residual diagnostic
and is not the B/C dp/dt. Default-OFF native regression and separately admitted
short CPU implementation jobs remain necessary after the root-reviewed build
and component results. No physical solver, half chain, new PRE or full2Tv is
automatically started by a successful component.
