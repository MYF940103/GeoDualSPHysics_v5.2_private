# GPU S1 BodyGravityStopTime Medium Smoke

This directory contains medium-length GPU Release smoke cases for the Scenario 1 single-run route.

The cases use `BodyGravityStopTime=0.002`, keep `HydraulicGravity=(0,0,-9.81)`, and keep the default production hydraulic boundary path `PorePressureBoundaryOperator=0`.

Runs:

- `T0p05`: `TimeMax=0.05`, `TimeOut=0.002`
- `T0p20`: `TimeMax=0.2`, `TimeOut=0.01`, run only if `T0p05` is stable

Generated heavy outputs are removed after analysis. The committed artifacts are XML/BAT files, scripts, CSV summaries, and figures.
