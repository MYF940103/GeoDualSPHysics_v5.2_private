# Notes: Self-Weight Consolidation

## Scenario 2: gravity maintained

Current runnable draft settings:

- body Gravity = `(0,0,-9.81)`
- HydraulicGravity = `(0,0,-9.81)`
- `PorePressureInit=1`
- `PorePressureFeedback=1`
- `PorePressureFeedbackMode=1`
- `PorePressureFeedbackOperator=1`
- `PorePressureTopDrained=1`
- `PorePressureTopDrainedStartTime=0.002`
- `PorePressureBottomNoFlux=1`
- `HydromechDampingXi=0.10`
- `PorePressureShepard=1`
- `PorePressureShepardInterval=10`
- `PorePressureDtSafety=0.20`

Expected qualitative trend: excess pore pressure decays and total pore pressure tends toward hydrostatic.

## Scenario 1: gravity switched off

Required missing feature:

- `PorePress` restart, or
- runtime body gravity switch such as `BodyGravityStopTime`.

After undrained self-weight generation, the second stage should run with body Gravity = `(0,0,0)` while `HydraulicGravity=(0,0,-9.81)` remains active and top drained is enabled.
