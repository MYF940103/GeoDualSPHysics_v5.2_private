# GPU G3 Pore-Pressure Update Report

Date: 2026-05-11

## Scope

GPU Phase G3 extends the G1/G2 passive and diagnostic pore-pressure path with
an explicit pressure-state update and a host-side `dt_pore` restriction. This
phase remains pressure-only with respect to hydromechanical coupling.

Implemented:

- `PorePressg[p] += PorePressRateg[p] * dt` for material/fluid particles.
- GPU timestep restriction:
  `dt_pore = PorePressureDtSafety * (rho_w*g_h*n/Kw) * h^2 / k`.
- Updated `PorePress` and `ExcessPorePress` output after the pressure update.
- Existing G2 diagnostic output:
  `PorePressRate`, `DivVel`, `LapPorePress`, and `LapZ`.

Not implemented in G3:

- GPU feedback or `PorePressureAccelDiff`.
- GPU Shepard regularization.
- GPU hydromechanical damping.
- GPU top drained or bottom no-flux correction.
- GPU boundary ghost logic.
- GPU softening.
- Long GPU runs.

## Modified Source Files

- `source/JSphGpu.h`
- `source/JSphGpu.cpp`
- `source/JSphGpuSingle.cpp`
- `source/JSphGpu_ker.h`
- `source/JSphGpu_ker.cu`

## Update Kernel

The new GPU kernel is exposed as:

```cpp
cusph::UpdatePorePressure(unsigned n,unsigned pini,const typecode *code,double dt,
  double *porepress,const float *porepressrate);
```

It updates only particles satisfying `CODE_IsFluid(code[p])`. It does not clamp
pressure and does not apply any boundary or smoothing correction.

## Call Order

The GPU step now follows the G3 pressure-only ordering:

1. Mechanical interaction is computed as before.
2. `ComputeHydroPrDiagnosticsGpu()` computes `DivVel`, `LapPorePress`, `LapZ`,
   and `PorePressRate`.
3. `DtVariable()` applies the `dt_pore` cap.
4. `UpdatePorePressureGpu(dt)` advances `PorePressg`.
5. The normal mechanical update continues.

For Symplectic, the initial `SymplecticDtPre` is also limited by `dt_pore`, as
in the CPU path.

## Timestep Restriction

The restriction is active only when:

```text
HydromechCoupling=1
PorePressureModel=1
SoilCte.HydraulicConductivity > 0
```

It uses:

- `SoilCte.Porosity0`
- `SoilCte.HydraulicConductivity`
- `SoilCte.WaterBulkModulus`
- `SoilCte.WaterDensity`
- `HydraulicGravity` magnitude
- `PorePressureDtSafety`
- `KernelH`

The G3 smoke cases reported:

```text
dt_pore = 4.76766e-07 s
```

## Smoke Cases

Smoke files are in:

`examples/u-pw/01_1D_Consolidation/experiments/GPU_G3_PorePressUpdate/`

Retained files:

- `Case1DConsolidation_PR_GPU_G3_Hydro_Def.xml`
- `Case1DConsolidation_PR_GPU_G3_Analytical_Def.xml`
- `xCase1DConsolidation_PR_GPU_G3_Hydro_win64_GPU_debug.bat`
- `xCase1DConsolidation_PR_GPU_G3_Analytical_win64_GPU_debug.bat`
- `analyze_gpu_g3.py`
- `gpu_g3_smoke_summary.csv`

The generated `_out` directories were removed after summary extraction.

## Build Results

- GPU Debug build: passed.
- GPU Release build: passed.

GPU Release was used for the smoke runs.

## Smoke Results

All four short runs completed successfully:

| Case | Mode | code | excluded | steps |
| --- | --- | ---: | ---: | ---: |
| hydrostatic | GPU Release | 0 | 0 | 1 |
| analytical excess | GPU Release | 0 | 0 | 1 |
| hydrostatic reference | CPU Release | 0 | 0 | 1 |
| analytical excess reference | CPU Release | 0 | 0 | 1 |

Selected metrics from `gpu_g3_smoke_summary.csv`:

| Metric | Hydrostatic GPU | Analytical GPU |
| --- | ---: | ---: |
| `dt_pore` | `4.76766e-07` | `4.76766e-07` |
| `DeltaPorePress_maxAbs` | `8.326e-06 Pa` | `7.602206 Pa` |
| `DeltaMinusRateDt_maxAbs` | `4.912e-06 Pa` | `1.113567 Pa` |
| `ExcessPorePress_maxAbs` | `8.326e-06 Pa` | `999.549498 Pa` |
| `PorePressRate_maxAbs` | `8.21733 Pa/s` | `1.3609694e7 Pa/s` |

CPU/GPU one-step pressure-delta differences:

- hydrostatic maxAbs: `8.994e-06 Pa`
- analytical excess maxAbs: `7.852e-06 Pa`

The analytical `DeltaMinusRateDt` value is not expected to be exactly zero
because the report compares the final output diagnostic rate against the
one-step pressure change. G3 recomputes diagnostics at output after the pressure
state has changed.

## G4 Readiness

G3 satisfies the requested pressure-update gate:

- `PorePressg` advances explicitly from `PorePressRateg`.
- `dt_pore` limits the GPU timestep.
- Updated pressure fields are written.
- One-step GPU/CPU pressure deltas agree within about `1e-5 Pa`.

G4 should not be started without an explicit request. The next pressure-only
parity work should focus on GPU top drained and bottom no-flux corrections and
the ordering needed for the 1D pressure-only diffusion baseline. GPU feedback,
Shepard, damping, boundary ghost, softening, and long runs remain outside G4
unless separately authorized.
