# GPU Port Plan for the CPU u-pw PR Prototype

This document is a read-only planning note for porting the current CPU-side u-pw PR prototype to GPU. It does not describe an immediate CUDA patch. The goal is to separate core production requirements from CPU-only diagnostics and to define a staged CPU/GPU parity path.

## Current GPU Port Status, 2026-05-12

The original passive GPU G1 gate has been completed and expanded through the
explicitly scoped G1-G9/B5 sequence. This file is now a living status and
planning note for the u-pw GPU PR path, not a pre-GPU blocking document.

Completed GPU-side production pieces include passive `PorePressg`, PR
diagnostics, pressure update and `dt_pore`, top drained / bottom no-flux layer
corrections, feedback operator `1`, hydromechanical damping, Shepard
regularization, Scenario 2 short/medium/long GPU runs, and the experimental
mode `1` boundary-operator GPU path.

The active next phase is Scenario 1 staged workflow planning/execution. The
recommended first route is the `BodyGravityStopTime` single-run workflow, not a
GPU restart workflow.

L3 1D consolidation loading-route audit is complete. The paper-aligned L2
external-load setup ran on CPU and GPU, but its top-layer `AccInput` route
created a strong dynamic excess-pressure peak and is not a strict surface-load
validation. The L3a initial-pressure gate uses existing CPU/GPU
`PorePressureInit=3`, top drained, and bottom no-flux support with no
mechanical `AccInput`; CPU and GPU both completed with `code=0`,
`excluded=0`, `DtMin=0`. This route is now the recommended PR
diffusion/boundary gate. A paper-faithful mechanical top-load route remains
future source/design work; broad damping/viscosity sweeps remain deferred.

Cryer C1 baseline launch workflow is complete: the reduced Cryer XML and
example-style CPU/GPU Release BATs are available under
`examples/u-pw/03_Cryer_Problem/`. Cryer C2 reference/geometry/boundary audit is
now documented. Strict Cryer remains unvalidated because the current XML is a
reduced workflow, the analytical reference is not yet implementation-ready, the
geometry is not a strict sphere, and the drained curved boundary/all-around
traction route is not locked. The next Cryer step should be either C3-A
reduced manual-run center-pressure extraction or C3-B strict geometry/reference
setup. No Cryer GPU-specific development should start before the CPU reference
and geometry are settled.

Cryer C3-B strict preparation has now started the strict track. It records the
PDF-checked center-pressure formula, recommends a true 3D sphere as the first
strict geometry, and marks all-around spherical traction plus drained curved
hydraulic boundary as the remaining formulation blockers. The next Cryer phase
should be C4-A reference-script validation before any source or GPU work.

Cryer C5f has now normalized the CPU-only boundary-particle drained weighting
for `CurvedDrainedBoundaryMode=4`. The normalized mode reduces raw mode-4
over-drainage and pressure-rate artifacts, but the compression center peak
remains too high for quantitative Figure 7B comparison. The strict Cryer path
therefore remains CPU-first and boundary-method-first. GPU support for
`FlexibleConfiningStress`, `PorePressureBoundaryOperator=3`,
`CurvedDrainedBoundaryMode=4`, and `HydraulicElevationSource=0` remains
deferred/unsupported.

Cryer C5g has completed one modest CPU-only dp / sphere-geometry diagnostic.
The finer sphere (`dp=0.008` versus `0.010`) reduced center averaging noise and
lowered the compression center peak from `7.448 p0` to `7.058 p0`, but it did
not materially reduce the compression surface residual. Geometry is therefore
a contributor, not the main blocker. C6 remains premature; the next Cryer work
should focus on MLS / flux-consistent drained spherical boundary coupling
before any broader resolution study or GPU work.

Cryer C5h-C5i are now complete. C5h showed that one higher-resolution sphere
does not make the boundary behavior monotone or C6-ready. C5i added a
postprocessing-only 1D finite-volume radial diffusion gate and found that the
current normalized mode-4 spherical drained boundary behaves like an
over-strong, nonuniform Robin-like boundary rather than a true drained
Dirichlet condition. The next Cryer task should be CPU-only MLS /
flux-consistent drained boundary design and validation; GPU remains deferred.

Still out of scope unless separately requested:

- GPU `PorePressureBoundaryOperator=2`;
- corrected-gradient PR production operators;
- GPU softening;
- Scenario 1 restart workflow;
- field-scale landslide reproduction.

## G1 Passive PorePressg Status, 2026-05-11

The first GPU phase has been implemented in the explicitly limited passive
scope:

- `PorePressg` is allocated, released, resized, sorted, and duplicated for
  periodic particles.
- `PorePressg` is initialized from a CPU temporary buffer for
  `PorePressureInit=0`, `1`, and `3`.
- GPU output now writes `PorePress` and `ExcessPorePress`.
- No GPU PR rate, feedback, Shepard, damping, boundary ghost, or softening
  kernels were added.

GPU Debug build succeeded. The G1 hydrostatic smoke case in
`examples/u-pw/01_1D_Consolidation/experiments/GPU_G1_PorePress/` completed
with `code=0`, `excluded=0`, `PorePress`/`ExcessPorePress` fields present,
`ExcessPorePress` maxAbs `0`, and hydrostatic maxAbs error about
`4.9e-4 Pa` from CSV precision.

Next allowed phase is G2 planning/implementation only if explicitly requested.
G2 must not expand beyond PR diagnostic arrays/kernels unless separately
approved.

## G2 PR Diagnostics Status, 2026-05-11

G2 has been implemented in the explicitly limited diagnostic-only scope:

- GPU arrays `PorePressRateg`, `DivVelg`, `LapPorePressg`, and `LapZg`
  are allocated, released, resized, sorted, and duplicated for periodic
  particles.
- A material-material GPU diagnostic kernel computes the current uncorrected
  production PR operators `DivVel`, `LapPorePress`, and `LapZ`.
- The diagnostic `PorePressRate` uses the CPU SW-2a sign convention:
  `Kw/n * (-DivVel + k/(rho_w*g_h)*LapPorePress + k*LapZ)`.
- GPU output now writes `PorePressRate`, `DivVel`, `LapPorePress`, and `LapZ`
  in addition to the G1 `PorePress` and `ExcessPorePress` fields.

This phase remains passive with respect to pore pressure and dynamics. It does
not update `PorePressg`, does not apply feedback, does not apply Shepard
regularization or hydromechanical damping, and does not port top drained,
bottom no-flux, boundary ghost, or softening logic.

GPU Debug build succeeded. A Debug smoke run showed a CRT dialog/hang for the
analytical-excess case after output, so the final smoke validation was run with
GPU Release. The hydrostatic and analytical-excess GPU Release smoke cases in
`examples/u-pw/01_1D_Consolidation/experiments/GPU_G2_PRDiagnostics/`
completed with `code=0`, `excluded=0`, and all G2 output fields present. The
hydrostatic case had `ExcessPorePress=0`, `DivVel=0`, head residual maxAbs
about `2.62e-5`, and diagnostic `PorePressRate` maxAbs about `17.5 Pa/s`.
The analytical-excess case produced nonzero `LapPorePress` and
`PorePressRate` with the expected diagnostic-only behavior: `PorePressg` was
not advanced.

Next allowed phase is G3 only if explicitly requested. G3 should be limited to
`PorePressg` update and `dt_pore` parity. It must still exclude feedback,
Shepard, damping, boundary ghost, softening, and long GPU runs unless those
scopes are separately authorized.

## G3 PorePress Update Status, 2026-05-11

G3 has been implemented in the limited explicit pressure-update scope:

- GPU `dt_pore` restriction uses the same formula as CPU:
  `PorePressureDtSafety * (rho_w*g_h*n/Kw) * h^2 / k`.
- The initial Symplectic timestep is limited by `dt_pore`.
- `DtVariable()` applies the same `dt_pore` cap during the GPU run.
- A GPU update kernel applies `PorePressg += PorePressRateg * dt` only to
  material/fluid particles.
- The update has no clamp, Shepard smoothing, top drained correction, bottom
  no-flux correction, feedback, damping, boundary ghost, or softening.

GPU Debug and GPU Release builds passed. The G3 micro-smoke cases in
`examples/u-pw/01_1D_Consolidation/experiments/GPU_G3_PorePressUpdate/`
completed with `code=0`, `excluded=0`, and finite output fields. The one-step
hydrostatic case kept `ExcessPorePress` near zero with maxAbs about
`8.33e-6 Pa`. The analytical-excess case changed pressure by about
`7.60 Pa` over one `dt_pore` step. GPU-vs-CPU one-step pressure-delta
differences were below `9e-6 Pa` in both smoke cases.

Next allowed phase is G4 only if explicitly requested. G4 should focus on the
remaining pressure-only parity pieces, especially GPU top drained and bottom
no-flux corrections and the minimum boundary/update ordering needed for the
1D diffusion baseline. GPU feedback, Shepard, damping, boundary ghost,
softening, and long runs remain out of scope until separately authorized.

## Current CPU Hydromechanical State

The CPU prototype currently owns the hydromechanical particle arrays in `JSphCpu`:

| CPU array | Type | Role | GPU priority |
| --- | --- | --- | --- |
| `PorePressc` | `double*` | Total pore pressure state | Required |
| `PorePressRatec` | `float*` | PR pressure-rate output | Required |
| `DivVelc` | `float*` | Mathematical skeleton velocity divergence, compression negative | Required |
| `LapPorePressc` | `float*` | SPH pore-pressure Laplacian diagnostic/operator | Required |
| `LapZc` | `float*` | SPH elevation Laplacian diagnostic/operator | Required |
| `PorePressureAcec` | `tfloat3*` | Symmetric stress-style pressure acceleration diagnostic | Optional compatibility only |
| `PorePressureAceDiffc` | `tfloat3*` | Difference-gradient pressure acceleration, current recommended feedback operator | Required |
| `PorePressureAceSymCorrc` | removed | Failed corrected-gradient symmetric diagnostic | Removed from CPU; do not port |

The CPU step sequence is:

1. Compute mechanical/stress acceleration.
2. Compute `DivVel`, `LapPorePress`, `LapZ`.
3. Compute pore-pressure acceleration diagnostics.
4. Add pore-pressure feedback to `Acec` when enabled.
5. Apply hydromechanical damping when enabled.
6. Compute `PorePressRate = Kw/n * (-DivVel + k/(rho_w*g_h)*LapPorePress + k*LapZ)`.
7. Limit timestep with `dt_pore`.
8. Update `PorePress`.
9. Optionally apply Shepard regularization.
10. Apply top drained and bottom no-flux corrections after the pressure update.

The GPU path currently has no equivalent pore-pressure arrays or kernels. It owns standard particle arrays such as `Idpg`, `Codeg`, `Dcellg`, `Posxyg`, `Poszg`, `PosCellg`, `Velrhopg`, `Sigmag`, `Kplasticg`, `Aceg`, and time-integration history arrays in `JSphGpu`.

## Arrays Required for the First Production GPU Port

The minimum useful GPU implementation should add:

| GPU array | Suggested type | Notes |
| --- | --- | --- |
| `PorePressg` | `double*` | Keep double for parity with CPU and restart precision. Revisit float only after parity. |
| `PorePressRateg` | `float*` | PR pressure-rate field. |
| `DivVelg` | `float*` | Diagnostic and PR volumetric term. |
| `LapPorePressg` | `float*` | PR diffusion term. |
| `LapZg` | `float*` | PR elevation-head term. |
| `PorePressureAceDiffg` | `float3*` | Recommended feedback acceleration (`PorePressureFeedbackOperator=1`). |

Temporary GPU buffers are also needed for:

- Shepard regularization numerator/denominator or output pressure buffer.
- Bottom no-flux reference-layer reductions: count, sum of excess pressure, and possibly min/max diagnostics.
- Top/bottom material elevation range reductions if computed on GPU.

The symmetric diagnostic `PorePressureAceg` may be ported later only if strict
backward compatibility with `PorePressureFeedbackOperator=0` is required on
GPU. The corrected symmetric diagnostic `PorePressureAceSymCorrc` has been
removed from CPU and must not be ported.

Corrected-gradient PR diagnostics (`DivVelCorr`, `LapPorePressCorr`, `LapZCorr`)
are also deferred. CPU-CG1 showed that the material-only corrected-gradient
diagnostics did not improve the hydrostatic or self-weight short smoke metrics
over the current production operators. The G1-G4 GPU baseline should therefore
port only the current uncorrected material-only PR operators:

```text
DivVel
LapPorePress
LapZ
PorePressRate
```

Do not allocate GPU correction-matrix arrays, fallback flags, or corrected PR
diagnostic fields in G1-G4.

## GPU Memory Lifecycle Work

The GPU port should mirror the current CPU lifecycle:

1. **Class members**
   Add GPU pointers in `JSphGpu.h`, probably near the existing particle arrays.

2. **Initialization and release**
   Initialize pointers to `NULL` in `InitVars()` and release them in `FreeGpuMemoryParticles()`.

3. **Allocation accounting**
   Extend `AllocGpuMemoryParticles()` in `JSphGpu.cpp` with the same conditional allocation used on CPU:
   `HydromechCoupling || SavePorePressure`.

4. **Reserve**
   Extend `ReserveBasicArraysGpu()` to reserve:
   - one `double*` array for `PorePressg`;
   - four `float*` arrays for `PorePressRateg`, `DivVelg`, `LapPorePressg`, `LapZg`;
   - one `float3*` array for `PorePressureAceDiffg`.

5. **Resize**
   Extend `ResizeGpuMemoryParticles()` to preserve the new arrays during particle buffer growth.

6. **Sorting**
   Extend `RunCellDivide()` in `JSphGpuSingle.cpp` to sort all hydromechanical arrays consistently with the main particle arrays.

   Current `JCellDivGpu` supports direct sorting for `float*`, `float3*`, `float4*`, `tsymatrix3f*`, and a combined `(double2*, double*, float4*)` position/velocity sort. There is no obvious direct `double*` sort overload for a standalone `PorePressg`.

   Recommended options:
   - Add a direct `double*` sort overload and CUDA kernel in `JCellDivGpu`/`JCellDivGpu_ker.cu`; this is the cleanest.
   - Avoid packing pore pressure into existing position sort calls; that would couple unrelated arrays and make future maintenance fragile.

7. **Periodic duplicate**
   Add duplicate handling for `PorePressg`, `PorePressRateg`, `DivVelg`, `LapPorePressg`, `LapZg`, and `PorePressureAceDiffg`, following the existing GPU periodic duplicate pattern.

## Kernel Coverage

### Required PR diagnostic kernels

Add material-material-only kernels equivalent to the CPU operators:

- `ComputeHydroDivVelGpu`
  - `DivVel` stores mathematical divergence.
  - Compression remains negative.

- `ComputeHydroLapPorePressGpu`
  - Uses total `PorePress`.
  - Material-material only in the first GPU port.

- `ComputeHydroLapZGpu`
  - Uses hydraulic elevation `z_h = -dot(pos, HydraulicUnit)`.
  - Requires hydraulic gravity constants on GPU.

- `ComputeHydroPorePressRatePRGpu`
  - Formula:
    `Kw/n * (-DivVel + k/(rho_w*g_h)*LapPorePress + k*LapZ)`.
  - This must preserve the SW-2a volumetric sign fix.

### Required pressure update and boundary kernels

- `UpdatePorePressureGpu`
  - `PorePress += dt * PorePressRate`.
  - Only material/fluid particles.

- `ApplyPorePressureTopDrainedGpu`
  - Time-gated by `PorePressureTopDrainedStartTime`.
  - Requires `zmax_material` and drain thickness.
  - Sets top layer total pressure to hydrostatic baseline.

- `ApplyPorePressureBottomNoFluxGpu`
  - Requires `zmin_material`.
  - Computes reference-layer mean excess pressure.
  - Applies bottom layer pressure as `hydrostatic + excess_ref_mean`.
  - Needs a reduction pass for reference count and sum.

- `ApplyPorePressureShepardGpu`
  - Material-material only.
  - First implementation can use one direct neighbor pass per regularized particle plus a temporary `double*` output buffer.
  - Mode 0 regularizes total pressure.
  - Mode 1 regularizes excess pressure and reconstructs `PorePress = hydrostatic + excess_reg`.
  - Top drained and bottom no-flux corrections must be applied after Shepard, matching CPU ordering.

### Required feedback and damping kernels

- `ComputePorePressureAccelDiffGpu`
  - Uses `PorePressureFeedbackMode`:
    - mode 0: total pore pressure;
    - mode 1: excess pressure relative to hydrostatic baseline.
  - Difference-gradient operator:
    `a_i = -1/rho_i * sum_j (m_j/rho_j) * (p_j - p_i) * gradW_ij`.
  - Material-material only.

- `ApplyPorePressureFeedbackGpu`
  - Adds `PorePressureAceDiffg` to `Aceg` before `ComputeAceMax` / `DtVariable`.
  - Only when:
    `HydromechCoupling=1`, `PorePressureModel=1`, `PorePressureFeedback=1`, `PorePressureFeedbackOperator=1`.

- `ApplyHydromechDampingGpu`
  - Adds `-c_d * velocity` to `Aceg`.
  - Use effective `HydromechDampingCoef`; the CPU already converts `HydromechDampingXi` to `c_d`.
  - Must run before `ComputeAceMax` / `DtVariable`.

### Timestep restriction

`dt_pore` can remain host-side because it depends on constants:

`dt_pore = PorePressureDtSafety * (rho_w * g_h * n / Kw) * h^2 / k`.

The GPU time loop must call the same limit point before accepting the final `dt`.

## Output and Restart

### Output

`JSphGpuSingle::SaveData()` currently copies standard GPU arrays back to CPU and then uses `JDataArrays`. The GPU u-pw port should reuse this path:

1. Copy `PorePressg`, `PorePressRateg`, `DivVelg`, `LapPorePressg`, `LapZg`, and `PorePressureAceDiffg` to CPU buffers.
2. Compute `ExcessPorePress` on CPU during output, using the same hydrostatic definition as CPU.
3. Add arrays to `JDataArrays`:
   - `PorePress`
   - `ExcessPorePress`
   - `PorePressRate`
   - `DivVel`
   - `LapPorePress`
   - `LapZ`
   - `PorePressureAccelDiff`

For the first GPU production path, do not output `PorePressureAccelSymCorr`. Symmetric `PorePressureAccel` can also remain CPU-only unless operator-0 compatibility is explicitly required.

### Precision

Keep `PorePress` as double on GPU for the initial parity implementation. The CPU path moved to double for stability and restart precision; changing precision during the port would mix formulation validation with numerical-storage changes.

### Restart

The first GPU port can keep pore-pressure restart CPU-only. Before GPU long runs are considered production-ready, restart should restore:

- `PorePress`
- soil stress/plastic fields already restored on CPU
- `Velrhop.w`

GPU restart parity should be treated as a separate phase after pressure-only GPU parity is complete.

## Temporarily CPU-only or Deferred Features

Keep these out of the first GPU port:

- `PorePressureAccelSymCorr` and corrected-gradient symmetric diagnostic.
- Boundary pore-pressure ghost / MLS / mDBC pore-pressure extrapolation.
- Corrected-gradient PR operators (`DivVelCorr`, `LapPorePressCorr`, `LapZCorr`) and any correction-matrix arrays.
- `PorePress` restart.
- Body-gravity stop/switch workflow.
- Deprecated source `TopLoad` path.
- Full diagnostic min/max logging from device reductions.

These are either not yet validated as production requirements or are better handled after the baseline GPU PR pipeline is stable.

## Minimum GPU Port Order

### Phase G1: passive pore-pressure GPU array and output

Goal: allocate, sort, duplicate, initialize, and output `PorePressg`.

Checks:
- hydrostatic initialization matches CPU;
- `PorePress` and `ExcessPorePress` output in BI4/CSV;
- sorting and periodic duplicates do not scramble the pressure field.

### Phase G2: PR diagnostics on GPU

Goal: compute uncorrected production `DivVelg`, `LapPorePressg`, `LapZg`, and
`PorePressRateg` without updating pressure. Do not port `DivVelCorr`,
`LapPorePressCorr`, or `LapZCorr` in this phase.

Checks:
- one-frame CPU/GPU comparison for pressure-only 1D column;
- `DivVel` sign remains mathematical divergence;
- hydrostatic consistency: `LapPorePress/(rho_w*g_h) + LapZ` remains near zero in the interior.

### Phase G3: pore-pressure update and `dt_pore`

Goal: update `PorePressg` using `PorePressRateg`, apply `dt_pore` restriction, and keep CPU ordering:

`update -> Shepard if enabled -> top drained -> bottom no-flux`.

Checks:
- pressure-only short run remains stable;
- `PorePress` evolution matches CPU within expected float/kernel tolerance.

### Phase G4: pressure-only 1D consolidation parity

Goal: reproduce the validated CPU pressure-only 1D diffusion benchmark.

This phase uses the current uncorrected production PR path. Corrected-gradient
matrix kernels are explicitly out of scope.

Checks:
- `A_fit(t)` decay trend;
- `ExcessPorePress` profiles;
- top drained and bottom no-flux layer behavior;
- CPU/GPU frame metrics within tolerance.

### Phase G5: feedback operator 1

Goal: implement difference-gradient pore-pressure feedback and add it to `Aceg`.

Checks:
- excess-mode hydrostatic case gives near-zero acceleration;
- uniform excess with no top drained gives near-zero acceleration, including top/bottom boundaries;
- nonuniform excess has the expected direction.

### Phase G6: Shepard regularization and hydromech damping

Goal: implement GPU Shepard and damping.

Checks:
- Shepard mode 1 preserves hydrostatic-only zero excess;
- damping modifies `Aceg` before `ComputeAceMax` / `DtVariable`;
- damping coefficient from `HydromechDampingXi` matches CPU because conversion remains host-side.

### Phase G7: self-weight Scenario 2 short parity

Goal: match the current stable CPU Scenario 2 short run.

Recommended parity case:
- body gravity and hydraulic gravity both `(0,0,-9.81)`;
- `PorePressureFeedbackMode=1`;
- `PorePressureFeedbackOperator=1`;
- `PorePressureShepard=1`, interval 10, mode 1;
- `HydromechDampingXi=0.10`;
- `PorePressureDtSafety=0.20`.

### Phase G8: long GPU release run

Goal: run the Scenario 2 long line on GPU release after all short parity tests pass.

Checks:
- excluded particles remain zero;
- `ExcessPorePress` envelope trends toward zero;
- total pressure trends toward hydrostatic;
- runtime is materially better than CPU release.

## Main Risks

1. **Standalone double sorting**
   `PorePressg` needs a clean `double*` sort path in `JCellDivGpu`.

2. **Boundary-layer corrections on GPU**
   Top drained and bottom no-flux need material elevation ranges and reductions. These should be implemented carefully and tested independently.

3. **Output parity**
   GPU output must preserve double `PorePress` and must not compute `ExcessPorePress` with a different hydraulic gravity/elevation convention.

4. **CPU/GPU ordering**
   The exact ordering around pressure update, Shepard, top drained, bottom no-flux, feedback, damping, and `DtVariable` matters. GPU should follow CPU ordering first, then optimize.

5. **Diagnostics creep**
   The GPU port should not carry every failed diagnostic path. `PorePressureAccelSymCorr` is useful history, not a production requirement.

## Recommended Next Action

Start with Phase G1 only:

- add passive `PorePressg`;
- keep double precision;
- implement allocation, free, resize, sort, periodic duplicate, output;
- run one hydrostatic-output parity case.

Do not start by porting the full feedback loop. The validated CPU path is now broad enough that GPU work needs small, auditable parity milestones.

## G4 Pressure-Only Boundary Status, 2026-05-11

Implemented in G4:

- GPU top drained correction:
  `PorePress = hydrostatic(z_h)` in the top material layer once
  `TimeStep >= PorePressureTopDrainedStartTime`.
- GPU bottom no-flux layer correction:
  the bottom layer excess pressure is set to the reference-layer mean excess.
- GPU reductions for material `zmax`, `zmin`, reference excess sum/count, and
  boundary affected counts.
- CPU/GPU pressure-only smoke templates and summary script in
  `examples/u-pw/01_1D_Consolidation/experiments/GPU_G4_PressureOnlyParity/`.

Validation summary:

- Static boundary smoke: GPU and CPU both finished with `code=0`,
  `excluded=0`, `steps=1`.
- Diffusion micro smoke: GPU and CPU both finished with `code=0`,
  `excluded=0`, `steps=5`.
- Top drained layer `maxAbs(ExcessPorePress)=0` in both GPU G4 smoke cases.
- Bottom layer minus reference excess maxAbs:
  - static boundary: `3.95e-08 Pa`;
  - diffusion micro: `1.60e-01 Pa`.
- GPU minus CPU `PorePress` final-frame maxAbs:
  - static boundary: `6.10e-05 Pa`;
  - diffusion micro: `2.10e-05 Pa`.

G4 does not include GPU feedback, `PorePressureAccelDiff`, Shepard,
hydromechanical damping, boundary ghost production operators, softening, or
long-time reproduction runs.

G5 may start only as a separately scoped feedback phase.

## G5 Difference-Gradient Feedback Status, 2026-05-11

Implemented in G5:

- GPU array `PorePressureAceDiffg` with allocation, release, resize, sorting,
  and periodic duplicate handling.
- GPU material-material difference-gradient feedback diagnostic:
  `a_pw = -grad(p_feedback)/rho`, where `p_feedback` is total pressure for
  mode `0` and excess pressure for mode `1`.
- GPU feedback application for `PorePressureFeedback=1` and
  `PorePressureFeedbackOperator=1` only.
- GPU output field `PorePressureAccelDiff`.
- Smoke templates and summary script in
  `examples/u-pw/01_1D_Consolidation/experiments/GPU_G5_Feedback/`.

Validation summary:

- GPU Debug build passed. A Debug hydro smoke wrote `code=0` but the executable
  did not exit cleanly, matching the earlier Debug-run behavior observed in G2.
  GPU Release was used for the final smoke validation.
- GPU Release hydrostatic, uniform-excess, and nonuniform-excess smokes all
  completed with `code=0`, `excluded=0`, `steps=21`.
- Hydrostatic and uniform-excess smokes gave
  `PorePressureAccelDiff` max magnitude about `4.01e-7 m/s2`.
- The nonuniform-excess smoke gave a nonzero feedback acceleration with max
  magnitude about `1.41 m/s2`.
- CPU/GPU final-frame `PorePressureAccelDiff` max-magnitude difference was
  about `4.86e-7 m/s2` for hydrostatic/uniform excess and `1.70e-2 m/s2` for
  the nonuniform excess smoke.

G5 does not include GPU Shepard regularization, hydromechanical damping,
boundary ghost production operators, corrected-gradient feedback, symmetric
operator `0`, softening, or long coupled runs.

G6 may start only as a separately scoped Shepard/damping phase if explicitly
requested.

## G6 Stabilization Status, 2026-05-11

Implemented in G6:

- GPU hydromechanical damping for the PR coupled path:
  `a_damp = -c_d v`, applied to `Aceg` after pore-pressure feedback and
  before acceleration reduction / timestep selection.
- GPU pore-pressure Shepard regularization using a temporary
  `PorePressShepardTmpg` buffer, material-material neighbors only.
- Shepard mode `0` regularizes total `PorePress`; mode `1` regularizes
  excess pressure and reconstructs total pressure from the hydrostatic state.
- GPU ordering now follows the CPU stabilization ordering for this stage:
  pressure update, optional Shepard, top drained correction, bottom no-flux
  correction.
- Smoke templates and summary script in
  `examples/u-pw/01_1D_Consolidation/experiments/GPU_G6_Stabilization/`.

Validation summary:

- GPU Debug and GPU Release builds passed.
- GPU Release smokes for damping off/on, Shepard hydrostatic, Shepard
  analytical excess, and coupled short all finished with `code=0`,
  `excluded=0`, and valid pore-pressure output fields.
- Shepard hydrostatic kept `ExcessPorePress` near zero:
  maxAbs about `2.87e-5 Pa`.
- Shepard analytical excess produced finite smoothing with final-initial
  `PorePress` maxAbs about `57.0 Pa`.
- Coupled short smoke with feedback, damping, Shepard, top drained, and
  bottom no-flux finished with `steps=21`; GPU/CPU final `PorePress` maxAbs
  difference was about `2.30e-5 Pa`, and `PorePressureAccelDiff` max-magnitude
  difference was about `1.32e-5 m/s2`.
- Generated particle/log outputs were cleaned after extracting
  `gpu_g6_smoke_summary.csv`.

G6 does not include GPU softening, boundary ghost production operators,
corrected-gradient PR production operators, symmetric feedback operator `0`,
or long coupled reproduction runs.

G7 may start only as a separately scoped short self-weight/Terzaghi-style GPU
parity phase if explicitly requested.

## G7 Self-Weight Short Parity Status, 2026-05-11

Implemented in G7:

- No source-code changes.
- Added a dedicated short self-weight Scenario 2 parity smoke in
  `examples/u-pw/02_SelfWeight_Consolidation/experiments/GPU_G7_SelfWeightParity/`.
- The smoke uses the CPU/GPU G1-G6 production GPU path:
  PR pressure update, dt-pore restriction, top drained, bottom no-flux,
  difference-gradient feedback operator `1`, hydromechanical damping, and
  excess-pressure Shepard regularization.

Validation summary:

- CPU Release reference: `code=0`, `excluded=0`, `steps=3147`.
- GPU Release smoke: `code=0`, `excluded=0`, `steps=3147`.
- Final-frame GPU minus CPU maxAbs differences:
  - `PorePress`: `2.60e-3 Pa`;
  - `ExcessPorePress`: `2.60e-3 Pa`;
  - `PorePressRate`: `8.77e4 Pa/s` versus a field maxAbs about `2.72e8 Pa/s`;
  - `PorePressureAccelDiff` magnitude: `1.47e-2 m/s2` versus a field maxAbs
    about `1.49e1 m/s2`;
  - velocity magnitude: `4.0e-9 m/s`.
- GPU top drained layer excess maxAbs was `8.50e-5 Pa`.
- GPU bottom no-flux proxy maxAbs was `4.71e-1 Pa`, comparable to CPU
  `4.72e-1 Pa`.

Generated particle/log outputs were cleaned after extracting
`gpu_g7_selfweight_summary.csv`.

G7 does not include long self-weight runs, Scenario 1 restart workflow on GPU,
GPU softening, boundary ghost production operators, corrected-gradient
production operators, or parameter sensitivity.

G8 may start only as a separately scoped long-GPU-release planning/execution
phase if explicitly requested.

## G8 Self-Weight Medium GPU Status, 2026-05-11

Implemented in G8:

- No source-code changes.
- Added medium-duration GPU Release self-weight Scenario 2 smokes in
  `examples/u-pw/02_SelfWeight_Consolidation/experiments/GPU_G8_SelfWeightMedium/`.
- The G8 smokes extend the G7 setup to:
  - `TimeMax=0.05 s`, `TimeOut=0.005 s`;
  - `TimeMax=0.2 s`, `TimeOut=0.02 s`.

Validation summary:

- `T0p05`: `code=0`, `excluded=0`, `steps=52437`, runtime `126.38 s`.
- `T0p2`: `code=0`, `excluded=0`, `steps=209747`, runtime `495.20 s`.
- The excess pressure envelope decreased after the early self-weight peak:
  - `T0p05`: peak maxAbs `2.77e4 Pa`, final maxAbs `1.67e4 Pa`;
  - `T0p2`: peak maxAbs `1.80e4 Pa` in the saved frames, final maxAbs
    `1.41e4 Pa`.
- Velocity also decreased over the medium run:
  - `T0p2` final max velocity `2.35e-3 m/s`, mean `1.71e-3 m/s`.
- Hydraulic boundaries remained stable:
  - final top drained excess maxAbs about `1.1e-5 Pa`;
  - final bottom no-flux proxy about `7.1e-3 Pa` for `T0p2`.

Generated particle/log outputs were cleaned after extracting
`gpu_g8_case_summary.csv` and `gpu_g8_frame_metrics.csv`.

G8 does not include 3.6 s reproduction, Scenario 1 restart workflow on GPU,
GPU softening, boundary ghost production operators, corrected-gradient
production operators, or parameter sensitivity.

The medium GPU self-weight path is stable enough to consider a separately
scoped 3.6 s GPU release run, but that run should remain a new explicit phase.

## G9 Self-Weight Long GPU Status, 2026-05-11

Implemented in G9:

- No source-code changes.
- Added a GPU Release 3.6 s self-weight Scenario 2 long trend run in
  `examples/u-pw/02_SelfWeight_Consolidation/experiments/GPU_G9_SelfWeightLong/`.
- The case uses the validated G1-G6 coupled PR GPU path with body gravity on,
  hydraulic gravity on, top drained active after `0.002 s`, bottom no-flux,
  feedback operator `1`, `HydromechDampingXi=0.10`, and excess-pressure
  Shepard every 10 steps.

Validation summary:

- GPU Release finished with `code=0`, `excluded=0`, `steps=3775438`,
  runtime `10946.52 s`.
- Saved-frame excess pressure declined from the early peak:
  peak maxAbs `1.56e4 Pa`, final maxAbs `1.16e3 Pa`.
- Total pressure approached hydrostatic:
  final `PorePress` max `10922.62 Pa` versus final hydrostatic max
  `9762.26 Pa`.
- Hydraulic boundaries remained stable:
  final top drained excess maxAbs `9.83e-7 Pa`;
  final bottom no-flux proxy `1.90e-4 Pa`.
- Final GPU versus CPU SW3h (`xi=0.10`) differences:
  - final `ExcessPorePress` max difference about `1.00 Pa`;
  - final `ExcessPorePress` mean difference about `0.56 Pa`;
  - final bottom excess mean difference about `1.00 Pa`;
  - final `PorePress` max difference about `1.01 Pa`.
- GPU speedup versus the committed CPU SW3h run was about `6.26x`.

Generated particle/log outputs were cleaned after extracting CSV summaries and
SVG figures.

G9 does not include parameter sensitivity, Scenario 1 GPU restart workflow,
GPU softening, boundary ghost production operators, corrected-gradient
production operators, or additional source-code changes.

## G9b Self-Weight xi=0.05 GPU Status, 2026-05-11

Implemented in G9b:

- No source-code changes.
- Added a GPU Release 3.6 s self-weight Scenario 2 `xi=0.05` comparison line in
  `examples/u-pw/02_SelfWeight_Consolidation/experiments/GPU_G9b_SelfWeightLong_Xi005/`.
- The case keeps the validated G1-G6 coupled PR GPU path and differs from G9
  only in `HydromechDampingXi=0.05`.

Validation summary:

- `code=0`, `excluded=0`.
- `steps=3,775,438`, runtime `12,888.19 s`, frames `37`.
- Final max excess pressure: `1110.17 Pa`.
- Final mean excess pressure: `695.39 Pa`.
- Final bottom mean excess pressure: `1110.00 Pa`.
- Final top drained excess maxAbs: `9.46e-7 Pa`.
- Final bottom no-flux proxy: `8.72e-3 Pa`.
- Saved-frame excess envelope decayed from peak maxAbs `15892.95 Pa` to
  `1110.17 Pa`, final/peak ratio `0.06985`.

Comparison:

- Relative to GPU G9 `xi=0.10`, the `xi=0.05` line ended with about `50 Pa`
  lower final max/bottom excess and about `30.6 Pa` lower mean excess.
- Runtime was about `1941.67 s` longer than GPU G9 `xi=0.10`.
- Relative to the committed CPU SW3h `xi=0.10` reference, the cross-damping
  speedup is `5.32x`.

Generated outputs:

- `gpu_g9b_frame_metrics.csv`;
- `gpu_g9b_case_summary.csv`;
- SVG and PNG comparison figures for profiles, bottom pressure, bottom excess,
  excess envelope decay, and CPU/GPU/hydrostatic reference comparison.

Generated particle/log outputs were cleaned after extracting summary CSVs and
figures.

G9b does not include Scenario 1 GPU workflow, GPU softening, boundary ghost
production operators, corrected-gradient production operators, parameter
sensitivity, or additional source-code changes. The `xi=0.05` line is suitable
as the paper-compatible Scenario 2 damping line; `xi=0.10` remains a useful
stability-diagnostic line.

## B4/B5 Boundary-Operator GPU Status, 2026-05-11

Implemented after G9b:

- Ported `PorePressureBoundaryOperator=1` from the CPU prototype to the GPU
  PR diagnostic/update path.
- `mode=0` remains the default legacy layer-correction path.
- `mode=1` now adds operator-level top drained excess-Dirichlet and bottom
  hydraulic-head/excess Neumann mirror ghost contributions to GPU
  `LapPorePress`, `LapZ`, and the derived `PorePressRate`.
- The existing post-update top drained and bottom no-flux layer projections
  remain active as safety corrections, matching the CPU `mode=1` prototype.
- `mode=2` remains unsupported/reserved.

B4 validation:

- GPU hydrostatic `mode=1`: `code=0`, `excluded=0`, top excess `0 Pa`,
  bottom proxy about `3.4e-7 Pa`, no NaN.
- CPU/GPU pressure-only `mode=1` parity over a short window:
  final `PorePress` maxAbs difference about `4.1e-3 Pa`.
- CPU/GPU self-weight short `mode=1` parity:
  final `PorePress` maxAbs difference about `2.2e-3 Pa`.
- GPU self-weight `mode=1` medium run to `0.05 s`:
  `code=0`, `excluded=0`, stable top drained and bottom no-flux corrections.

B5 long-run analytical comparison:

- GPU Release self-weight Scenario 2, `xi=0.05`, `TimeMax=3.6 s`,
  `PorePressureBoundaryOperator=1` finished with `code=0`, `excluded=0`,
  `steps=3,775,438`, runtime `9,668.14 s`.
- Final max excess pressure was `1110.26 Pa`; final bottom mean excess was
  `1110.09 Pa`.
- Compared with the existing `mode=0`, `xi=0.05` G9b run, the long-run bottom
  excess RMSE against the analytical reconstruction was effectively unchanged:
  `550.17 Pa` (`mode=0`) versus `550.18 Pa` (`mode=1`).
- The retained-profile comparison indicates that the current material-adjacent
  ghost contribution does not reduce the late-time profile RMSE; for this
  configuration it is experimental rather than a production improvement.

Recommendation:

- Keep `PorePressureBoundaryOperator=1` as an optional experimental production
  candidate, not the default.
- Do not port corrected-gradient PR operators to production based on these
  results alone.
- If strict analytical agreement remains the priority, the next boundary work
  should audit the analytical reconstruction and investigate a more complete
  boundary quadrature/MLS treatment rather than promoting the current
  material-layer ghost contribution.

## A1/A2/P1 Analytical Audit and Calibrated Reference Status, 2026-05-12

A1 audited the analytical reconstruction used for self-weight Scenario 2. The
main finding was that the Supporting-Materials-style analytical solution is a
quasi-static 1D consolidation reference, not the raw dynamic PR equation solved
inside the fully coupled SPH model.

A2 then performed a targeted initial-state audit. It showed that the actual
generated excess-pressure profile around the drainage activation time does not
exactly equal Eq.(4), but using the measured early profile did not improve the
long-run comparison. The best nominal reference remains Eq.(4) plus nominal
`cv`.

P1 generated the paper figure set:

`examples/u-pw/02_SelfWeight_Consolidation/experiments/PaperFigures_SelfWeightScenario2/`

Current Scenario 2 validation line:

- main simulation line: GPU `xi=0.05`, `PorePressureBoundaryOperator=0`;
- nominal analytical bottom excess relative RMSE: about `7.59%`;
- calibrated effective reference: `cv_eff = 1.1175 * cv`;
- calibrated bottom excess relative RMSE: about `1.98%`;
- interpretation: effective time-factor / apparent consolidation-coefficient
  sensitivity, not material retuning.

Scenario 2 is considered closed for the current paper validation workflow.

## O1/H1 Hydraulic Operator and Boundary Audit Status, 2026-05-12

O1-revised confirmed that existing mDBC/cDBC particles provide mechanical
boundary support but do not automatically carry production hydraulic state in
the PR pore-pressure operators. The current production PR loops are effectively
material-material for `LapPorePress`, `LapZ`, `PorePressureAccelDiff`, and
Shepard. Standalone 1D diagnostics indicated:

- material-only eigenmode scale `s0` about `0.912`;
- idealized boundary-particle hydraulic quadrature target `s0` about `0.995`;
- 1D MLS target `s0` about `1.000`.

H1 implemented `PorePressureBoundaryOperator=2` as a CPU-only hydraulic
mDBC-style boundary-particle prototype. It uses reconstructed boundary
hydraulic state at `pos_b + BoundNormal_b` and adds those boundary particles to
CPU `LapPorePress` / `LapZ` quadrature. H1 short tests completed with
`code=0` and `excluded=0`, and logs confirmed real bottom boundary
contributions. However:

- hydrostatic residual was slightly worse than mode `0/1`;
- pressure-only diffusion short metrics did not improve;
- self-weight short metrics did not improve;
- mode `2` does not explain the Scenario 2 time-factor mismatch.

Frozen boundary conclusions:

- `PorePressureBoundaryOperator=0` remains default production.
- `PorePressureBoundaryOperator=1` remains experimental and GPU-supported.
- `PorePressureBoundaryOperator=2` remains CPU-only experimental and GPU
  unsupported.
- There is no current evidence supporting a GPU port of mode `2`.
- Corrected-gradient PR production remains deferred.

## Next Active Phase: Scenario 1 Staged Workflow

The next active workflow is Scenario 1. Start with the
`BodyGravityStopTime` single-run route:

1. body gravity on to generate self-weight excess pressure;
2. mechanical body gravity stops at the staged time;
3. hydraulic gravity remains active;
4. top drained activates at the same staged time;
5. bottom no-flux remains active.

The first concrete phase should be a CPU/GPU short-smoke experiment to about
`0.003-0.005 s`, comparing switch-time velocity, excess-pressure, and
top/bottom boundary consistency. Do not start Scenario 1 restart workflow until
the single-run path is stable.

## Scenario 1 BodyGravityStopTime Status

The Scenario 1 `BodyGravityStopTime` single-run workflow is complete through
S1-4:

- S1-1b: GPU mechanical body gravity stop support and short CPU/GPU parity.
- S1-2: GPU medium smoke to `0.05 s` and `0.2 s`.
- S1-3: GPU long run to `3.6 s` with `code=0`, `excluded=0`.
- S1-4: paper-figure and reference-context note generated.

`HydraulicGravity` remains active after the mechanical body force stops.
`PorePressureBoundaryOperator=0` remains the production path. The restart route,
corrected-gradient production operators, and GPU `PorePressureBoundaryOperator=2`
remain deferred.

## Overall Self-Weight Validation Section Status

The self-weight validation section is drafted in
`validation_section_selfweight_consolidation_draft.md`, with supplementary
explanations in `validation_supplementary_notes.md`.

Closed validation items:

- Scenario 2 validation is closed for the current paper line:
  - GPU `xi=0.05`, `PorePressureBoundaryOperator=0` is the production
    simulation line.
  - The nominal analytical reference captures the consolidation trend.
  - The calibrated effective reference `cv_eff=1.1175 cv` reduces bottom
    excess-pressure relative RMSE from about `7.59%` to about `1.98%`.
  - This is interpreted as effective time-factor sensitivity, not material
    retuning.
- Scenario 1 validation is closed as a gravity-switch
  drainage-to-equilibrium stability figure:
  - S1-1b short CPU/GPU parity passed.
  - S1-2 GPU medium windows passed.
  - S1-3 GPU long run to `3.6 s` passed with `code=0`, `excluded=0`.
  - S1-4 paper figures and reference-context notes were generated.
- Boundary audit conclusions are frozen:
  - mode `0` remains default production;
  - mode `1` remains GPU-supported experimental;
  - mode `2` remains CPU-only experimental and GPU unsupported;
  - corrected-gradient production remains deferred.

Recommended next benchmark:

1. Cryer problem, if the priority is a pore-pressure boundary /
   poroelastic-response benchmark.
2. Undrained triaxial test, if the priority is stress path and constitutive
   response.
3. Retrogressive slope, only after benchmark coverage is sufficient, unless
   the manuscript structure needs the application case first.

## E1 Linear Elastic Skeleton Switch

E1 adds `SoilConstitutiveModel` under `<special><soils>`:

- `0`: linear elastic skeleton for strict poroelastic benchmarks;
- `1`: Drucker-Prager elastoplastic skeleton, default;
- `2`: Drucker-Prager + exponential softening, including legacy
  `Softening=1` mapping.

CPU and GPU step paths both support model `0`, and the strict Cryer draft now
uses it. This does not change PR pore-pressure operators or hydraulic boundary
modes. The next Cryer task remains C4-B spherical traction support audit before
any strict sphere run.

## Cryer C4-B Spherical Traction Audit

C4-B is complete as a documentation/source audit. No strict Cryer simulation
was run and no source was modified.

Result:

- no existing native XML route was found for uniform all-around spherical
  traction `p0`;
- `AccInput` is not strict because it applies marker-wise acceleration rather
  than `F_i=-p0 A_i n_i`;
- floating-body force routes are total rigid-body force inputs, not deformable
  poroelastic surface traction;
- prescribed motion is a displacement-control surrogate, not traction control.

## Cryer C4-B2 Flexible Confining Stress Route

C4-B2 supersedes the earlier radial-area traction source idea. The `AccInput`
patchwise surrogate is rejected for strict Cryer because it remains a marker
acceleration/body-force equivalent, not a continuous pressure traction.

The selected strict loading route is flexible confining stress:

- add an isotropic compressive stress `sigma_conf = -p0 I` to the mechanical
  momentum summation;
- rely on SPH kernel symmetry for interior cancellation;
- rely on free-surface truncation for the effective exterior confining pressure;
- keep the term independent of `AccInput`, body gravity, `HydraulicGravity`, and
  the PR pore-pressure equation.

Recommended next strict path:

1. C4-B3 CPU-only flexible confining stress implementation with no-load,
   sign, symmetry, and surface-localization diagnostics;
2. drained curved hydraulic boundary audit/development as a separate blocker;
3. coarse CPU strict sphere smoke only after loading diagnostics pass;
4. GPU support only after CPU strict behavior is credible.

Strict Cryer simulation remains paused. Corrected-gradient production remains
deferred.

## Cryer C4-B3 CPU Flexible Confining Stress

C4-B3 is complete as a CPU-only minimal implementation and smoke. The new
`FlexibleConfiningStress` XML switch defaults to off and adds an isotropic
stress-like contribution only to the CPU mechanical momentum pair summation.
It is independent of `AccInput`, body gravity, `HydraulicGravity`, and the PR
pore-pressure equation. It is not written into the material stress state.

The retained CPU smokes are under:

`examples/u-pw/03_Cryer_Problem/strict_reproduction_plan/flexible_confining_stress_C4B3/`

Results:

- no-load, sign, and ramp smokes: `code=0`, `excluded=0`;
- positive `ConfiningStressP0` produced inward surface radial velocity;
- net-force/center-of-mass diagnostics remained near zero for the symmetric
  tiny specimen;
- GPU support is deliberately unsupported and hard-errors if the switch is
  enabled.

Next recommended Cryer step: C4-B4 traction-only free-sphere smoke on CPU,
followed by C4-C drained curved pore-pressure boundary work. Strict Cryer
simulation remains paused; no GPU port should start before CPU loading and
boundary behavior are credible.

## Cryer C4-B4 Free-Sphere Flexible Confining Stress

C4-B4 is complete as a CPU-only traction-source smoke. It did not modify
source, did not run GPU, and did not start strict Cryer.

The retained smoke package is under:

`examples/u-pw/03_Cryer_Problem/strict_reproduction_plan/flexible_confining_stress_C4B4_FreeSphere/`

Results:

- no-load free-sphere regression: `code=0`, `excluded=0`;
- ramped free-sphere `FlexibleConfiningStress` with `p0=50 Pa`: `code=0`,
  `excluded=0`;
- target particles: `739`;
- final max confining acceleration: `1.95492 m/s2`;
- final surface radial velocity mean: `-6.28e-04 m/s`;
- final surface radial displacement mean: `-1.09e-06 m`;
- final net/absolute force: `1.94e-08`;
- final COM acceleration estimate: `2.08e-08 m/s2`;
- `Kplastic=0` with `SoilConstitutiveModel=0`.

`FlexibleConfiningStress` is now the current CPU traction candidate for strict
Cryer. It is not a complete Cryer validation. GPU support remains unsupported,
and the drained curved pore-pressure boundary remains the next blocker.

Next recommended Cryer step: C4-C drained curved pore-pressure boundary
audit/development. Strict Cryer simulation remains paused.

## Cryer C4-C CPU Drained Curved Boundary

C4-C is complete as a CPU-only operator-level prototype and short smoke. The
new `PorePressureBoundaryOperator=3` path is enabled with
`PorePressureCurvedDrained=1`. It selects material particles near a prescribed
spherical exterior and adds a drained Dirichlet ghost state to CPU
`LapPorePress` and `LapZ` before `PorePressRate` is computed. It is not a
post-update clamp, and modes `0`, `1`, and `2` remain unchanged.

GPU support is intentionally unsupported. GPU execution with mode `3` or
`PorePressureCurvedDrained=1` hard-errors during XML loading.

The retained smoke package is under:

`examples/u-pw/03_Cryer_Problem/strict_reproduction_plan/drained_curved_boundary_C4C/`

Results:

- zero/no-source stability smoke: `code=0`, `excluded=0`;
- pressure-only uniform-excess diffusion smoke: `code=0`, `excluded=0`;
- flexible confining stress plus drained curved boundary smoke:
  `code=0`, `excluded=0`;
- diffusion surface excess decreased from `1000 Pa` to about `963 Pa` over
  the short run;
- compression produced early positive center excess and kept `Kplastic=0`.

Remaining strict-Cryer blockers:

- no-elevation hydraulic representation: the current PR path still requires
  positive `HydraulicGravity` for hydraulic scaling;
- mode `3` is a first-order spherical ghost prototype, not MLS or general
  boundary quadrature;
- no strict analytical center-pressure comparison has been run;
- no GPU port should start until CPU strict behavior is credible.

Next recommended Cryer step: C5 coarse CPU strict-sphere smoke only if the
no-elevation-source limitation is explicitly accepted or resolved. Strict
Figure 7 reproduction remains unclaimed.

## Cryer C4-D Hydraulic No-Elevation Mode

C4-D is complete as a CPU-only hydraulic representation needed before a coarse
strict-Cryer smoke. The new `HydraulicElevationSource` parameter keeps legacy
behavior by default:

- `HydraulicElevationSource=1`: old self-weight/Terzaghi behavior,
  `PorePressRate = Kw/n*(-DivVel + k/(rho_w*g_h)*LapPorePress + k*LapZ)`;
- `HydraulicElevationSource=0`: gravity-free Cryer behavior,
  `PorePressRate = Kw/n*(-DivVel + k/(rho_w*g_h)*LapPorePress)`, with zero
  hydrostatic reference and `ExcessPorePress == PorePress`.

The C4-D CPU smokes under
`examples/u-pw/03_Cryer_Problem/strict_reproduction_plan/hydraulic_no_elevation_C4D/`
passed with `code=0`, `excluded=0`. GPU support is intentionally deferred; GPU
execution hard-errors if `HydraulicElevationSource=0` is requested.

Next recommended task: C5 coarse CPU strict-sphere smoke. Do not start GPU or
strict Figure 7 comparison until the combined CPU route is stable.

## Cryer C5 Coarse CPU Strict-Sphere Smoke

C5 is complete as a CPU-only short smoke, not a final validation. The retained
package is:

`examples/u-pw/03_Cryer_Problem/strict_reproduction_plan/C5_StrictSphere_CoarseSmoke/`

The smoke combines linear elasticity, CPU flexible confining stress, CPU curved
drained pore-pressure boundary, and no-elevation hydraulics. It completed with
`code=0`, `excluded=0`, and `Kplastic=0`; center pore pressure rose under
compression and `LapZ` was excluded from the used pressure-rate terms.

Because longer exploratory windows entered coarse free-sphere oscillation and
particle out-check risk, C5 should not go directly to quantitative Figure 7B
comparison. Next recommended step: C5b geometry/time-window refinement. GPU
remains deferred for `FlexibleConfiningStress`, mode `3`, and
`HydraulicElevationSource=0`.

## Cryer C5b Strict-Sphere Refinement

C5b is complete as a targeted CPU-only refinement. No source code was changed
and no GPU run was performed.

Retained package:

`examples/u-pw/03_Cryer_Problem/strict_reproduction_plan/C5b_StrictSphere_Refinement/`

Outcome:

- baseline, slow-ramp, and lower-p0 variants completed with `code=0`,
  `excluded=0`, and `Kplastic=0`;
- the longer slow-ramp variant is not accepted because it reached
  `excluded=425` after particle out-check warnings beginning near
  `t=0.025 s`;
- lower `p0` scales almost exactly with the baseline, so the current high
  normalized peak is not a load-magnitude nonlinearity;
- slower ramp delays the pressure peak but does not remove the high normalized
  response;
- center averaging has a moderate effect, while near-surface material excess
  remains large despite zero curved-ghost residual.

Decision: C6 quantitative Figure 7 comparison is not ready. The recommended
next task is drained curved boundary/material-surface refinement, followed by a
cleaner geometry/time-window retry. GPU remains deferred.

## Cryer C5c Curved Boundary Coupling

C5c is complete as a CPU-only refinement under:

`examples/u-pw/03_Cryer_Problem/strict_reproduction_plan/C5c_CurvedBoundaryCoupling/`

It adds sub-modes for `CurvedDrainedBoundaryMode` while keeping
`PorePressureBoundaryOperator=3` experimental:

- `0`: previous first-order drained ghost;
- `1`: strengthened image-style drained ghost;
- `2`: diagnostic surface material clamp, not production.

All C5c CPU Release runs completed with `code=0`, `excluded=0`, and
`Kplastic=0`. The near-surface residual is systematic rather than an outlier:
old mode `3` has mean `179.37 Pa`, p95 `218.47 Pa`, and max `263.15 Pa` in
the `r>0.85R` material shell at the final frame.

The strengthened ghost gives only minor compression improvement, while the
diagnostic clamp confirms that stronger material-surface drainage can strongly
reduce the center response but is not a production boundary. C6 remains
premature. Recommended next step: principled mode-3 boundary quadrature /
multi-sample Dirichlet refinement, then modest dp/geometry refinement.

GPU remains deferred for Cryer strict modes (`FlexibleConfiningStress`, mode
`3`, and `HydraulicElevationSource=0`).

## Cryer C5d Curved Boundary Quadrature

C5d is complete as a CPU-only refinement under:

`examples/u-pw/03_Cryer_Problem/strict_reproduction_plan/C5d_BoundaryQuadrature/`

It adds `CurvedDrainedBoundaryMode=3` as a multi-sample spherical Dirichlet
boundary quadrature for `PorePressureBoundaryOperator=3`. The mode contributes
to the CPU `LapPorePress`/`LapZ` operator and does not clamp material pressure.

All C5d CPU Release cases completed with `code=0`, `excluded=0`, and
`Kplastic=0`, but the improvement is marginal: compression surface p95 excess
decreases from `218.47 Pa` to `208.90 Pa`, and the center peak decreases from
`7.672 p0` to `7.657 p0`. Pressure-only diffusion does not yet show a clean
operator-quality improvement over the strengthened ghost.

Decision: C6 quantitative Cryer comparison is not ready. GPU remains deferred
for `FlexibleConfiningStress`, `PorePressureBoundaryOperator=3`, and
`HydraulicElevationSource=0`.

## Cryer LIT-B Boundary Literature Audit

LIT-B is complete as a documentation-only pause after C5d. It did not change
source or run simulations.

The literature audit indicates that the original u-pw boundary treatment is
closer to boundary-particle hydraulic state plus MLS/free-surface pressure
treatment than to the current material-side spherical ghost/quadrature mode.
The drained/undrained SPH paper also supports boundary-particle pressure
extrapolation through normalized kernels, but it is not itself a transient PR
diffusion boundary formulation.

GPU work remains paused. The next CPU task should design a paper-faithful
boundary-particle hydraulic state / MLS or Adami extrapolation route for the
spherical drained Cryer boundary. GPU should not be revisited until that CPU
route produces credible pressure-only diffusion and coarse Cryer behavior.

## Cryer C5e Boundary-Particle Drained Boundary

C5e is complete as a CPU-only source and smoke refinement under:

`examples/u-pw/03_Cryer_Problem/strict_reproduction_plan/C5e_BoundaryParticleDrained/`

It adds `CurvedDrainedBoundaryMode=4` for the existing experimental
`PorePressureBoundaryOperator=3` curved-drained path. Selected boundary
particles carry prescribed drained `p_w=0` and contribute to CPU
`LapPorePress`/`LapZ`. The mode does not clamp material pressure and does not
change the PR governing equation. GPU remains unsupported for this Cryer
strict-boundary path.

All C5e CPU Release cases completed with `code=0`, `excluded=0`, and
`Kplastic=0`. Mode 4 reduced the compression center peak from `7.657 p0` to
`6.908 p0`, but pressure-only diffusion over-drained and introduced large
pressure-rate artifacts (`PorePressRate` maxAbs about `9.38e5 Pa/s`).

GPU porting is not recommended. The CPU boundary still needs
MLS/Adami-normalized boundary-particle weighting before C6 or GPU work.

## Cryer C5f-C5g Boundary Weighting and Geometry Diagnostics

C5f is complete as a CPU-only boundary-particle weighting refinement under:

`examples/u-pw/03_Cryer_Problem/strict_reproduction_plan/C5f_BoundaryParticleWeighting/`

It adds `CurvedDrainedBoundaryWeighting` for `CurvedDrainedBoundaryMode=4`.
The normalized mode reduces raw mode-4 over-drainage and pressure-rate
artifacts, and improves the compression surface residual, but the center peak
remains high at about `7.45 p0`.

C5g is complete as a no-source-change CPU geometry diagnostic under:

`examples/u-pw/03_Cryer_Problem/strict_reproduction_plan/C5g_GeometryDpDiagnostic/`

It compares the C5f normalized coarse sphere (`dp=0.010`) with one modestly
finer sphere (`dp=0.008`). All C5g CPU Release cases completed with `code=0`,
`excluded=0`, and `Kplastic=0`. The finer sphere reduced center averaging
noise and lowered the center peak from `7.448 p0` to `7.058 p0`, but did not
materially improve the compression surface p95 residual.

Decision: geometry quality contributes to the error budget, but it is not the
main strict-Cryer blocker. C6 remains premature. The next CPU work should focus
on MLS / flux-consistent drained spherical boundary coupling before broader
resolution studies or GPU porting.

## Cryer C5h Higher-Resolution Sphere Diagnostic

C5h is complete as a no-source-change CPU diagnostic under:

`examples/u-pw/03_Cryer_Problem/strict_reproduction_plan/C5h_HigherResolutionSphere/`

It adds one higher-resolution sphere (`dp=0.0065`, `2601` material particles)
to the C5g coarse/finer comparison. Both C5h CPU Release cases completed with
`code=0`, `excluded=0`, and `Kplastic=0`.

The center peak continues to decrease (`7.448 p0 -> 7.058 p0 -> 6.731 p0`),
but the higher-resolution surface and pressure-only diffusion behavior worsen:
compression surface p95 rises to `244.34 Pa`, pressure-only final center
pressure rises to `746.40 Pa`, and pressure-only surface p95 rises to
`1023.40 Pa`.

Decision: sphere resolution is a contributor but not the main blocker. Simple
dp refinement should pause. The next Cryer work should return to MLS /
flux-consistent drained spherical boundary calibration before C6 or any GPU
porting.

## Cryer C5i Spherical Diffusion Flux Calibration

C5i is complete as a postprocessing-only radial diffusion gate under:

`examples/u-pw/03_Cryer_Problem/strict_reproduction_plan/C5i_SphericalDiffusionFluxCalibration/`

It did not modify source, did not run GPU, and did not run new compression
cases. The 1D FV reference shows that the current normalized mode-4 boundary is
not a true drained Dirichlet boundary: apparent storage flux is often too
strong, but the near-surface pressure shell remains too high. The normalized
mode-4 median apparent SPH/FV flux ratios are about `1.63`, `2.26`, and `2.18`
for `dp=0.010`, `0.008`, and `0.0065`; the highest-resolution case also shows
a late flux reversal.

Decision: C6 remains blocked, simple dp refinement should stay paused, and GPU
porting remains deferred. The next CPU task should be a narrow MLS /
flux-consistent spherical drained boundary prototype with pressure-only radial
diffusion as the first acceptance gate.

## Cryer C5j MLS Boundary Flux Prototype

C5j adds `CurvedDrainedBoundaryMode=5` as a CPU-only experimental subroute of
`PorePressureBoundaryOperator=3`. The mode uses a constrained radial MLS
gradient against the prescribed spherical drained value and applies a
shell-average integrated `LapPorePress` flux correction. It does not clamp
material pressure and does not count dummy boundary-particle volumes.

The C5j pressure-only CPU Release gate ran for `dp=0.008` and `dp=0.010`.
Both cases completed with `code=0`, `excluded=0`, and `Kplastic=0`, with zero
MLS fallback. However, the gate did not pass: surface shell pressure remains
far above the FV radial reference and final SPH/FV flux ratio remains about
`4`. No Cryer compression smoke was run.

GPU porting remains deferred. Mode `5` is still protected by the existing GPU
hard error for `PorePressureBoundaryOperator=3` /
`PorePressureCurvedDrained=1`. The next CPU task should address radial
shell/FV flux matching before any GPU implementation is considered.

## Cryer C5k Radial-Shell Flux Boundary Prototype

C5k adds `CurvedDrainedBoundaryMode=6` as another CPU-only experimental
subroute of `PorePressureBoundaryOperator=3`. Mode `6` estimates a drained
spherical FV flux from radial shell averages and applies it as a shell
`LapPorePress` correction. It does not clamp material pore pressure and does
not change the PR governing equation.

The C5k pressure-only CPU Release gate ran for `dp=0.008` and `dp=0.010`.
Both cases completed with `code=0`, `excluded=0`, and `Kplastic=0`. The gate
still failed: `dp=0.010` improves median flux ratio but leaves the surface
shell far too pressurized, while `dp=0.008` shows late apparent flux reversal
and a large pressure-rate artifact. No Cryer compression smoke was run.

GPU porting remains deferred. Mode `6` is covered by the same GPU hard error
as the other curved drained experimental modes. The next CPU task should solve
near-boundary radial redistribution/interior Laplacian consistency before any
GPU implementation is useful.

## Cryer C5l Radial Operator Audit

C5l is complete as a no-source-change postprocessing audit. It does not add GPU
coverage and does not run GPU. The audit shows that the material-only
`LapPorePress` operator preserves constant fields and is acceptable in the
interior for `u=r^2`, but its curved near-boundary behavior is not consistent
enough for strict Cryer radial diffusion. The `dp=0.0065` boundary cloud is
rougher and has many more material-boundary pairs, so resolution alone is not a
GPU-ready path.

GPU porting remains deferred. The next CPU task should be a conservative
multi-shell radial exchange prototype; GPU work should resume only after that
pressure-only FV radial diffusion gate passes.

## Cryer C5m Conservative Shell Exchange Prototype

C5m adds `CurvedDrainedBoundaryMode=7` as a CPU-only experimental subroute of
`PorePressureBoundaryOperator=3`. Mode `7` enforces radial shell storage
balance through FV interface fluxes and a shell-average `LapPorePress`
correction. It does not clamp material pore pressure, does not count dummy
boundary volumes, and does not change the PR pressure update form.

The C5m pressure-only CPU Release gate ran for `dp=0.008` and `dp=0.010`.
Both cases completed with `code=0`, `excluded=0`, and `Kplastic=0`, and the
source shell storage residual is essentially machine zero. The pressure-only
gate still failed: `dp=0.008` has late apparent flux reversal and a large
pressure-rate artifact, while `dp=0.010` improves the surface shell but worsens
center/volume decay.

GPU porting remains deferred. Mode `7` is covered by the same curved drained
GPU hard error as modes `3` to `6`; porting it before the pressure-only FV
radial diffusion gate passes would only duplicate a failing diagnostic route.

## Cryer C5n Corrected Laplacian Prototype

C5n adds `CurvedDrainedBoundaryMode=8` as a CPU-only experimental subroute of
`PorePressureBoundaryOperator=3`. Mode `8` is a boundary-aware corrected
quadratic MLS Laplacian near the drained sphere. It replaces near-boundary
`LapPorePress`, keeps the prescribed drained value `p_b=0` in the pressure-only
Cryer gate, does not clamp material pore pressure, and does not count dummy
boundary volumes.

The static manufactured audit improved the near-boundary operator strongly:
for `dp=0.008`, `u=r^2` p95 error dropped from about `13.81` to roundoff when
the manufactured boundary value was consistent, and the drained-like `R-r`
field p95 error dropped from about `121.32` to `5.23`. The dynamic
pressure-only gate still failed: the `dp=0.008` CPU Release case completed
with `code=0`, `excluded=0`, and `Kplastic=0`, but it produced negative
pressure, flux reversal, and a final `PorePressRate` maxAbs of `9.37e6 Pa/s`.
No Cryer compression smoke was run.

GPU porting remains deferred. Mode `8` is protected by the same
`PorePressureBoundaryOperator=3` GPU hard error. A GPU port should not start
until a CPU corrected-boundary route passes the pressure-only FV radial
diffusion gate without flux reversal or over-drain.

## Cryer C5o Corrected Laplacian Stabilization

C5o adds mode-8-only limiter controls for the CPU corrected Laplacian path:
positivity limiting, fixed MLS/material Laplacian blending, and optional
positivity after blending. Defaults preserve the C5n behavior. No GPU support
was added.

The C5o pressure-only CPU Release gate ran four `dp=0.008` limiter cases. All
completed with `code=0`, `excluded=0`, and `Kplastic=0`, but none passed the FV
radial diffusion gate. Blend `0.25` improved the center RMSE and reduced the
final pressure-rate artifact, but the surface shell stayed far above the FV
reference and apparent flux reversal remained.

GPU porting remains deferred. Porting the curved drained mode-8 limiter path
would only duplicate a failing CPU diagnostic. C6 also remains blocked.

## Cryer C5p Strict Route Freeze

C5p freezes the strict Cryer route as a documentation-only no-go decision. No
source, CPU, GPU, GenCase, or PartVTK work was performed.

The CPU strict route now has useful infrastructure, including the linear
elastic skeleton switch, CPU flexible confining stress, no-elevation hydraulic
mode, Cryer analytical reference, FV spherical diffusion reference, and
mode-by-mode drained-boundary diagnostics. However, the required pressure-only
spherical FV diffusion gate failed after boundary-particle, MLS flux,
radial-shell flux, conservative shell exchange, corrected Laplacian, and
limiter attempts.

GPU porting for strict Cryer remains deferred. Porting these curved drained
boundary modes now would only reproduce a CPU path that is not validation-ready.
C6 Figure 7B comparison is not started.

Next benchmark recommendation:

1. Start an undrained triaxial baseline if the goal is constitutive and stress
   path validation.
2. Use external-load 1D full reproduction if the goal is consolidation
   parameter validation.
3. Defer retrogressive slope strict work until mechanical and constitutive
   baselines are stronger.

## Cryer C5q Interface Cleanup Audit

C5q audited the parameter/interface surface left by the strict Cryer route. It
does not add GPU work and does not run GPU.

GPU-relevant decision:

- `SoilConstitutiveModel` remains CPU/GPU-supported infrastructure.
- `PorePressureBoundaryOperator=1` remains experimental and GPU-supported.
- `PorePressureBoundaryOperator=2`, `PorePressureBoundaryOperator=3`,
  `PorePressureCurvedDrained=1`, `HydraulicElevationSource=0`, and
  `FlexibleConfiningStress=1` remain CPU-only or GPU hard-error paths.
- `CurvedDrainedBoundaryMode=5/6/7/8` and their limiter/shell/MLS parameters
  are deprecated archived Cryer experiments, not GPU port targets.

No source cleanup is recommended before T1. GPU work should not port the failed
strict Cryer boundary modes unless a new CPU drained-boundary formulation first
passes the pressure-only spherical FV diffusion gate.

## T1 Undrained Triaxial Baseline

T1 is complete as a CPU Release reduced smoke under:

`examples/u-pw/04_Undrained_Triaxial/experiments/T1_UndrainedTriaxialBaseline/`

The case uses `SoilConstitutiveModel=0`, native AccInput axial loading on the
top material layer, `PorePressureBoundaryOperator=0`, and
`HydraulicElevationSource=0`. It is not a full paper reproduction and does not
use Cryer curved drained boundary modes.

CPU result:

- GenCase `code=0`;
- DualSPHysics CPU Release `code=0`;
- PartVTK `code=0`;
- `excluded=0`;
- final upper-middle mean excess pore pressure `42.12 Pa`;
- final `Kplastic` max `0`;
- no NaN/Inf in the postprocessed fields.

GPU was not run because `HydraulicElevationSource=0` is CPU-only in the current
branch. T2 should refine stress-path postprocessing, DP baseline behavior, and
loading/confinement before any GPU parity or paper comparison.

## T2 Zhao Flexible Confinement Audit

T2 adds no source and no GPU work. It converts and reviews Zhao et al.'s
flexible confined boundary method and audits the current CPU
`FlexibleConfiningStress` path.

GPU-relevant decision:

- `FlexibleConfiningStress=1` remains CPU-only and GPU hard-errors.
- This is still the correct behavior because strict triaxial lateral
  confinement first needs CPU diagnostics:
  - kernel-completeness index `f_i`;
  - near-boundary selection;
  - lateral-cylinder selection;
  - top/bottom cap exclusion;
  - confinement-only smoke.
- MCC remains deferred until mechanical confinement and measurement regions are
  stable.

T3 should be CPU-only. GPU parity should wait until the Zhao-style confinement
selector has passed a confinement-only smoke and an axial-compression smoke.

## T3 Flexible Confinement Diagnostics

T3 adds CPU source diagnostics and opt-in selectors for the existing
`FlexibleConfiningStress` path. It does not add GPU support.

Implemented CPU-only controls:

- `FlexibleConfiningStressFiDiagnostic`;
- `SaveConfiningStressDiagnostics`;
- `ConfiningStressFiThreshold`;
- `ConfiningStressGeometry=1` with cylinder center/axis/radius/height;
- `ConfiningStressUseFiSelector`;
- `ConfiningStressUseLateralSelector`.

CPU Release smokes under
`examples/u-pw/04_Undrained_Triaxial/experiments/T3_FlexibleConfinementDiagnostics/`
completed with `code=0`, `excluded=0`, and `Kplastic=0`:

- confinement-only legacy;
- confinement-only selected;
- axial AccInput plus selected flexible confinement.

The selected route reduces the active target set from `407` to `112` particles
and removes active cap axial leakage in the confinement diagnostics
(`~0.93 m/s2` to `0`). GPU remains deferred because the CPU path still uses the
raw kernel gradient and needs T4 measurement/stress-path refinement before any
porting or parity work.

## T4 Triaxial Stress-Path Postprocessing

T4 adds no source and no GPU work. It refines the CPU selected-confinement
triaxial postprocessing under:

`examples/u-pw/04_Undrained_Triaxial/experiments/T4_StressPathPostprocessing/`

The retained CPU Release smoke uses `SoilConstitutiveModel=0`,
`HydraulicElevationSource=0`, `PorePressureBoundaryOperator=0`, and the T3
`f_i` + lateral flexible-confinement selectors. It completes with `code=0`,
`excluded=0`, and `Kplastic=0` over a deliberately short `TimeMax=0.0015 s`
window.

T4 confirms that confinement targeting remains healthy: active cap leakage is
zero, lateral inward acceleration is coherent, and the net-force symmetry
residual stays small. However, the pore-pressure and stress-path curves are
still diagnostic/proxy only. The late short-window pore-pressure response shows
large pressure-rate excursions and sign reversal, and the output fields do not
yet provide strict total/effective stress labeling, original position, material
`mk`, or per-particle confinement class.

GPU remains deferred. The next CPU-first task should be T4b Zhao-style
renormalized-gradient confinement and loading/stability refinement before any
T5 DP baseline, GPU parity run, or T6 MCC implementation.

## T4b Zhao Renormalized Confinement

T4b adds CPU-only `ConfiningStressGradientMode` for the flexible confinement
term:

- `0`: raw kernel gradient, default and legacy behavior;
- `1`: local first-order renormalized/corrected gradient for
  `FlexibleConfiningStress` only.

CPU Release and GPU Release builds passed. No GPU simulation was run.
`ConfiningStressGradientMode=1` and `FlexibleConfiningStress=1` remain
GPU-unsupported and hard-error on GPU.

Two CPU Release smokes under
`examples/u-pw/04_Undrained_Triaxial/experiments/T4b_RenormalizedConfinement/`
completed with `code=0`, `excluded=0`, and `Kplastic=0`. The gradient
diagnostic corrected all selected lateral targets with zero fallbacks. The
selector still eliminates cap leakage.

The renormalized gradient is not yet a validation path. It roughly doubles the
lateral confinement acceleration in the reduced cylinder and worsens the
short-window pressure-rate/pressure-reversal artifact. Gentler axial loading
helps only marginally. GPU work remains deferred; the next CPU task should
stabilize the selected-confinement loading response before T5 DP, T6 MCC, or
GPU parity.

## T4c Triaxial Loading Stabilization

T4c adds no GPU work and no source change. It tests staged selected
confinement and gentler axial loading under:

`examples/u-pw/04_Undrained_Triaxial/experiments/T4c_LoadingStabilization/`

All retained CPU Release smokes complete with `code=0`, `excluded=0`, and
`Kplastic=0`, with cap leakage still zero. The retained short gate uses
`ConfiningStressRampEnd=0.001`, axial loading start at `0.0015 s`, and
`TimeMax=0.0018 s`.

T4c shows that pressure reversal begins around `0.0014 s`, before delayed
axial loading starts. The current blocker is therefore selected-confinement
equilibration/u-pw feedback stability, not the first axial AccInput impulse.

## T4d Triaxial Confinement Equilibration

T4d adds no source and no GPU work. It isolates the selected flexible
confinement stage under:

`examples/u-pw/04_Undrained_Triaxial/experiments/T4d_ConfinementEquilibration/`

All retained CPU Release cases complete with `code=0`, `excluded=0`, and
`Kplastic=0`. The target-p0 confinement-only feedback-on case still reverses at
about `0.001404 s`, with max `PorePressRate=3.12e12 Pa/s` and `85` DtMin
adjustments. Disabling `PorePressureFeedback` for the same selected
confinement removes reversal over the retained window, removes DtMin
adjustments, and reduces max `PorePressRate` to `2.11e7 Pa/s`.

Lower p0 and longer ramp/damping reduce or delay the artifact but do not
stabilize the feedback-on route. Cap leakage remains zero, so the active
blocker is the selected-confinement/u-pw feedback equilibration loop rather
than the lateral selector. GPU remains deferred, and T5 DP / T6 MCC should not
start until a stable feedback-on confinement equilibration stage exists.

Renormalized confinement remains an amplifier rather than a cure. GPU remains
deferred; do not proceed to GPU parity, T5 DP, or T6 MCC until the CPU
linear-elastic selected-confinement response is stable.

## T4e Feedback-Gated Triaxial Confinement

T4e adds CPU-only pore-pressure feedback timing controls for selected
confinement diagnostics:

- `PorePressureFeedbackStartTime`;
- `PorePressureFeedbackRampEndTime`;
- `PorePressureFeedbackScale`.

The defaults preserve the previous behavior. GPU Release builds passed after
the parser/source change, but non-default feedback gating remains unsupported
on GPU and hard-errors. No GPU simulation was run.

CPU Release cases under
`examples/u-pw/04_Undrained_Triaxial/experiments/T4e_FeedbackGatedConfinement/`
show that feedback-off confinement-only equilibration remains stable to
`0.005 s` with no reversal, no exclusions, and no DtMin adjustments. However,
restoring full feedback after equilibration is still unstable: abrupt,
short-ramp, and long-ramp full feedback all trigger reversal, DtMin bursts,
and particle exclusion. A diagnostic long-ramp case with
`PorePressureFeedbackScale=0.25` avoids exclusions in the short run but still
reverses at the final frame.

GPU remains deferred. T5 DP and T6 MCC remain deferred until the CPU
linear-elastic selected-confinement feedback loop is stable with full feedback
enabled.

## T4f Feedback Stabilization GPU Status

T4f adds CPU-only pore-pressure feedback diagnostics and acceleration
stabilization:

- `SavePorePressureFeedbackDiagnostics`;
- `PorePressureFeedbackRelaxation`;
- `PorePressureFeedbackLimiterMode`;
- `PorePressureFeedbackMaxAccel`;
- `PorePressureFeedbackMaxAccelRatio`.

CPU Release and GPU Release builds pass. GPU simulation was not run. The GPU
feedback path still supports only default feedback timing/stabilization and
`PorePressureFeedbackOperator=1`; any non-default T4e/T4f feedback timing or
stabilization parameter hard-errors on GPU.

T4f does not unlock GPU validation. The best CPU confinement-only diagnostic
case removes exclusions and DtMin bursts with full feedback scale `1`, but it
still has local negative pressure and order `1e9 Pa/s` pressure-rate artifacts,
and the gentle axial smoke reintroduces center-core reversal. GPU parity,
T5 DP, and T6 MCC remain deferred until the CPU feedback formulation is
stable without relying on a purely diagnostic limiter.

## T4g Feedback Formulation Audit GPU Status

T4g adds CPU-only feedback formulation diagnostics and opt-in class filtering:

- `PorePressureFeedbackUseClassFilter`;
- `PorePressureFeedbackExcludeCaps`;
- `PorePressureFeedbackExcludeEdges`;
- `PorePressureFeedbackExcludeConfinementTargets`;
- `PorePressureFeedbackInteriorOnly`.

The defaults preserve existing behavior. GPU Release builds pass, but
non-default feedback timing, stabilization, diagnostics, or class filtering
remain GPU-unsupported and hard-error. No GPU simulation was run.

The CPU audit finds operator `1` to be the physically preferred feedback
candidate: it is constant-pressure consistent and gives the expected
down-gradient response for a linear pressure field. Operator `0` produces a
nonzero uniform-pressure surface response and is not recommended for the
triaxial internal feedback route.

Class filtering is useful but does not complete the CPU gate. It removes the
operator-`1` unfiltered exclusion and DtMin burst
(`excluded=164`, `256` DtMin adjustments) and reduces max `PorePressRate` from
about `1.30e13` to `4.79e10 Pa/s`, but pressure reversal and negative pressure
remain in confinement-only full-feedback tests. GPU parity, T5 DP, and T6 MCC
remain deferred. The next CPU task should be a narrow feedback formulation
patch based on class-filtered operator `1`, not a GPU port or constitutive
model extension.

## T4h Corrected Feedback Gradient GPU Status

T4h adds `PorePressureFeedbackOperator=2`, a CPU-only experimental LSQ
pressure-gradient feedback operator. It solves a local weighted least-squares
gradient and applies `a_fb=-grad(p_w)/rho` through the existing feedback
acceleration path. New LSQ controls are:

- `PorePressureFeedbackLSQRadiusFactor`;
- `PorePressureFeedbackLSQConditionLimit`;
- `PorePressureFeedbackLSQFallback`.

The parser accepts these keys on both builds, but GPU execution hard-errors
when `PorePressureFeedbackOperator=2` is requested. This is intentional. T4h
shows that LSQ improves manufactured linear-gradient consistency, but it does
not pass the selected-confinement dynamic gate. Operator `2` remains a CPU
diagnostic path, not a GPU validation target.

GPU triaxial validation remains deferred. The default GPU route must continue
to avoid non-default feedback gating, class filtering, stabilization, and LSQ
feedback until the CPU feedback formulation is validation-ready.

## T4i-B Feedback Fidelity Audit GPU Status

T4i-B is documentation-only. It does not add source code or run simulations.
The audit concludes that the original u-pw notes are closer to a symmetric
stress-like pore-pressure pair term than to the current operator `1/2`
pressure-gradient feedback routes.

GPU remains deferred for two reasons:

1. current non-default feedback timing, stabilization, class filtering, and LSQ
   operator paths are CPU-only diagnostics;
2. the recommended T4j route is a new CPU-first paper-style feedback coupling
   prototype that must pass controlled gates before any GPU port is meaningful.

No GPU triaxial parity, DP, or MCC work should start until the CPU
paper-fidelity route is stable without relying on limiter caps.

## T4j Paper-Style Feedback GPU Status

T4j adds `PorePressureFeedbackOperator=3`, a CPU-only experimental
paper-style pressure stress-pair feedback operator. GPU execution hard-errors
when operator `3` is requested, matching the existing CPU-only status of
operator `2` and other non-default triaxial feedback diagnostics.

The CPU gate did not pass. Operator `3` is closer to the u-pw notes in pair
form, but the raw material-only stress-pair route produces the expected
free-surface uniform-pressure response and is dynamically worse than the
operator-`1` interior baseline in selected confinement. No GPU port should be
started. The next CPU work should focus on T4k initial hydrostatic confinement
and pressure-boundary/stress consistency before returning to GPU parity, DP, or
MCC.

## T4k Initial Hydrostatic Confinement GPU Status

T4k adds `InitialStressMode=1`, a CPU-only initial skeleton/effective stress
initialization for triaxial confinement staging. The parser is shared, so CPU
Release, CPU Debug, and GPU Release builds were checked, but GPU execution
hard-errors when non-default initial stress is requested.

The CPU gate did not unlock triaxial validation. Initial stress is written
correctly to `Sigmac`, but the reduced free-surface cylinder still lacks a
balanced cap/axial hydrostatic confinement route. Delayed full feedback again
produces a large `PorePressRate` excursion in confinement-only tests. No axial
smoke, GPU run, DP baseline, or MCC work should start from T4k.

## T4l Full Hydrostatic Confinement GPU Status

T4l adds `CapConfiningStress`, a CPU-only cap-normal hydrostatic support route
for reduced triaxial staging. The parser is shared, so CPU Release, CPU Debug,
and GPU Release builds were checked, but GPU execution hard-errors when
`CapConfiningStress=1`.

The CPU results confirm that cap support is useful but not sufficient. With
feedback off, full cap+lateral support greatly improves the center-core pore
pressure compared with the T4k lateral-only mismatch. With delayed full
feedback, however, the confinement-only state still develops order
`1e12 Pa/s` `PorePressRate` and large negative pressure. No axial smoke or GPU
simulation was run. GPU parity, T5 DP, and T6 MCC remain deferred until a CPU
full-feedback hydrostatic equilibrium gate passes.

## T4m All-Surface Confinement GPU Status

T4m is XML/workflow-only and adds no new GPU code. It uses existing CPU-only
features: `FlexibleConfiningStress`, `InitialStressMode=1`, and non-default
feedback timing/classification diagnostics. GPU simulation was not run.

The CPU result improves the feedback-off hydrostatic state when
`ConfiningStressUseFiSelector=1` and `ConfiningStressUseLateralSelector=0`,
reducing final `q` from about `53.5 Pa` to `15.6 Pa`. Delayed full feedback
still fails with order `1e12 Pa/s` `PorePressRate`. GPU parity, DP, and MCC
remain deferred until the CPU all-surface or staged-equilibrium route passes a
full-feedback confinement-only gate.

## T4n Staged Selector Switch GPU Status

T4n adds `ConfiningStressLateralSelectorStartTime`, a CPU-only selector
scheduling parameter for `FlexibleConfiningStress`. The shared parser and both
Release builds were checked, but GPU execution hard-errors if a non-default
selector schedule is requested. No GPU simulation was run.

The CPU staged-switch tests completed with `code=0`, `excluded=0`, and no
DtMin burst. The active target count changed from `208` all-surface low-`f_i`
particles to `112` lateral selected particles at the switch time. The switch
is not yet a validation route: feedback-off `q` grows and delayed feedback
still fails the physical stability gate. GPU parity, DP, and MCC remain
deferred.

## T4n1 Literature Audit GPU Status

T4n1 is documentation-only. It does not add source code, build, or run CPU/GPU
simulations.

The audit concludes that Zhao and the u-pw notes support initial stress,
damping, `f_i` selection, smooth particle layouts, corrected gradients, and
careful staged equilibration. They do not directly support a ramped
all-surface-to-lateral selector transition. Therefore no new GPU porting work
should begin from a ramped selector idea.

Recommended GPU stance remains unchanged: defer GPU triaxial validation until
the CPU workflow has a reference-supported stable confinement route. The next
CPU task should audit restart-based all-surface confinement equilibrium before
any selector-ramp implementation, axial loading, DP, or MCC work.

## T4n2 Restart Equilibrium Audit GPU Status

T4n2 is XML/script/postprocessing only. It uses existing CPU restart support
and does not add source code or GPU functionality.

The CPU audit confirms that restart can preserve the current elastic u-pw
state needed for staged confinement: velocity, density, stress tensor,
`Kplastic`, and `PorePress` are restored from Stage A `Part_0023`. The restart
is exact in saved CSV precision. This removes restart fidelity as the immediate
blocker.

The physics gate still fails. Restarting into lateral-only confinement lowers
`q` relative to a fresh lateral-only run, but hydrostatic balance is still lost
and delayed feedback after restart reaches order `1e12 Pa/s` `PorePressRate`.
No axial loading, GPU simulation, DP baseline, or MCC work should start from
T4n2.

## T4o Cap-Support-Preserving Staging GPU Status

T4o is XML/script/postprocessing only and adds no new GPU functionality. It
uses existing CPU-only staged triaxial features: `InitialStressMode=1`,
`FlexibleConfiningStress`, restart, and `CapConfiningStress`.

The CPU audit confirms that keeping explicit cap support after the all-surface
restart does not solve the hydrostatic transition. Stage B runs cleanly but
ends with higher `q` (`~61.9 Pa`) than the T4n2 lateral-only restart
(`~37.9 Pa`), and delayed feedback still reaches order `1e12 Pa/s`
`PorePressRate`. No axial smoke, GPU simulation, DP baseline, or MCC work
should start from T4o.

## T4p Cap / Platen Boundary Audit GPU Status

T4p is documentation-only. It adds no source code, no parser changes, no build,
and no CPU/GPU simulations.

The audit concludes that `CapConfiningStress` is not a production triaxial
platen route. Zhao-style triaxial loading uses explicit top/bottom platens:
bottom fixed, top prescribed in axial motion, with lateral confinement handled
separately. The current GPU plan therefore remains deferred until a CPU
platen-boundary workflow is defined and validated.

T4q should be CPU-first. If it needs new platen-boundary controls, the GPU path
should hard-error for non-default settings until the CPU formulation passes the
elastic triaxial staging gates. DP and MCC remain deferred.

## T4q Explicit Platen Workflow GPU Status

T4q is XML/script/postprocessing only. It adds no source code, no parser keys,
and no GPU functionality. GPU simulation was not run.

The CPU Release smokes show that an explicit platen route can be built from
existing fixed/moving `mkbound` mechanics: top prescribed velocity works,
bottom fixed support works, and lateral `FlexibleConfiningStress` can coexist
with the moving top platen. This is a CPU workflow milestone, not a GPU-ready
validation route.

GPU remains deferred because the next blocker is not kernel parity but a
validated platen reaction / axial stress diagnostic. T4r should stay CPU-only
until the platen reaction and specimen-only measurement path are clear. DP and
MCC remain deferred.

## T4r Platen Reaction Diagnostics GPU Status

T4r is XML/script/postprocessing only. It adds no source code, no parser keys,
and no GPU functionality. GPU simulation was not run.

The CPU smokes confirm that explicit platens remain stable with feedback off
and that specimen-only stress proxies can be extracted. However, ordinary
fixed/moving `mkbound` platens still do not expose a true reaction-force output.
T4r therefore reports only a specimen-stress reaction proxy.

GPU remains deferred. The next GPU-relevant source task, if pursued, would be a
diagnostic reaction accumulator for top/bottom platen `mkbound` groups after
the CPU design is validated. Full feedback, DP, and MCC remain deferred.

## T4s Platen Axial Baseline GPU Status

T4s is XML/script/postprocessing only. It adds no source code, no parser keys,
and no GPU functionality. GPU simulation was not run.

The CPU Release feedback-off platen baselines both completed with `code=0`,
`excluded=0`, `DtMin=0`, and `Kplastic=0`. The explicit moving top platen and
fixed bottom platen remain kinematically correct over a longer `0.006 s`
window, and selected lateral `FlexibleConfiningStress` remains compatible with
the platen workflow.

GPU remains deferred. The active blocker for strict validation is still CPU
measurement fidelity: ordinary fixed/moving `mkbound` platens do not expose a
true reaction force, so T4s uses a specimen-stress proxy. A future GPU task
should wait until the CPU reaction diagnostic and full-feedback stability are
resolved. Full feedback, MCC, and GPU triaxial validation remain deferred.

## T5 DP Feedback-Off Platen Baseline GPU Status

T5 is XML/script/postprocessing only. It adds no source code, no parser keys,
and no GPU functionality. GPU simulation was not run.

The CPU Release DP feedback-off baselines both completed with `code=0`,
`excluded=0`, and `DtMin=0`. The high-strength DP case remains effectively
elastic with `Kplastic=0`; the mild-yield case activates `Kplastic` while
remaining bounded in the reduced platen workflow.

GPU remains deferred because the active validation blockers are still CPU-side:
true platen reaction is unavailable, and full pore-pressure feedback remains
deferred. MCC should not be started on GPU before the CPU DP/platen measurement
and feedback decisions are settled.

## T4t Platen Reaction Diagnostics GPU Status

T4t adds CPU-only parser keys and a CPU pairwise platen reaction accumulator:

- `SavePlatenReactionDiagnostics`;
- `PlatenTopMkBound`;
- `PlatenBottomMkBound`;
- `PlatenReactionMode`;
- `PlatenReactionArea`;
- `PlatenReactionInterval`.

The diagnostic hard-errors on GPU when enabled. GPU Release is still built to
verify shared parser/source compatibility, but no GPU simulation is run.

The CPU diagnostic accumulates specimen-platen SPH pairwise interaction
reaction for selected fixed/moving `mkbound` platens. This resolves the
immediate T5 measurement blocker for reduced feedback-off DP refinement, but
it is not a GPU-ready validation route. Full feedback, MCC, and GPU triaxial
validation remain deferred until the CPU platen workflow is physically stable.

## T5b DP Feedback-Off Refinement GPU Status

T5b is XML/script/postprocessing only. It adds no source code, no parser keys,
and no GPU functionality. GPU simulation was not run.

The CPU Release elastic, high-strength DP, and mild-yield DP cases all finish
with `code=0`, `excluded=0`, and `DtMin=0` using the T4t pairwise platen
reaction diagnostic. The high-strength DP line matches the elastic reference;
the mild-yield line activates `Kplastic` in `341/407` specimen particles while
remaining bounded.

This is a CPU reduced feedback-off benchmark. GPU remains deferred until the
full feedback route, actuator-level reaction decision, and any MCC direction
are resolved on CPU.

## T5c DP Feedback-Off Extended Response GPU Status

T5c is XML/script/postprocessing only. It adds no source code, no parser keys,
and no GPU functionality. GPU simulation was not run.

The CPU Release high-strength and mild-yield DP extended cases both finish with
`code=0`, `excluded=0`, and `DtMin=0` using the T4t pairwise platen reaction
diagnostic. The mild-yield case reaches `Kplastic_max approx 1.46e-3` with all
407 specimen particles plastic by the final saved frame while remaining
bounded in velocity and pore-pressure-rate diagnostics.

This remains a CPU reduced feedback-off route. GPU remains deferred until the
full feedback route and any MCC direction are settled on CPU.

## T5d DP Feedback-Off Package GPU Status

T5d is a consolidation-only package. It adds no source code, no parser keys, no
new simulation, and no GPU functionality.

The package summarizes the CPU feedback-off explicit-platen DP route from T4s,
T4t, T5, T5b, and T5c. It confirms that the reduced CPU route has stable
platen grouping, selected lateral confinement, pairwise reaction diagnostics,
and DP plasticity metrics. It does not validate GPU, full pore-pressure
feedback, MCC, or actuator-level platen reactions.

GPU remains deferred. MCC may proceed only as planning/audit work until the CPU
return-mapping and single-point-test path is defined.

## M1 MCC Design Audit GPU Status

M1 is documentation-only. It adds no source code, no parser keys, no build, no
simulation, and no GPU functionality.

The audit recommends `SoilConstitutiveModel=3` for a future Modified Cam Clay
CPU path, but GPU support should remain hard-deferred until:

- CPU single-point MCC return mapping passes;
- MCC state arrays are restart-safe and output-safe on CPU;
- a feedback-off CPU SPH platen smoke passes;
- the full feedback route is either fixed or explicitly scoped out.

Future GPU work will need mirrored MCC state arrays, device return mapping,
sorting/restart/output integration, and parity tests. Full feedback and GPU
triaxial validation remain deferred.

## M2 MCC Single-Point Prototype GPU Status

M2 adds only a standalone Python material-point MCC prototype under
`src/papers/u-p/mcc_single_point/`. It does not modify C++/CUDA source, parser
logic, production builds, or GPU kernels.

The prototype confirms a CPU-side return-mapping direction for future M3 work,
but GPU remains deferred. A future GPU MCC port would need:

- CPU `SoilConstitutiveModel=3` parity first;
- MCC state arrays on CPU and GPU;
- restart/output support for MCC fields;
- device-side local Newton return mapping;
- single-point and SPH parity tests.

Until those gates pass, future `SoilConstitutiveModel=3` should hard-error on
GPU. Full pore-pressure feedback also remains deferred.

## M3a MCC C++ Helper GPU Status

M3a adds a standalone C++ MCC material-point helper under
`src/papers/u-p/mcc_single_point/cpp/`. It is not linked into the production
SPH solver and adds no CUDA path.

The helper passes Python parity for isotropic, drained-like, and undrained-like
single-point paths. This is a CPU-side numerical reference only. GPU MCC
remains deferred until after CPU parser/state/output and CPU SPH stress-update
smokes pass.

## M3b MCC Parser / State Init GPU Status

M3b adds production parser/state/output infrastructure for
`SoilConstitutiveModel=3` on CPU:

- MCC XML parameters;
- CPU state arrays;
- initialization from `pc0` or `OCR`;
- `SaveMccState` output fields.

GPU behavior is intentionally conservative:

```text
SoilConstitutiveModel=3 -> hard error when Cpu=false
```

GPU Release build passes, but no GPU simulation was run. There are still no
GPU MCC state arrays, no device return mapping, no GPU restart support, and no
GPU validation route.

Full pore-pressure feedback and GPU remain deferred. M3c should be CPU stress
update only.

## M3c MCC CPU Stress Update GPU Status

M3c connects Modified Cam Clay to the CPU stress-update branch only. The GPU
policy is unchanged:

```text
SoilConstitutiveModel=3 -> hard error when Cpu=false
```

GPU Release build passes after the shared parser/source changes, but no GPU
simulation was run. There is still no GPU MCC return mapping, no GPU MCC state
array update, and no GPU restart/output parity for MCC.

The CPU smokes confirm high-pc elastic-like behavior and mild-yield MCC state
updates under feedback-off explicit platen loading. GPU work remains deferred
until the CPU MCC branch has a stable M3d/M3e feedback-off baseline and the
full pore-pressure feedback question is either fixed or explicitly scoped out.

## M3d MCC Feedback-Off Refinement GPU Status

M3d performs CPU-only MCC refinement cases with no source changes and no GPU
simulation. The existing policy remains:

```text
SoilConstitutiveModel=3 -> hard error when Cpu=false
```

The high-pc MCC extended case is elastic-like and stable, but the mild-yield
extended case exposes local return failures (`MccReturnStatus=-3` in a small
particle subset). GPU MCC work should remain deferred until the CPU local
return behavior is robust over the feedback-off platen baseline. Full
pore-pressure feedback remains deferred as well.

## M3j Boundary Failure Audit GPU Status

M3j is a postprocessing-only boundary/platen/edge audit using retained M3d2,
M3f, and M3h CSV outputs. It adds no source changes, no GPU source, no GPU
build requirement, and no GPU simulation.

The GPU policy remains:

```text
SoilConstitutiveModel=3 -> hard error when Cpu=false
```

M3j concludes that the remaining mild-MCC return failures are concentrated in
platen/edge/cap-adjacent regions and recommends a CPU-only dense-output
boundary diagnostic before any clean MCC validation package. GPU MCC and full
pore-pressure feedback remain deferred.

## M3h MCC Admissible Return GPU Status

M3h changes shared CPU/parser/output code for MCC admissible line-search
diagnostics but does not add GPU MCC support. The GPU policy remains:

```text
SoilConstitutiveModel=3 -> hard error when Cpu=false
```

New M3h CPU-only MCC diagnostics:

- `MccAdmissibleLineSearch`;
- `MccLineSearchMaxBacktrack`;
- `MccLineSearchMinStep`;
- `MccLineSearchResidualReduction`;
- `MccEnforcePositivePlasticMultiplier`;
- `MccAdmissibleProjection`;
- `MccLineSearchBacktrackCount`;
- `MccLineSearchRejectReason`;
- `MccLineSearchMinAlpha`.

The M3h CPU cases are solver-stable, but the mild MCC return route is still not
a clean validation candidate because every tested route retains at least one
saved-frame negative return status. GPU MCC should remain deferred until the
CPU return mapping has a clean no-fallback candidate and the device-side MCC
state/update/restart design is specified. Full pore-pressure feedback remains
deferred.

## M3d2 MCC Return Robustness GPU Status

M3d2 adds CPU-only XML/workflow/postprocessing diagnostics for the MCC local
return failures found in M3d. No GPU simulation was run and no GPU source was
changed.

The audit confirms that the remaining mild-yield issue is local MCC return
robustness: baseline and tight-return cases end with `ReturnStatus=-3` for
8/407 particles, while half top-platen velocity clears the final failed set but
not all intermediate local failures.

GPU MCC remains deferred. The next CPU step should be an opt-in MCC
substepping/admissibility-guard patch, still with the existing GPU hard error
for `SoilConstitutiveModel=3`. Full pore-pressure feedback remains deferred.

## M3d3 MCC Substepping GPU Status

M3d3 adds CPU-only MCC constitutive substepping, admissibility guards, fallback
diagnostics, and additional `SaveMccState` output fields. The GPU policy is
unchanged:

```text
SoilConstitutiveModel=3 -> hard error when Cpu=false
```

CPU Release and GPU Release builds pass after the shared parser/source changes,
but no GPU simulation was run. There is still no GPU MCC return mapping, no GPU
MCC substepping, and no GPU MCC state-array update. Full pore-pressure feedback
also remains deferred.

## M3e MCC Reporting Package GPU Status

M3e is a postprocessing and documentation consolidation stage. It adds no GPU
source, no GPU build requirement beyond the already-passed M3d3 GPU Release
compile, and no GPU simulation.

The GPU policy remains:

```text
SoilConstitutiveModel=3 -> hard error when Cpu=false
```

The consolidated MCC route is CPU-only, feedback-off, and reduced. GPU MCC
should remain deferred until the CPU return/staging issue is clean and a GPU
MCC state/update/restart design exists. Full pore-pressure feedback also
remains deferred.

## M3f MCC Return/Staging GPU Status

M3f changes shared CPU/parser/output code for MCC diagnostics but does not add
GPU MCC support. The GPU policy remains:

```text
SoilConstitutiveModel=3 -> hard error when Cpu=false
```

New M3f CPU-only MCC diagnostics:

- `MccMinSubsteps`;
- `MccSubstepYieldDistanceThreshold`;
- `MccSubstepTriggerReason`.

The M3f CPU cases show that the mild MCC return/staging route is still not
clean: all tested candidates retain transient negative return-status episodes.
GPU MCC should remain deferred until the CPU route has a clean no-fallback
candidate and a device-side MCC state/update/restart design. Full
pore-pressure feedback remains deferred as well.

## M3k Platen/Edge Diagnostic GPU Status

M3k adds no GPU source changes and runs no GPU simulation. It is a CPU-only
dense-output postprocessing diagnostic for MCC return failures near
platen/edge/cap regions.

The GPU policy remains:

```text
SoilConstitutiveModel=3 -> hard error when Cpu=false
```

The M3k evidence points to boundary-induced local strain/support paths rather
than a GPU-portable constitutive-kernel task. GPU MCC should remain deferred
until the CPU platen/edge issue has a clean no-fallback route and the MCC
state/update/restart design is stable. Full pore-pressure feedback remains
deferred.

## M3l Platen/Specimen Smoothing GPU Status

M3l is XML/geometry/workflow/postprocessing only. It adds no GPU source and runs
no GPU simulation.

The GPU policy remains unchanged:

```text
SoilConstitutiveModel=3 -> hard error when Cpu=false
```

The M3l cases confirm that boundary/interface geometry changes can strongly
alter MCC return failures. This reinforces that GPU MCC should remain deferred
until the CPU reduced route has a clean boundary geometry and a stable
state/update/restart design. Full pore-pressure feedback remains deferred.

## M3m Refined Geometry GPU Status

M3m is XML/geometry/workflow/postprocessing only. It adds no GPU source and
runs no GPU simulation.

The GPU policy remains unchanged:

```text
SoilConstitutiveModel=3 -> hard error when Cpu=false
```

M3m confirms that platen/edge geometry can improve but not clean the CPU MCC
return route. The larger platen overhang reduces near-tension statuses and
keeps the global response bounded, but transient `ReturnStatus=-3` remains and
the short extended check is not clean. GPU MCC remains deferred until a cleaner
CPU boundary geometry or smooth/fan-like layout is established. Full
pore-pressure feedback also remains deferred.

## M3n Smooth Layout GPU Status

M3n is XML/workflow/postprocessing only. It adds no GPU source changes and
runs no GPU simulation.

The GPU policy remains unchanged:

```text
SoilConstitutiveModel=3 -> hard error when Cpu=false
```

The M3n higher-resolution cut-cell diagnostic improves edge/cap support
metrics, but it worsens transient MCC return-status populations. This keeps
GPU MCC deferred: there is still no clean CPU boundary/layout route to port,
and full pore-pressure feedback remains deferred.

## M3o Smooth/Fan-Like Layout GPU Status

M3o adds no GPU source and runs no GPU simulation. It is an isolated external
geometry generator plus support/neighbor diagnostics for a radial-ring
smooth-edge triaxial specimen prototype.

The GPU policy remains unchanged:

```text
SoilConstitutiveModel=3 -> hard error when Cpu=false
```

The generated fan-like layout is not yet connected to GenCase/DualSPHysics as a
solver input, and it is not a clean CPU MCC candidate. GPU MCC remains deferred
until there is a confirmed CPU custom-particle or smooth-layout workflow with
stable return-status behavior. Full pore-pressure feedback remains deferred.

## M3i-Revised Caveated MCC Package GPU Status

M3i-revised adds no GPU source changes and runs no GPU simulation. It is a
reporting-only consolidation of the CPU feedback-off MCC reduced route after
the decision to defer custom fan-like solver import.

The GPU policy remains unchanged:

```text
SoilConstitutiveModel=3 -> hard error when Cpu=false
```

The current MCC route is useful as a CPU reduced prototype, but not as clean
validation. Local boundary-induced return failures remain, full pore-pressure
feedback remains deferred, custom smooth/fan-like import is deferred, and GPU
MCC remains deferred until a clean CPU validation path exists.

## L2 External-Load 1D Consolidation GPU Status

L2 adds no source changes. It is an XML/workflow/postprocessing extension of
the native `AccInput` one-dimensional external-load route.

GPU Release supports the selected parameters:

```text
SoilConstitutiveModel=0
HydraulicElevationSource=1
PorePressureBoundaryOperator=0
PorePressureFeedbackOperator=1
native AccInput on mkfluid=1
```

The L2 GPU short run completed with `code=0`, `excluded=0`, and no DtMin
adjustments, matching the CPU run closely. The GPU path is therefore available
for this reduced external-load workflow.

The physics result is caveated: mapping `q0=-10 kPa` to a top material-layer
acceleration produced a large dynamic excess-pressure response rather than the
quasi-static Terzaghi analytical curve. This is a loading-route limitation, not
a GPU port blocker. Full GPU MCC and full-feedback triaxial validation remain
deferred under their previous policies.

## L3b Mechanical Top-Load GPU Status

L3b adds a small CPU-only source path for `MechanicalTopLoad=1`. The parser and
shared code compile in GPU Release, but GPU simulation intentionally hard-errors
when the new option is enabled:

```text
MechanicalTopLoad=1 -> CPU-only in this branch
```

The CPU L3b case is numerically stable, but its pressure response remains
dynamic and not Terzaghi-faithful. GPU implementation is therefore deferred
until a physically acceptable mechanical loading route is established. The L3a
initial-pressure diffusion gate remains the GPU-supported analytical PR
boundary check.

## L3c Consistent Initial-State GPU Status

L3c adds no source changes. It uses the GPU-supported initial-pressure route:

```text
PorePressureInit=3
PorePressureAnalyticalProfile=3
InitialStressMode=0
MechanicalTopLoad=0
PorePressureFeedback=0
```

Both CPU and GPU Release L3c runs completed with `code=0`, `excluded=0`, and
`DtMin=0`. The pressure metrics match the L3a diffusion gate and avoid the
L2/L3b dynamic excess-pressure peak.

The CPU-only `InitialStressMode=1` path remains unavailable on GPU, but L3c
does not need it: the Terzaghi instantaneous-undrained initial condition is
represented as `p_w^0=|q0|` with zero effective-stress increment. GPU support
for L3c is therefore active for the reduced PR diffusion/boundary validation
gate. Mechanical load generation and full feedback remain separate deferred
tasks.

## L3e 1D Consolidation Package GPU Status

L3e is reporting-only. It adds no GPU source and runs no new simulation.

The package confirms:

- L2 AccInput: CPU/GPU stable but not strict validation because the loading
  route generates a dynamic pressure peak;
- L3a/L3c initial-state gates: CPU/GPU stable and suitable for PR diffusion and
  hydraulic-boundary validation;
- L3b MechanicalTopLoad: CPU-only diagnostic, GPU implementation deferred
  because the route is not physically acceptable yet.

GPU support for the current 1D validation figure is active through L3c.
Mechanical top-load GPU work should remain deferred until a CPU route is
paper-faithful. Full-feedback and MCC GPU work remain deferred under their
existing policies.
