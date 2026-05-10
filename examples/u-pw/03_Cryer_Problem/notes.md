# Notes: Cryer Problem

## Status

This directory has a Cryer-like strict/minimal CPU smoke case plus a
strict-reproduction TODO placeholder. The smoke case verifies that the current
u-pw PR fields, mechanics, and near-center pore-pressure postprocessing can run
in a Cryer-labeled scaffold without crashing.

The current smoke is not strict Cryer analytical reproduction. The strict Cryer path still
requires paper geometry, a drained curved boundary, pore-pressure ghost / MLS or
an equivalent boundary treatment, and center-pressure analytical
postprocessing. These gaps remain strict-reproduction blockers unless
explicitly deferred.

## Parameters

The converted main-paper text confirms that Cryer uses the same elastic and
material constants as the one-dimensional Terzaghi consolidation simulation,
except for a Poisson-ratio sweep. The reduced smoke currently uses the standard
1D consolidation material constants:

- `E = 2e6 Pa`
- `nu = 0.3`
- `Porosity0 = 0.3`
- `HydraulicConductivity = 1e-3 m/s`
- `WaterBulkModulus = 2e8 Pa`
- `WaterDensity = 1000 kg/m3`

Unknown strict Cryer parameters remain TODO:

- selected sphere radius / exact geometry scaling for the GeoDualSPHysics XML;
- drained exterior boundary implementation;
- analytical center-pressure normalization;
- strict boundary operator choice.

Known strict Cryer features from the paper:

- poroelastic sphere;
- drained exterior surface;
- uniform all-around normal traction `p0`;
- normalized center pressure `p_w(r=0)/p0`;
- Poisson ratios `0.1`, `0.2`, `0.3`, `0.45`;
- Mandel-Cryer nonmonotonic center pressure response.

## Boundary Approximation

The reduced smoke reuses the current layer-style hydraulic boundary tools. This
is acceptable for smoke only. It is not a strict drained spherical Cryer boundary.
Boundary ghost and corrected-gradient diagnostics are not promoted to production
operators.

## Smoke Readiness

Latest smoke status is recorded in `smoke_status.md`.

The smoke postprocessing helper `analyze_cryer_smoke.py` reads `PartCsv_*.csv`
files and writes `cryer_smoke_center_pressure.csv`. It reports a nearest-to-
centroid pore-pressure history as a center-pressure proxy. This is only a smoke
metric; it is not the analytical Cryer center pressure comparison.
