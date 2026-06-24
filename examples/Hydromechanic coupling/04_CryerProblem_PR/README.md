# CryerProblem_PR

This case validates the u-pw pore-pressure-rate formulation on Cryer's problem: a saturated poroelastic sphere with a drained exterior surface and a uniform inward normal pressure.

The active verification path uses `HydroMechInitMode=0` (`None`), `HydroMechTopLoadMode=2` (`FlexibleConfinement`) for the sustained confining pressure, and `HydroMechDrainage=1` to drain tracked exterior free-surface particles. The direct uniform pore-pressure initialization path is not used because it was not paired with a consistent 3D effective-stress and displacement initialization.

The formal release case is now a one-stage drained calculation. The older undrained-then-drained restart path was abandoned for the release configuration. The case applies `FlexibleConfinement` from `t=0`, keeps the exterior free surface drained from `t=0`, and compares the center pore-pressure history directly against Cryer's analytical sequence.

The retained validation record for the selected release settings is `refinement/notes/k1e5_dp0025_full_20260622.md`. The formal XML uses:

- `dp=0.0025`
- `k=1e-5 m/s`
- `HydroMechTopLoadMode=2` (`FlexibleConfinement`)
- `HydroMechTopLoadRampTime=0`
- `HydroMechDrainage=1`
- `HydroMechDrainageStartTime=0`
- `TimeMax=0.910928571429 s`, corresponding to `T_v=1`
- `TimeOut=0.000910928571429 s`, corresponding to `Delta T_v=0.001`

The first nonzero output is therefore `T_v=0.001`. Earlier values are not retained in the formal run because the high-resolution refinement tests showed strong startup oscillation below this range.

The batch files also pass `CRYER_TV_MIN=0.001` to the postprocessor, so generated CSV, figures, and summary metrics exclude any solver-saved initial `t=0` state.

Run on Windows GPU release:

```bat
xCaseCryerProblem_PR_win64_GPU.bat
```

## High-resolution closed-ramp Poisson sweep

An additional high-resolution release-candidate sweep is prepared for the four
Poisson-ratio groups. These files keep the same `k=1e-5` and damping settings
as the retained validation runs, but use:

- `dp=0.002`
- `HydroMechTopLoadRampTime=0.0025 s`
- `HydroMechDrainage=1`
- `HydroMechDrainageStartTime=0.0025 s`
- postprocess time origin `CRYER_TL=0.0025 s`
- center sampling radius `r <= 1dp = 0.002 m`

The solver `TimeMax` in each XML/batch is `0.0025 s + T_v=1` for that
Poisson ratio. `TimeOut` remains `Delta T_v=0.001`.

Run the four GPU batches:

```bat
xCaseCryerProblem_PR_dp002_rampclosed_nu010_win64_GPU.bat
xCaseCryerProblem_PR_dp002_rampclosed_nu020_win64_GPU.bat
xCaseCryerProblem_PR_dp002_rampclosed_nu030_win64_GPU.bat
xCaseCryerProblem_PR_dp002_rampclosed_nu045_win64_GPU.bat
```

Formal outputs are kept under one directory:

- `CaseCryerProblem_PR_out/data`
- `CaseCryerProblem_PR_out/particles`
- `CaseCryerProblem_PR_out/figures`

The PartVTK command in both bat files requests:

```text
+idp,+mk,+vel,+rhop,+press,+sigma_kk,+sigma_ij,+kplastic,+fstype,+fsnormal,+porepress,+porepress0,+excessporepress,+hydromechloadace
```

Open `CaseCryerProblem_PR_out/particles/PartFluid_*.vtk` in ParaView and inspect `FSType`, `FSNormal`, `PorePress`, and `HydroMechLoadAce`.

Expected postprocess outputs:

- `CaseCryerProblem_PR_out/figures/cryer_center_pressure_dp0025_k1e5.png`
- `CaseCryerProblem_PR_out/figures/cryer_center_pressure_dp0025_k1e5.csv`
- `CaseCryerProblem_PR_out/figures/cryer_center_pressure_dp0025_k1e5_summary.json`

The geometry includes a tiny fixed boundary block far outside the kernel support of the sphere. It is only a solver guard for code paths that expect at least one boundary particle and does not interact with the poroelastic sphere.

Exploratory tests are documented under `refinement/notes/`. Bulky temporary
outputs are intentionally not retained in the release case directory.
