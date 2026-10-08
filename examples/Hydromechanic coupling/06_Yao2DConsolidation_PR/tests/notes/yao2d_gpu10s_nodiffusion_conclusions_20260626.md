# Yao 2025 2D Consolidation GPU 10 s No-Diffusion Run

Date: 2026-06-26

## Case

Output directory:

- `CaseYao2DConsolidation_PR_gpu10s_dp01_damp002_nodiffusion_out`

Formal run entry:

- `../xCaseYao2DConsolidation_PR_win64_GPU.bat`

This run is the 10 s baseline without density/stress diffusion and without pore-pressure Shepard regularization.

Confirmed runtime settings:

- `DensityDiffusion="None"`
- `DensityDT=0`
- `PoreShepardRegularization="Disabled"`
- `PoreShepardRegularization=0`
- `TimeMax=10`
- `TimeOut=0.05`
- `HydroMechTopLoadMode="TopStripVertical"`
- Yao strip footprint: `x=[-3,3] m`
- `HydroMechTopLoadQ0=5000 Pa`
- `HydroMechTopLoadRampTime=0.1 s`
- `SoilDampingCoef=0.02`
- `SlipMode=1`
- `PeriodicActive="None"`

## Completion

The GPU run completed successfully.

Run summary:

- Physical time: `10.000020 s`
- Saved part files: `201`
- Steps: `500001`
- Boundary particles: `1644`
- Fluid particles: `20301`
- Total particles: `21945`

VTK output:

- `PartBound_0000.vtk` to `PartBound_0200.vtk`
- `PartFluid_0000.vtk` to `PartFluid_0200.vtk`

## Boundary Symmetry Check At t = 10 s

Checked from:

- `particles/PartBound_0200.vtk`
- field: `PorePress`

Mirror mapping:

- left boundary point `(x, z)`
- right boundary target `(-x, z)`

Result:

- Mirror pairs: `396`
- Missing mirror pairs: `0`
- Maximum left-right pore-pressure difference: `0.00360107421875 Pa`
- Mean left-right pore-pressure difference: `0.000905581194945056 Pa`

The boundary pore-pressure mapping remains symmetric to near output precision.

## A/B Normalized EPWP Measurement

Point coordinates are taken from Fig. 26:

- A: `(2, 8)`
- B: `(8, 2)`

Because the full model is centered at `x=0`, these are directly sampled in the current full-domain coordinate system.

The measured quantity is normalized excess pore water pressure:

- `EPWP / q0`
- `q0 = 5000 Pa`
- `EPWP = ExcessPorePress`

Sampling:

- A sampled particle id: `13844`, initial location `(2, 8)`, target distance `0 m`
- B sampled particle id: `19844`, initial location `(8, 2)`, target distance `0 m`

Output files:

- `figures/yao2d_ab_normalized_epwp.csv`
- `figures/yao2d_ab_normalized_epwp.png`
- `figures/yao2d_ab_epwp_kpa.png`

Summary:

- A maximum `EPWP/q0 = 0.54983232421875` at `t = 0.15 s`
- A final `EPWP/q0 = 0.12712493896484375` at `t = 10 s`
- B maximum `EPWP/q0 = 0.3379040283203125` at `t = 0.15 s`
- B final `EPWP/q0 = 0.175529931640625` at `t = 10 s`

The A point rises faster and dissipates below the B point after approximately mid-time, matching the expected difference between the shallower loaded-zone point and the deeper/right-side point.

## Follow-Up Comparison Matrix

The next comparison runs should use this no-diffusion case as the baseline:

1. `DensityDT=0`, `PoreShepardRegularization=0`:
   current baseline.
2. Stress/density diffusion enabled, `PoreShepardRegularization=0`:
   isolates the diffusion effect.
3. Stress/density diffusion disabled or enabled, `PoreShepardRegularization=1`:
   isolates the pore-pressure Shepard regularization effect.

Each run should repeat:

- output count check,
- final boundary mirror check,
- A/B `EPWP/q0` time-history extraction.

