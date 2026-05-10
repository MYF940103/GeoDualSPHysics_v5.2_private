# Notes: Retrogressive Slope

## Current Purpose

`CaseRetrogressiveSlope_PR_ReducedSmoke_Def.xml` is a reduced CPU smoke case for
the u-pw PR implementation. It verifies that a small 3D slope-like wedge can be
generated, advanced briefly under body gravity, and saved with pore-pressure
diagnostic fields.

It is not a strict reproduction of the paper's retrogressive landslide.

The current case is reduced execution smoke only. It should not be promoted to
strict reproduction status until sensitive clay / strain softening,
remolding/destructuration, initial stress and pore-pressure construction,
production hydraulic boundaries, and large-deformation validation are addressed
or explicitly deferred.

## Current Setup

- Narrow 3D wedge geometry with coarse `dp=0.02 m`.
- Body gravity and hydraulic gravity are both `(0,0,-9.81)`.
- Soil constants are written in `<execution><special><soils>`.
- `PorePressureInit=1` with a fully saturated reduced water level.
- `PorePressureModel=1` and `SavePorePressure=1`.
- `PorePressureFeedback=0` in this first reduced smoke to isolate geometry,
  stress, and PR diagnostic output.

## Paper Parameters Extracted From Main PDF

The paper studies two sensitive-clay slopes:

- 5 m high, 45 degree slope, base length 25 m, top length 20 m, `Delta=0.1 m`,
  11,275 particles.
- 8 m high slope, base length 17 m, top length 16 m, `Delta=0.1 m`, 8,470
  particles.

Material / hydraulic parameters:

- `E=25 MPa`, `nu=0.3`;
- mixture density `2150 kg/m3`, water density `1000 kg/m3`;
- porosity `0.4`;
- `Kw=0.2 GPa`;
- `k=1e-8 m/s`;
- peak cohesion `15.1 kPa`, residual cohesion `1.5 kPa`;
- internal friction and dilatancy `0 deg`;
- softening coefficient `5`;
- initial stress with `K0=0.5`, gravity loading using peak strength and
  `eta=0`, then cohesion strength reduction factor `1.65`.

## Missing Before Meaningful Reproduction

- Sensitive clay / strain-softening model or calibrated remolding law.
- Initial slope stress state and pore-pressure state consistent with the paper.
- Production hydraulic boundary treatment for sloped/lateral boundaries.
- Coupled feedback stability at slope scale.
- GPU implementation for meaningful resolution and runtime.
- Postprocessing for retrogression distance, failure surface, plastic strain,
  velocity, and pore pressure.

## Readiness Decision

The reduced smoke is runnable and can serve as a health check for the current
PR field plumbing. It does not satisfy the full CPU strict reproduction gate.
Strict retrogressive behavior remains deferred until the material model,
boundary treatment, initial-state workflow, and GPU path are ready or formally
deferred.

`analyze_slope_smoke.py` provides the current reduced-smoke postprocessing
path. It reports displacement and velocity magnitudes, pore-pressure ranges,
and `Kplastic` ranges. This is a smoke-health metric only; it is not a
retrogression-distance or failure-surface analysis.
