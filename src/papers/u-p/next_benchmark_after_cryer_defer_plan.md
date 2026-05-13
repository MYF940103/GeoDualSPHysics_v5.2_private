# Next Benchmark After Cryer Defer Plan

Date: 2026-05-13

## Decision Context

The strict Cryer route is deferred because the pressure-only spherical drained
diffusion gate failed across local ghost, boundary-particle, MLS flux,
radial-shell flux, conservative shell exchange, corrected Laplacian, and
limiter variants.

The blocker is specific to a curved drained spherical PR diffusion boundary.
It does not invalidate the broader u-pw implementation, the linear elastic
skeleton switch, or the CPU loading infrastructure.

## Recommended Route: T1 Undrained Triaxial Baseline

The next benchmark should be an undrained triaxial baseline.

Rationale:

- it validates stress path, pore-pressure response, and constitutive behavior;
- it does not require a spherical drained diffusion boundary;
- it can reuse the `SoilConstitutiveModel` switch;
- it can exercise external/confining loading infrastructure without Cryer
  surface-drain artifacts;
- it is a cleaner bridge toward constitutive validation before slope cases.

Initial T1 scope:

- one baseline case first, not a broad parameter sweep;
- CPU setup and smoke before any GPU parity work;
- track `p`, `q`, pore pressure, volumetric response, and `Kplastic`;
- compare linear elastic and the existing Drucker-Prager route only if the
  baseline setup is stable;
- document boundary and loading assumptions before attempting paper-level
  reproduction.

Acceptance gate:

- `code=0`, `excluded=0`;
- no NaN/Inf;
- clear pore-pressure response under undrained loading;
- expected stress-path direction;
- `Kplastic=0` for the linear elastic run and sensible activation for plastic
  runs if attempted.

## Secondary Route: L2 External-Load 1D Full Reproduction

The next-best route is an external-load 1D full reproduction extending the
existing L1 baseline.

Rationale:

- it continues consolidation validation with a simpler boundary topology;
- it can refine paper parameters and postprocessing;
- it avoids the Cryer spherical drained boundary blocker.

Initial L2 scope:

- use the established external-load route;
- avoid a full artificial-viscosity/damping sweep at first;
- compare pressure and settlement/consolidation trends against the intended
  paper setup;
- keep the case CPU-first.

## Deferred Route: Retrogressive Slope

Retrogressive slope work should wait until stress-path and constitutive
baselines are cleaner. It involves more geometry, material, softening, and
failure-progression uncertainty than T1 or L2.

## Recommendation

Proceed next with T1: undrained triaxial baseline. Keep L2 as the fallback if
the immediate priority shifts back to consolidation parameter validation.
