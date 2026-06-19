# Stage1 hydraulic-conductivity comparison conclusions

Date: 2026-06-18

This note preserves the conclusions from the temporary root-level
`k_stage1_test` directory before that output directory was removed.

## Setup

- Particle mode: FrDraw sphere
- `dp = 0.003 m`
- `q0 = 10000 Pa`
- `HydroMechDrainage = 0`
- `HydroMechTopLoadMode = SphereNormal`
- Area-normalized external load was active
- `TimeMax = 0.006 s`
- `TimeOut = 0.003 s`
- Compared hydraulic conductivity:
  - `k = 0`
  - `k = 1e-8 m/s`

## Result at `t ~= 0.006 s`

- center-nearest pore pressure, `k=0`: `3144 Pa` (`0.314 q0`)
- center-nearest pore pressure, `k=1e-8`: `3162 Pa` (`0.316 q0`)
- core mean pore pressure for `r <= 0.006 m`, `k=0`: `4741 Pa`
- core mean pore pressure for `r <= 0.006 m`, `k=1e-8`: `4740 Pa`
- surface mean pore pressure, `k=0`: `16636 Pa`
- surface mean pore pressure, `k=1e-8`: `16628 Pa`

The radial-bin mean differences were only a few Pa in the interior and about
`-8 Pa` on the surface, compared with pore pressures of several thousand Pa.

## Interpretation

Using a tiny non-zero hydraulic conductivity (`1e-8 m/s`) did not materially
improve the Stage1 pore-pressure distribution.

This argues against `k=0` itself being the main reason for the low center pore
pressure. The stronger hypotheses remain:

- the spherical external load is not physically equivalent to the reference
  problem's quasi-static uniform boundary traction;
- the volumetric particle distribution, especially the FrDraw shell-like
  interior, produces an uneven compression field and delayed center response;
- the problem is a 3D spherical transient loading/equilibration issue, not a
  failure of the u-pw governing equation already verified in the 1D and
  landslide cases.
