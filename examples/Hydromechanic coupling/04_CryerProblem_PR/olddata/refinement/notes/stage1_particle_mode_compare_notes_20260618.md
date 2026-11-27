# Stage1 particle-mode comparison notes

Date: 2026-06-18

This short diagnostic compares `setfrdrawmode` and regular `drawsphere`
particle generation for the Cryer Stage1 loading path. No source code was
changed.

## Setup

- `dp = 0.003 m`
- `R = 0.05 m`
- `q0 = 10000 Pa`
- `HydroMechDrainage = 0`
- `HydroMechTopLoadMode = SphereNormal`
- Area-normalized external load is active
- `SoilDampingCoef = 0.02`
- `TimeMax = 0.006 s`
- `TimeOut = 0.003 s`

## Geometry comparison

FrDraw:

- fluid particles: `22483`
- max radius: about `0.050000 m`
- outer loaded surface particles: `3630`
- equivalent loaded layer thickness: about `1.04 dp`

Regular `drawsphere`:

- fluid particles: `22887`
- max radius: about `0.05439 m`
- particles with `r > 0.05 m`: `3494`
- particles with `r > 0.051 m`: `2302`
- equivalent loaded layer thickness based on the geometric outer shell:
  about `1.48 dp`

Interpretation: FrDraw gives a much cleaner geometric exterior surface, while
regular `drawsphere` creates a thicker and rougher exterior that extends beyond
the intended analytical radius.

## Load diagnostics

FrDraw:

- `N_surface = 3630`
- `R_eff = 0.05`
- `A_sum = 0.0314159`
- residual `|sum(A_i n_i)|/sum(A_i) = 2.75e-4`
- full-load acceleration: `1526.37 m/s2`

Regular `drawsphere`:

- `N_surface = 3392`
- `R_eff = 0.0514711`
- `A_sum = 0.0332918`
- residual `|sum(A_i n_i)|/sum(A_i) = 1.865e-2`
- full-load acceleration: `1731.0 m/s2`

Interpretation: regular `drawsphere` applies a larger total scalar load and has
a much larger resultant imbalance. Its sometimes larger center pore pressure
should not be interpreted as better agreement with the analytical Cryer
problem.

## Stage1 pressure at `t ~= 0.006 s`

FrDraw:

- center-nearest pore pressure: `3144 Pa` (`0.314 q0`)
- core mean pressure, `r <= 0.006 m`: `4741 Pa`
- surface mean pressure: `16636 Pa`
- center velocity magnitude: `2.39e-4 m/s`

Regular `drawsphere`:

- center-nearest pore pressure: `14702 Pa` (`1.47 q0`)
- core mean pressure, `r <= 0.006 m`: `9379 Pa`
- surface mean pressure: `21429 Pa`
- center velocity magnitude: `2.11e-2 m/s`

Interpretation: regular `drawsphere` creates a much stronger dynamic response,
with high surface pressure scatter and large center velocity. FrDraw is
geometrically cleaner and dynamically quieter, but its internal shell-like
particle distribution still delays the pressure response at the center.

## Working conclusion

The Stage1 center-pressure issue is more consistent with a geometry/load-path
problem than with a failure of the u-pw governing equation:

- Cryer's analytical problem assumes a quasi-static all-around normal traction
  on a smooth sphere.
- In the current SPH case the traction is applied as acceleration on a detected
  free-surface particle layer.
- FrDraw improves the boundary traction surface but introduces shell-like
  volumetric layering.
- Regular `drawsphere` improves neither the smooth boundary nor the load
  balance; it only drives a stronger transient response because its effective
  radius and total scalar load are larger.

The next non-code direction should be to improve the particle model itself:
use a regular volumetric interior with a controlled surface layer, or create a
relaxation/pre-processing step that preserves a smooth spherical boundary
without radial shell layering.
