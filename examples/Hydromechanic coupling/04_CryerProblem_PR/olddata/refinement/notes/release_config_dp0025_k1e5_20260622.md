# Formal Cryer release configuration, dp=0.0025 and k=1e-5

Date: 2026-06-22

## Active release files in case root

- `CaseCryerProblem_PR_Def.xml`
- `xCaseCryerProblem_PR_win64_GPU.bat`
- `xCaseCryerProblem_PR_win64_CPU.bat`
- `README.md`

The older two-stage XML files were moved out of the case root to:

- `refinement/archived_two_stage_20260622/CaseCryerProblem_PR_Stage1_Def.xml`
- `refinement/archived_two_stage_20260622/CaseCryerProblem_PR_Stage2_Def.xml`

## Selected release settings

- One-stage drained calculation, no restart.
- `setfrdrawmode auto="true"` sphere generation.
- `dp=0.0025`.
- `HydraulicConductivity=1e-5 m/s`.
- `HydroMechInitMode=0`.
- `HydroMechTopLoadMode=3` (`FlexibleConfinement`).
- `HydroMechTopLoadRampTime=0`.
- `HydroMechDrainage=1`.
- `HydroMechDrainageStartTime=0`.
- `SoilDampingCoef=0.02`.
- `DtFixed=5e-6 s`.
- `TimeMax=0.910928571429 s`, corresponding to `T_v=1`.
- `TimeOut=0.000910928571429 s`, corresponding to `Delta T_v=0.001`.

This writes 1000 nonzero-time output intervals for the formal full-period run. The initial `t=0` particle state may also be present depending on solver output behavior; it should not be used for analytical error metrics.

The formal batch files set `CRYER_TV_MIN=0.001`, so postprocessed CSV, figures, and summary metrics skip any saved state below `T_v=0.001`.

## Validation performed locally

Only GenCase was run locally to check XML syntax and geometry generation. DualSPHysics was not launched on this machine for the full release run.

GenCase completed successfully with:

- `Dp=0.0025`.
- `37173` fluid particles.
- `8` fixed dummy boundary particles outside the sphere support.

The temporary GenCase check output was removed after validation.

## Expected output location

The batch files write all formal run outputs under:

- `CaseCryerProblem_PR_out/data`
- `CaseCryerProblem_PR_out/particles`
- `CaseCryerProblem_PR_out/figures`

PartVTK outputs include:

`+idp,+mk,+vel,+rhop,+press,+sigma_kk,+sigma_ij,+kplastic,+fstype,+fsnormal,+porepress,+porepress0,+excessporepress,+hydromechloadace`
