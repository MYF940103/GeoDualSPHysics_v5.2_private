# GPU G6 Pore-Pressure Stabilization Report

Date: 2026-05-11

## Scope

G6 added only the GPU stabilization operators needed for short coupled smoke
tests:

- hydromechanical damping;
- pore-pressure Shepard regularization.

G6 did not add GPU softening, boundary ghost production operators,
corrected-gradient PR production operators, symmetric feedback operator `0`, or
long coupled reproduction runs.

## Modified Source Files

- `source/JSphGpu.h`
- `source/JSphGpu.cpp`
- `source/JSphGpuSingle.cpp`
- `source/JSphGpu_ker.h`
- `source/JSphGpu_ker.cu`

## Hydromechanical Damping

GPU damping mirrors the CPU formula:

```text
a_damp = -c_d v
```

The host-side effective damping coefficient is the same value already resolved
from `HydromechDampingCoef` or `HydromechDampingXi`. The GPU path applies
damping only when:

- `HydromechCoupling=1`;
- `PorePressureModel=1`;
- `PorePressureFeedback=1`;
- `HydromechDamping=1`;
- the effective coefficient is positive;
- the current time lies within the configured start/end window.

The damping kernel adds to `Aceg`; it does not modify velocity directly. The
call is placed after pore-pressure feedback and before acceleration reduction /
timestep selection.

## Pore-Pressure Shepard

GPU Shepard regularization uses a temporary double buffer:

```text
PorePressShepardTmpg
```

The operator is material-material only. It does not use boundary ghost pressure
or MLS reconstruction.

Mode behavior:

- mode `0`: regularize total `PorePress`;
- mode `1`: regularize excess pressure and reconstruct
  `PorePress = hydrostatic + excess_reg`.

The GPU ordering is:

```text
PorePress update
-> Shepard if due
-> top drained correction
-> bottom no-flux correction
```

This matches the CPU ordering used for the stabilization path. The interval
uses the same step counter convention as CPU, applying on `Nstep + 1`.

## Build Results

- GPU Debug build: passed.
- GPU Release build: passed.

Both builds used `VS/DualSPHysics5Re.sln` with x64 platform.

## Smoke Cases

Templates and analysis are stored in:

```text
examples/u-pw/01_1D_Consolidation/experiments/GPU_G6_Stabilization/
```

The generated particle/log outputs were removed after analysis. The retained
files are XML/BAT templates, `analyze_gpu_g6.py`, and
`gpu_g6_smoke_summary.csv`.

### Summary

| Case | code | excluded | steps | Key result |
|---|---:|---:|---:|---|
| DampingOff | 0 | 0 | 21 | baseline coupled feedback smoke without damping |
| DampingOn | 0 | 0 | 21 | damping path active; GPU/CPU `PorePress` maxAbs diff `4.15e-5 Pa` |
| ShepardHydro | 0 | 0 | 21 | hydrostatic excess maxAbs `2.87e-5 Pa` |
| ShepardAnalytical | 0 | 0 | 5 | smoothing finite; final-initial `PorePress` maxAbs `57.0 Pa` |
| CoupledShort | 0 | 0 | 21 | feedback+damping+Shepard+top/bottom smoke passed |

Selected final-frame comparisons:

- `CoupledShort` GPU/CPU `PorePress` maxAbs difference:
  `2.30e-5 Pa`.
- `CoupledShort` GPU/CPU `PorePressureAccelDiff` max-magnitude difference:
  `1.32e-5 m/s2`.
- `ShepardAnalytical` GPU/CPU `PorePress` maxAbs difference:
  `1.33e-5 Pa`.
- `DampingOn` versus `DampingOff` remained finite and bounded in the very short
  smoke window.

## G7 Readiness

G6 is complete for short stabilization parity. A separately scoped G7 may start
with short self-weight / Terzaghi-style GPU parity only.

G7 should not include long reproduction runs, GPU softening, boundary ghost
production operators, or corrected-gradient production operators.
