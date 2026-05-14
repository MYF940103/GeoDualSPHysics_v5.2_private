# L4 GPU Long-Run Value And Limits

Date: 2026-05-14

## Objective

L4 would extend the L3c consistent initial-state pressure gate into a longer
GPU validation run. This note defines what L4 can and cannot prove.

## What L4 Can Validate

L4 can validate the Level-1 PR diffusion and hydraulic-boundary route:

- long-term GPU pressure update stability for `PorePressureInit=3`;
- top drained boundary behavior over a longer Terzaghi time window;
- bottom and lateral no-flux behavior over a longer decay path;
- analytical dissipation trend in profiles and bottom pressure;
- CPU/GPU parity for the selected initial-state gate;
- absence of late-time drift, NaN/Inf, or unexpected pressure growth;
- robustness of existing output and postprocessing for paper-compatible
  pressure figures.

Because L3c already has CPU/GPU parity over the short/medium gate, L4 is a low
risk way to turn the current pressure-gate evidence into a stronger validation
figure.

## What L4 Cannot Validate

L4 cannot validate:

- top surcharge mechanical load generation;
- force-controlled plate or true surface traction behavior;
- total/effective stress consistency under a mechanical loading process;
- full hydromechanical feedback;
- quasi-static mechanical consolidation loading path;
- damping/viscosity choices for a dynamic mechanical load route.

The L4 setup still uses the initial pressure field directly:

```text
p_w0 = |q0| = 10 kPa
MechanicalTopLoad = 0
AccInput disabled
PorePressureFeedback = 0
```

That is correct for the Level-1 Terzaghi initial-value gate, but it bypasses
the Level-2 loading-generation stage.

## Why L4 Is Still Worth Doing

L4 is still worth doing because it is the cleanest next validation step:

- it needs no source changes;
- it uses a route already supported on CPU and GPU;
- it targets the part of the formulation that currently has a clean analytical
  reference;
- it can produce a paper-compatible PR diffusion and boundary figure;
- it does not depend on the unresolved mechanical top-load design.

L4 should therefore be framed as foundational validation, not as the final
strict 1D consolidation reproduction.

## Recommended L4 Scope

Recommended L4 scope:

- reuse the L3c XML and analysis structure;
- run a longer CPU/GPU pair if runtime is acceptable;
- compare profiles at multiple Terzaghi time factors;
- compare bottom excess pressure and volume-mean decay;
- report top drained residual and bottom no-flux proxy;
- keep `PorePressureFeedback=0`;
- keep mechanical loading disabled.

No damping or viscosity sweep should be added to L4. That would mix the clean
diffusion gate with the separate mechanical loading problem.

## Decision

L4 is recommended as the next step when the project needs the most stable and
useful immediate validation. It is a Level-1 strict diffusion/boundary gate. It
is not strict full mechanical consolidation reproduction.
