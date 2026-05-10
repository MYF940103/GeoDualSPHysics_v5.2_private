# GPU Port Plan for the CPU u-pw PR Prototype

This document is a read-only planning note for porting the current CPU-side u-pw PR prototype to GPU. It does not describe an immediate CUDA patch. The goal is to separate core production requirements from CPU-only diagnostics and to define a staged CPU/GPU parity path.

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
| `PorePressureAceSymCorrc` | `tfloat3*` | Corrected-gradient symmetric diagnostic that did not improve boundary behavior | Do not port initially |

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

The symmetric diagnostic `PorePressureAceg` may be ported later only if strict backward compatibility with `PorePressureFeedbackOperator=0` is required on GPU. The corrected symmetric diagnostic `PorePressureAceSymCorrc` should remain CPU-only or be removed later, because it increased the uniform-pressure boundary spike in CPU tests.

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
