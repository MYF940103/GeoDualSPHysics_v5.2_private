# GPU G5 Pore-Pressure Feedback Report

Date: 2026-05-11

## Scope

GPU Phase G5 implements the CPU-recommended difference-gradient pore-pressure
feedback path on GPU:

```text
grad p_i = sum_j (m_j / rho_j) * (p_j - p_i) * gradW_ij
a_pw_i   = -grad p_i / rho_i
```

For `PorePressureFeedbackMode=1`, the feedback pressure is excess pressure:

```text
p_feedback = PorePress - hydrostatic
```

This phase does not implement GPU Shepard regularization, hydromechanical
damping, top/bottom boundary changes beyond G4, boundary ghost production,
softening, corrected-gradient feedback, symmetric feedback operator `0`, or
long coupled GPU runs.

## Modified Source Files

- `source/JSphGpu.h`
- `source/JSphGpu.cpp`
- `source/JSphGpuSingle.cpp`
- `source/JSphGpu_ker.h`
- `source/JSphGpu_ker.cu`

## New GPU State

Added:

```cpp
float3 *PorePressureAceDiffg;
```

It is now included in:

- initialization to `NULL`;
- GPU particle allocation and accounting;
- resize save/restore;
- sorting with `JCellDivGpu::SortDataArrays(float3*)`;
- periodic duplicate via the new `PeriodicDuplicateFloat3()`;
- initialization/reset to zero;
- output copy-back with periodic-particle filtering.

## Kernels

Added GPU kernels/wrappers:

- `ComputePorePressureAccelDiff()`
- `ApplyPorePressureFeedback()`
- `PeriodicDuplicateFloat3()`

The feedback kernel is material-material only and mirrors the current CPU
`PorePressureAccelDiff` sign convention. It supports feedback modes `0` and
`1`, but G5 validation focuses on the recommended excess-pressure mode `1`.

When `PorePressureFeedback=1`, GPU feedback currently requires
`PorePressureFeedbackOperator=1`. Operator `0` is not implemented on GPU and
raises an error instead of silently using a different path.

## Call Site

`JSphGpuSingle::Interaction_Forces()` now performs:

```text
ComputeHydroPrDiagnosticsGpu()
ComputePorePressureAccelDiffGpu()
ApplyPorePressureFeedbackGpu() when feedback is enabled
```

This happens after the base interaction force calculation and before the
2D `Ace.y` reset and `ComputeAceMax()`, so the feedback acceleration contributes
to the accepted GPU timestep.

`SaveData()` recomputes the diagnostic before output when `SavePorePressure=1`.

## Output

G5 adds:

```text
PorePressureAccelDiff.x
PorePressureAccelDiff.y
PorePressureAccelDiff.z
```

Existing G1-G4 output fields remain:

```text
PorePress
ExcessPorePress
PorePressRate
DivVel
LapPorePress
LapZ
```

## Build Results

- GPU Debug build: passed.
- GPU Release build: passed.

The GPU Debug hydrostatic smoke wrote a finished `Run.out` with `code=0`, but
the process did not exit cleanly. This matches earlier Debug-run behavior, so
the final smoke validation used GPU Release.

## Smoke Cases

Smoke files are in:

`examples/u-pw/01_1D_Consolidation/experiments/GPU_G5_Feedback/`

Retained files:

- `Case1DConsolidation_PR_GPU_G5_Hydro_Def.xml`
- `Case1DConsolidation_PR_GPU_G5_Uniform_Def.xml`
- `Case1DConsolidation_PR_GPU_G5_NonUniform_Def.xml`
- `xCase1DConsolidation_PR_GPU_G5_Hydro_win64_GPU_debug.bat`
- `xCase1DConsolidation_PR_GPU_G5_Uniform_win64_GPU_debug.bat`
- `xCase1DConsolidation_PR_GPU_G5_NonUniform_win64_GPU_debug.bat`
- `analyze_gpu_g5.py`
- `gpu_g5_smoke_summary.csv`

Generated output directories were removed after extracting the summary.

## Smoke Results

| Case | code | excluded | steps | `PorePressureAccelDiff` max magnitude |
| --- | ---: | ---: | ---: | ---: |
| Hydrostatic excess mode | 0 | 0 | 21 | `4.0067e-7 m/s2` |
| Uniform excess, no drained boundary | 0 | 0 | 21 | `4.0067e-7 m/s2` |
| Nonuniform excess | 0 | 0 | 21 | `1.4110 m/s2` |

CPU/GPU final-frame comparisons:

| Case | maxAbs `PorePress` difference | max magnitude difference in `PorePressureAccelDiff` |
| --- | ---: | ---: |
| Hydrostatic excess mode | `3.73e-5 Pa` | `4.86e-7 m/s2` |
| Uniform excess | `3.73e-5 Pa` | `4.86e-7 m/s2` |
| Nonuniform excess | `4.36e-5 Pa` | `1.70e-2 m/s2` |

The hydrostatic and uniform-excess cases produce near-zero feedback
accelerations, while the nonuniform excess case produces a finite acceleration
with the same qualitative behavior as CPU.

## Assessment

G5 passes the scoped feedback smoke tests. The GPU now supports the recommended
excess-pressure difference-gradient feedback operator (`PorePressureFeedbackMode=1`,
`PorePressureFeedbackOperator=1`) for short coupled smoke tests.

G6 may be considered only as a separate phase. It should not start automatically
from this report.
