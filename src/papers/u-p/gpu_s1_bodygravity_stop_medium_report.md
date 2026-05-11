# GPU S1 BodyGravityStopTime medium smoke

## Objective

This stage extends the S1-1b short smoke to GPU medium windows using the single-run `BodyGravityStopTime` route. It checks whether the gravity stop, top-drained activation, bottom no-flux projection, and coupled pore-pressure feedback remain stable after the switch.

## S1-1b Recap

S1-1b added GPU support for `BodyGravityStopTime`. The short GPU/CPU parity smoke passed with `code=0`, `excluded=0`, and final CPU/GPU `PorePress` and `ExcessPorePress` max-absolute differences of about `0.00394 Pa`.

## Setup

- `PorePressureBoundaryOperator=0`
- `BodyGravityStopTime=0.002`
- `PorePressureTopDrained=1`
- `PorePressureTopDrainedStartTime=0.002`
- `PorePressureBottomNoFlux=1`
- `Gravity=(0,0,-9.81)`
- `HydraulicGravity=(0,0,-9.81)`
- `HydromechDampingXi=0.05`
- `PorePressureFeedback=1`, mode `1`, operator `1`
- `PorePressureShepard=1`, interval `10`, mode `1`
- `PorePressureDtSafety=0.20`
- `SavePorePressure=1`

CPU 0.05 s reference was not run in this stage. The S1-1b 0.005 s CPU reference already passed, while the observed CPU runtime for 0.005 s was about 122 s, so a 0.05 s CPU reference was projected to be too costly for this GPU-medium sanity step.

## GPU Medium Results

| run | code | excluded | steps | runtime_s | frames | gravity stop log | final Excess maxAbs [Pa] | final bottom excess [Pa] | final top excess maxAbs [Pa] | final bottom no-flux proxy [Pa] | final max velocity [m/s] | final/peak excess |
|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---:|
| T0p05 | 0 | 0 | 52437 | 123.984268 | 26 | True | 84.084 | -84.0068 | 2.01457e-07 | 0.00101205 | 4.3073e-05 | 0.00368587 |
| T0p20 | 0 | 0 | 209747 | 490.911163 | 21 | True | 27.3597 | -27.3506 | 7.34182e-09 | 3.06824e-05 | 5.59964e-06 | 0.00225952 |

## Stability Checks

- Mechanical gravity stop was detected in the GPU log for every completed medium run.
- Hydraulic gravity remained active in the same log diagnostic.
- Top-drained excess stayed near zero after activation.
- Bottom no-flux proxy stayed finite and small relative to the pore-pressure scale.
- Velocity did not show a switch-induced spike; the post-switch velocity envelope remained bounded.
- `ExcessPorePress` decayed from the early peak over the completed medium windows.

## CPU Reference / Parity

No new CPU medium reference was run. The parity basis for this stage is the S1-1b CPU/GPU short smoke at `TimeMax=0.005 s`, which remained aligned after the GPU `BodyGravityStopTime` patch. This medium stage is therefore a GPU stability gate, not a fresh CPU/GPU parity benchmark.

## Recommendation

The 0.2 s GPU medium smoke also passed, so Scenario 1 GPU long-run preparation may start next, still using the BodyGravityStopTime single-run route and not the restart route.

The restart route remains deferred.

## Artifacts

- XML/BAT, scripts, CSV metrics, and figures: `examples/u-pw/02_SelfWeight_Consolidation/experiments/GPU_S1_BodyGravityStopMedium/`
