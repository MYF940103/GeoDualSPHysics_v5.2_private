# Notes: Retrogressive Slope

## Current Purpose

`CaseRetrogressiveSlope_PR_ReducedSmoke_Def.xml` is a reduced CPU smoke case for
the u-pw PR implementation. It verifies that a small 3D slope-like wedge can be
generated, advanced briefly under body gravity, and saved with pore-pressure
diagnostic fields.

It is not a strict reproduction of the paper's retrogressive landslide.

## Current Setup

- Narrow 3D wedge geometry with coarse `dp=0.02 m`.
- Body gravity and hydraulic gravity are both `(0,0,-9.81)`.
- Soil constants are written in `<execution><special><soils>`.
- `PorePressureInit=1` with a fully saturated reduced water level.
- `PorePressureModel=1` and `SavePorePressure=1`.
- `PorePressureFeedback=0` in this first reduced smoke to isolate geometry,
  stress, and PR diagnostic output.

## Missing Before Meaningful Reproduction

- Sensitive clay / strain-softening model or calibrated remolding law.
- Initial slope stress state and pore-pressure state consistent with the paper.
- Production hydraulic boundary treatment for sloped/lateral boundaries.
- Coupled feedback stability at slope scale.
- GPU implementation for meaningful resolution and runtime.
- Postprocessing for retrogression distance, failure surface, plastic strain,
  velocity, and pore pressure.

## Readiness Decision

The reduced smoke is runnable and can serve as a CPU pre-GPU case-readiness
check. Strict retrogressive behavior remains deferred until the material model,
boundary treatment, and GPU path are ready.
