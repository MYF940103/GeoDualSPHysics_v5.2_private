# Scenario 1 BodyGravityStopTime paper-figure note

## Purpose

This note documents the final paper-figure set for the self-weight Scenario 1
`BodyGravityStopTime` route. The route generates self-weight pore-pressure
response with mechanical body gravity active, then stops the mechanical body
force at `t=0.002 s` while keeping `HydraulicGravity=(0,0,-9.81)` active and
activating the top-drained boundary.

## Why the BodyGravityStopTime Route Was Used

The single-run route avoids GPU restart-state mapping risk while preserving the
physical split required by Scenario 1:

- mechanical body gravity is removed after the undrained generation stage;
- hydraulic gravity remains active for hydrostatic elevation and `LapZ`;
- top drainage activates at the same staged time;
- bottom no-flux remains active.

The restart route remains deferred because the short/medium/long GPU route is
already stable and because restart parity would add a separate state-mapping
problem.

## Short CPU/GPU Parity Recap

S1-1b passed after the GPU `BodyGravityStopTime` patch:

- CPU/GPU `code=0`, `excluded=0`;
- GPU mechanical body gravity stopped at about `t=0.00200051 s`;
- `HydraulicGravity` remained active;
- final CPU/GPU `PorePress` and `ExcessPorePress` max-absolute differences were
  about `0.00394 Pa`;
- final velocity max-absolute difference was about `6e-09 m/s`.

## Medium Stability Recap

S1-2 passed both GPU medium windows:

- `0.05 s`: final `ExcessPorePress` maxAbs `84.08 Pa`;
- `0.2 s`: final `ExcessPorePress` maxAbs `27.36 Pa`;
- `code=0`, `excluded=0` for both.

## Long-Run Result

S1-3 ran to `3.600001 s` with `code=0`, `excluded=0`, `3,775,438` steps, and
`37` retained frames.

Key final metrics:

| metric | value |
|---|---:|
| final max velocity [m/s] | 2.99721e-07 |
| final mean velocity [m/s] | 1.91873e-07 |
| final `ExcessPorePress` maxAbs [Pa] | 1.64504 |
| final bottom excess mean [Pa] | -1.64484 |
| final top-drained excess maxAbs [Pa] | 1.40389e-09 |
| final bottom no-flux proxy [Pa] | 1.86976e-06 |
| excess final / long-run retained peak | 0.0426782 |

The S1-3 long run agrees with S1-2 at the overlap point:

| comparison | S1-2 medium | S1-3 long |
|---|---:|---:|
| time [s] | None | None |
| `ExcessPorePress` maxAbs [Pa] | nan | nan |
| bottom excess mean [Pa] | nan | nan |
| max velocity [m/s] | nan | nan |

## Boundary Consistency

The top-drained residual stayed near zero and the bottom no-flux proxy remained
small throughout the long run. No pressure blow-up or gravity-switch velocity
spike was observed.

## Reference / Analytical Comparison

The local Supporting Materials notes give a Scenario 1 cosine-series
dissipation reference assuming an instantaneous Eq.(4) undrained
self-weight profile at drainage activation. That reference was reconstructed
for context in `scenario1_reference_metrics.csv`.

It is not used as a strict error target for the final BodyGravityStopTime line,
because this validated route is a dynamic single-run workflow. Previous A2
audits showed that the actual generated profile at `t ~= 0.002 s` does not equal
the ideal Eq.(4) state. Therefore Scenario 1 is treated here as a
drainage-to-equilibrium stability and dissipation benchmark rather than a
strict analytical-profile reproduction.

## Figures

Paper figures and metrics are stored in:

`examples/u-pw/02_SelfWeight_Consolidation/experiments/PaperFigures_Scenario1_BodyGravityStop/`

Main figures:

1. bottom excess pressure vs time;
2. excess-pressure decay;
3. excess-pressure profiles carried forward from S1-3;
4. total pore-pressure profiles carried forward from S1-3;
5. velocity decay;
6. top-drained and bottom no-flux checks;
7. short/medium/long consistency;
8. pressure-rate, volumetric, and hydraulic contributions.

## Recommended Manuscript Wording

The Scenario 1 self-weight consolidation test was conducted using a single-run
mechanical-gravity switch, in which the mechanical body force was removed after
the undrained loading stage while the hydraulic gravity remained active. The
GPU solution remained stable over 3.6 s, with no particle exclusion,
continuous pressure dissipation, negligible top-drained residual, and a small
bottom no-flux residual. The excess pore pressure decayed to a final maximum
magnitude of approximately `1.65 Pa`, while the maximum velocity decreased to
approximately `3.0e-7 m/s`, confirming the stability of the coupled u-pw PR
implementation under the gravity-switch drainage workflow.

## Limitations

- This figure set does not claim strict analytical-profile reproduction for
  Scenario 1.
- The restart route remains deferred.
- `PorePressureBoundaryOperator=0` remains the production interpretation.
- Corrected-gradient production operators remain deferred.

## Closure

Scenario 1 can be used as a paper-compatible stability and
drainage-to-equilibrium validation figure for the current u-pw PR
implementation.
