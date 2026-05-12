# Notes: Cryer Problem

## Status

This directory has a Cryer-like strict/minimal CPU smoke case plus a
strict-reproduction TODO placeholder. It now also has an example-style
baseline launch workflow (`CaseCryer_PR_Baseline_Def.xml` plus CPU/GPU Release
BATs) for manual reruns. The smoke case verifies that the current u-pw PR
fields, mechanics, and near-center pore-pressure postprocessing can run in a
Cryer-labeled scaffold without crashing.

The current smoke is not strict Cryer analytical reproduction. The strict Cryer path still
requires paper geometry, a drained curved boundary, pore-pressure ghost / MLS or
an equivalent boundary treatment, and center-pressure analytical
postprocessing. These gaps remain strict-reproduction blockers unless
explicitly deferred.

The C1-revised baseline workflow was prepared only; it was not run. It uses
production `PorePressureBoundaryOperator=0` and should be treated as a reduced
workflow for future manual CPU/GPU reruns, not as a validation result.

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

## C2 Audit Summary

C2 was a reference, geometry, boundary, and postprocessing audit only. It did
not run GenCase, DualSPHysics, GPU, CPU, or PartVTK.

Findings:

- The strict paper benchmark is a poroelastic sphere with a drained exterior
  surface and uniform all-around traction `p0`.
- The paper compares normalized center pressure `p_w(r=0,t)/p0` against a
  Mandel-Cryer analytical solution for `nu=0.1`, `0.2`, `0.3`, and `0.45`.
- Current Cryer XMLs are reduced rectangular/column-style workflows, not strict
  spheres.
- Current baseline and smoke XMLs do not apply all-around traction.
- Current hydraulic boundary controls are reduced top/bottom layer controls,
  not a strict drained curved exterior boundary.
- `analyze_cryer_smoke.py` remains a smoke helper, not a strict center-pressure
  comparison.

Recommended C3 choices:

- C3-A: prepare reduced-workflow center-pressure extraction, still no strict
  reproduction claim.
- C3-B: recover the clean analytical reference and build strict sphere/traction
  geometry before deciding on boundary source changes.
