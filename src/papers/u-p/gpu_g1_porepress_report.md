# GPU G1 Passive Pore Pressure Report

Date: 2026-05-11

## Scope

Implemented only the passive GPU pore-pressure state needed for one-frame
output parity. This phase does not implement GPU PR pore-pressure rate,
feedback, Shepard regularization, hydromechanical damping, hydraulic boundary
correction, boundary ghost operators, corrected-gradient operators, or
softening.

## Modified Source Paths

- `source/JSphGpu.h`
- `source/JSphGpu.cpp`
- `source/JSphGpuSingle.cpp`
- `source/JCellDivGpu.h`
- `source/JCellDivGpu.cpp`
- `source/JCellDivGpu_ker.h`
- `source/JCellDivGpu_ker.cu`
- `source/JSphGpu_ker.h`
- `source/JSphGpu_ker.cu`

## Implementation Summary

- Added `double *PorePressg` in `JSphGpu`.
- Allocated `PorePressg` when `HydromechCoupling || SavePorePressure`.
- Preserved `PorePressg` during GPU particle-buffer resize.
- Initialized `PorePressg` from a CPU temporary buffer using the same
  hydrostatic elevation convention as CPU:

  ```text
  z_h = -dot(pos, HydraulicGravity / |HydraulicGravity|)
  p_hydro = WaterDensity * |HydraulicGravity| * max(PorePressureWaterLevel - z_h, 0)
  ```

- Supported passive initialization modes:
  - `PorePressureInit=0`: zero;
  - `PorePressureInit=1`: hydrostatic;
  - `PorePressureInit=3`: hydrostatic plus analytical excess.
- Added a standalone `double*` sort path in `JCellDivGpu`.
- Added standalone periodic duplicate support for scalar `double` arrays.
- Added GPU output of:
  - `PorePress`;
  - `ExcessPorePress`, computed on CPU during output from copied `PorePressg`.

## Explicitly Not Implemented

- No `PorePressRateg`.
- No `DivVelg`.
- No `LapPorePressg`.
- No `LapZg`.
- No `PorePressureAccelDiffg`.
- No GPU pore-pressure update.
- No GPU feedback.
- No GPU Shepard/damping.
- No GPU top drained/bottom no-flux.
- No GPU boundary ghost.
- No GPU softening.

## Build

Command:

```powershell
msbuild .\VS\DualSPHysics5Re.sln /m /t:Build /p:Configuration=Debug /p:Platform=x64 /v:minimal
```

Result: succeeded.

Notes: existing PDB/link warnings were reported for bundled libraries; no G1
compile errors remain.

## Smoke Test

Case:

```text
examples/u-pw/01_1D_Consolidation/experiments/GPU_G1_PorePress/
  Case1DConsolidation_PR_GPU_G1_PorePress_Def.xml
```

Settings:

- `HydromechCoupling=1`
- `PorePressureModel=1`
- `PorePressureInit=1`
- `PorePressureWaterLevel=1.0`
- `SavePorePressure=1`
- `TimeMax=0.0001`
- `TimeOut=0.0001`

Run result:

- GenCase `code=0`.
- DualSPHysics GPU Debug wrote `Run.out` with `code=0`.
- `excluded=0`.
- `PorePress` and `ExcessPorePress` were present in `PartCsv_0000.csv` and
  `PartCsv_0001.csv`.
- No NaN/Inf was detected in the sampled pore-pressure fields.

Summary from `gpu_g1_smoke_summary.csv`:

| Part | material particles | PorePress max [Pa] | Excess maxAbs [Pa] | hydrostatic maxAbs error [Pa] |
|---|---:|---:|---:|---:|
| 0000 | 1000 | 9760.9504 | 0 | 4.89422e-4 |
| 0001 | 1000 | 9760.9504 | 0 | 4.89422e-4 |

Generated output directories were removed after summary extraction.

## Readiness

G1 is complete for passive `PorePressg` state/output parity.

Do not enter G2 without a separate instruction. The next phase, if approved,
should remain limited to PR diagnostic arrays/kernels and should still exclude
feedback, Shepard, damping, boundary ghost, softening, and long GPU runs unless
explicitly authorized.
