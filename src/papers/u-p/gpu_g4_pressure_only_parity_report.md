# GPU G4 Pressure-Only Boundary Parity Report

Date: 2026-05-11

## Scope

GPU Phase G4 adds the pressure-only hydraulic boundary corrections required for
1D consolidation parity:

- top drained layer correction;
- bottom no-flux layer correction.

This phase still excludes GPU feedback, `PorePressureAccelDiff`, Shepard,
hydromechanical damping, boundary ghost production operators, softening, and
long GPU reproduction runs.

## Modified Source Files

- `source/JSphGpu.h`
- `source/JSphGpu.cpp`
- `source/JSphGpuSingle.cpp`
- `source/JSphGpu_ker.h`
- `source/JSphGpu_ker.cu`

## Top Drained Correction

The GPU path now mirrors the CPU layer correction:

```text
z_h = -dot(pos, HydraulicGravityUnit)
zmax = max(z_h over material particles)
drain_thickness = PorePressureDrainThickness > 0 ? PorePressureDrainThickness : KernelH

if TimeStep >= PorePressureTopDrainedStartTime
and z_h >= zmax - drain_thickness:
    PorePress = hydrostatic(z_h)
```

The correction is applied at initialization and after each accepted pressure
update.

## Bottom No-Flux Correction

The GPU path computes:

```text
zmin = min(z_h over material particles)
bottom layer:    z_h <= zmin + thickness
reference layer: zmin + thickness < z_h <= zmin + 2*thickness

mean_ref = mean(PorePress - hydrostatic(z_h) in reference layer)

for bottom layer:
    PorePress = hydrostatic(z_h) + mean_ref
```

The first version uses GPU kernels plus float reductions for:

- material `zmax`;
- material `zmin`;
- reference excess sum;
- reference count;
- affected-particle counts.

Only a few scalar reduction results are copied back to the host for control and
logging.

## Ordering

G4 uses the pressure-only ordering:

```text
ComputeHydroPrDiagnosticsGpu
DtVariable with dt_pore
UpdatePorePressureGpu
ApplyPorePressureTopDrainedGpu
ApplyPorePressureBottomNoFluxGpu
```

Shepard regularization is not implemented on GPU in this phase, so the CPU
`update -> Shepard -> top drained -> bottom no-flux` ordering reduces here to:

```text
update -> top drained -> bottom no-flux
```

## Smoke Cases

Smoke files are in:

`examples/u-pw/01_1D_Consolidation/experiments/GPU_G4_PressureOnlyParity/`

Retained files:

- `Case1DConsolidation_PR_GPU_G4_StaticBoundary_Def.xml`
- `Case1DConsolidation_PR_GPU_G4_Diffusion_Def.xml`
- `xCase1DConsolidation_PR_GPU_G4_StaticBoundary_win64_GPU_debug.bat`
- `xCase1DConsolidation_PR_GPU_G4_Diffusion_win64_GPU_debug.bat`
- `analyze_gpu_g4.py`
- `gpu_g4_smoke_summary.csv`

Generated `_out` directories were removed after extracting the summary.

## Build Results

- GPU Debug build: passed.
- GPU Release build: passed.

GPU Release was used for the smoke runs.

## Smoke Results

| Case | Mode | code | excluded | steps |
| --- | --- | ---: | ---: | ---: |
| static boundary | GPU Release | 0 | 0 | 1 |
| static boundary | CPU Release reference | 0 | 0 | 1 |
| diffusion micro | GPU Release | 0 | 0 | 5 |
| diffusion micro | CPU Release reference | 0 | 0 | 5 |

Boundary metrics from the final frames:

| Case | top maxAbs excess [Pa] | bottom-minus-reference maxAbs [Pa] |
| --- | ---: | ---: |
| GPU static boundary | 0 | 3.95e-08 |
| CPU static boundary | 0 | 1.01e-08 |
| GPU diffusion micro | 0 | 1.60e-01 |
| CPU diffusion micro | 0 | 1.60e-01 |

CPU/GPU final-frame pressure differences:

| Case | maxAbs PorePress difference [Pa] | mean PorePress difference [Pa] |
| --- | ---: | ---: |
| static boundary | 6.10e-05 | 1.11e-06 |
| diffusion micro | 2.10e-05 | 4.44e-06 |

The diffusion micro run shows excess-pressure decay:

```text
GPU final maxAbs(ExcessPorePress) = 998.252 Pa
Initial sine-profile maxAbs(ExcessPorePress) was about 999.874 Pa
```

## G4 Assessment

G4 passes the pressure-only hydraulic boundary smoke tests. The top drained
layer is enforced, the bottom layer tracks the reference excess mean, and
CPU/GPU pressure-state parity is within roundoff-level pressure differences for
these micro tests.

## Next Phase Boundary

G5 may implement `PorePressureAccelDiff` feedback as a separately scoped phase.
G5 must not silently expand into Shepard, damping, boundary ghost production,
softening, or long coupled GPU runs.
