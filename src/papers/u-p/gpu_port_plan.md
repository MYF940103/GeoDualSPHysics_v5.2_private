# GPU Port Plan for the CPU u-pw PR Prototype

This document is a read-only planning note for porting the current CPU-side u-pw PR prototype to GPU. It does not describe an immediate CUDA patch. The goal is to separate core production requirements from CPU-only diagnostics and to define a staged CPU/GPU parity path.

## Full CPU Gate Status, 2026-05-11

This document remains a technical reference only. GPU coding is currently
blocked by the stricter full CPU reproduction gate: reduced smokes for 03-06 are
not strict paper reproductions. Do not start `JSphGpu*`, `JCellDivGpu*`, `.cu`,
CUDA memory, sorting, duplicate, output, or kernel work until the full CPU
audit/backlog blockers are implemented or explicitly deferred.

If GPU work is later allowed, the first permitted scope should remain passive
`PorePressg`/output parity only, not the full PR loop.

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
