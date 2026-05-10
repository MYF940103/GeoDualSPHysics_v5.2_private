# GPU G2 PR Diagnostics Report

Date: 2026-05-11

## Scope

GPU Phase G2 was implemented as a diagnostic-only extension of G1. The GPU path
now carries and outputs the passive pore-pressure state from G1 plus four PR
diagnostic fields:

- `PorePressRate`
- `DivVel`
- `LapPorePress`
- `LapZ`

The phase deliberately does not update `PorePressg` and does not modify the GPU
dynamics. No GPU feedback, Shepard regularization, hydromechanical damping,
top drained or bottom no-flux correction, boundary ghost operator, softening,
or long GPU run was added.

## Modified Source Files

- `source/JSphGpu.h`
- `source/JSphGpu.cpp`
- `source/JSphGpuSingle.cpp`
- `source/JSphGpu_ker.h`
- `source/JSphGpu_ker.cu`

## GPU Arrays

The following GPU arrays were added:

| Array | Type | Role |
| --- | --- | --- |
| `PorePressRateg` | `float*` | Diagnostic PR pore-pressure rate |
| `DivVelg` | `float*` | Mathematical skeleton velocity divergence |
| `LapPorePressg` | `float*` | Pore-pressure Laplacian |
| `LapZg` | `float*` | Hydraulic elevation Laplacian |

They are allocated when `HydromechCoupling || SavePorePressure`, matching the
G1 passive pressure allocation policy.

## Lifecycle Coverage

G2 arrays are connected to:

- pointer initialization in `JSphGpu::InitVars()`;
- release/reset in `JSphGpu::FreeGpuMemoryParticles()`;
- memory accounting in `JSphGpu::AllocGpuMemoryParticles()`;
- reservation in `JSphGpu::ReserveBasicArraysGpu()`;
- resize preserve/restore in `JSphGpu::ResizeGpuMemoryParticles()`;
- zero initialization in `JSphGpu::InitPorePressureDiagnosticsGpu()`;
- sorting in `JSphGpuSingle::RunCellDivide()`;
- periodic duplicate copy in `JSphGpuSingle::RunPeriodic()`;
- output copy-back in `JSphGpuSingle::SaveData()`.

## Diagnostic Kernel

`cusph::ComputeHydroPrDiagnostics()` computes material-material-only PR
diagnostics from the current GPU particle state. The implementation mirrors the
current CPU production operators:

- `DivVel` is the mathematical divergence of the skeleton velocity, so
  compression remains negative.
- `LapPorePress` uses total `PorePressg`.
- `LapZ` uses the same hydraulic elevation convention as CPU.
- `PorePressRate` is diagnostic-only and uses the SW-2a sign convention:

```text
PorePressRate =
  Kw/n * (-DivVel + k/(rho_w*g_h)*LapPorePress + k*LapZ)
```

The kernel does not update `PorePressg`.

## Output Fields

GPU `SaveData()` now writes:

- `PorePress`
- `ExcessPorePress`
- `PorePressRate`
- `DivVel`
- `LapPorePress`
- `LapZ`

It still does not write GPU `PorePressureAccelDiff` or any feedback,
Shepard, damping, boundary ghost, or softening fields because those are not in
G2 scope.

## Build

- GPU Debug build: passed.
- GPU Release build: passed.

The Debug executable produced a Visual C++ runtime dialog/hang during the
analytical-excess smoke after output. The final smoke validation therefore used
GPU Release. This did not require any G2 scope expansion.

## Smoke Cases

Smoke files are in:

`examples/u-pw/01_1D_Consolidation/experiments/GPU_G2_PRDiagnostics/`

The directory contains:

- `Case1DConsolidation_PR_GPU_G2_Hydro_Def.xml`
- `Case1DConsolidation_PR_GPU_G2_Analytical_Def.xml`
- GPU debug launch BAT files for both cases
- `analyze_gpu_g2.py`
- `gpu_g2_smoke_summary.csv`

Both smoke XML files use the current recommended soil-material location for
u-pw constants under `<execution><special><soils>`.

## Smoke Results

Final GPU Release smoke results:

| Case | code | excluded | steps | Key result |
| --- | ---: | ---: | ---: | --- |
| hydrostatic | 0 | 0 | 1 | `ExcessPorePress=0`, `DivVel=0`, diagnostic fields present |
| analytical excess | 0 | 0 | 1 | nonzero `LapPorePress` and `PorePressRate`, pressure not advanced |

Selected hydrostatic metrics from `gpu_g2_smoke_summary.csv`:

- `HeadResidual` maxAbs:
  `2.61962477407e-05`
- `PorePressRate` maxAbs:
  `17.464165 Pa/s`
- `PorePress` max:
  `9760.95041752 Pa`

Selected analytical-excess metrics:

- `ExcessPorePress` max:
  `999.874127674 Pa`
- `LapPorePress` maxAbs:
  `960240.12`
- `PorePressRate` maxAbs:
  `15945362 Pa/s`

CPU reference runs were also executed from the same smoke XMLs. They are useful
for sign and field-order checks, but they are not strict one-step parity because
the CPU path applies the active `dt_pore` restriction and advances pressure for
210 substeps over the same output window, while G2 deliberately does not update
`PorePressg`.

## Generated Output Cleanup

Generated `_out` directories are not part of the intended commit. The retained
artifacts are the XML/BAT smoke templates, the analysis script, and the summary
CSV.

## G3 Readiness

G2 satisfies the requested diagnostic-only gate:

- passive `PorePressg` from G1 remains intact;
- PR diagnostic arrays are lifecycle-safe;
- sorting and periodic duplicate paths are covered;
- output fields are present and finite;
- GPU Release smoke passed with `code=0` and `excluded=0`.

The next phase may be planned as G3 only if explicitly requested. Its scope
should be limited to `PorePressg` update and `dt_pore` parity. G3 should still
exclude feedback, Shepard regularization, hydromechanical damping, production
boundary ghost logic, softening, and long GPU runs.
