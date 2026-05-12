# Scenario 1/2 GPU visualization launchers

This folder contains lightweight, reproducible GPU launch packages for the frozen self-weight consolidation validation cases.

No full raw output is committed here. Run the BAT files locally when complete particle output is needed for ParaView or reporting.

## Packages

- `Scenario2_G9b_Xi005/`
  - Production Scenario 2 self-weight consolidation, `xi=0.05`, `TimeMax=3.6 s`.
  - Uses `PorePressureBoundaryOperator=0`, the frozen production boundary mode.
  - Run: `xS2_G9b_VIS_T36_win64_GPU_release.bat`

- `Scenario1_BodyGravityStop/`
  - Production Scenario 1 BodyGravityStopTime single-run workflow, `TimeMax=3.6 s`.
  - Mechanical body gravity stops at `t=0.002 s`; `HydraulicGravity` remains active.
  - Uses `PorePressureBoundaryOperator=0`, the frozen production boundary mode.
  - Run: `xS1_BGStop_VIS_T36_win64_GPU_release.bat`

## What the BAT files do

Each BAT follows the normal example workflow:

1. Run `GenCase`.
2. Run GPU DualSPHysics Release with `-sv:csv,binx`.
3. Run `PartVTK` for all fluid/material particle frames with u-pw diagnostic fields.

The generated output folders are intentionally ignored from this committed package and can be regenerated locally.

## Notes

- This package does not reproduce a top-load / upper-particle external-load route.
- The current validated production route uses Scenario 2 self-weight loading and Scenario 1 `BodyGravityStopTime`.
- Restart workflow, boundary mode 1/2 production use, corrected-gradient production, and top-load cases remain deferred.
