# GPU S1 BodyGravityStopTime Long Run

This directory contains the Scenario 1 single-run `BodyGravityStopTime` GPU Release long run.

The case keeps the production hydraulic boundary path:

- `PorePressureBoundaryOperator=0`
- `BodyGravityStopTime=0.002`
- `PorePressureTopDrainedStartTime=0.002`
- `PorePressureBottomNoFlux=1`
- `HydraulicGravity=(0,0,-9.81)` remains active
- `HydromechDampingXi=0.05`
- `PorePressureShepard=1`, interval `10`, mode `1`
- `PorePressureFeedback=1`, mode `1`, operator `1`
- `TimeMax=3.6`, `TimeOut=0.1`

Generated heavy outputs are removed after analysis. The committed artifacts are XML/BAT files, this script, CSV summaries, figures, and the report in `src/papers/u-p/`.
