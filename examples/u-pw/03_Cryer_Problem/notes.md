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

## C3-B Strict Route Notes

C3-B has selected the strict route over the reduced manual-run route.

Reference:

- The clean center-pressure formula was recovered from the local PDF image for
  Equations (46)-(47).
- It still needs an independent C4 reference script and comparison against
  Figure 7B or trusted digitized data.

Geometry:

- First strict route should be a true 3D sphere.
- Axisymmetric/2D variants remain reduced surrogates unless a matching
  analytical reference is supplied.

Loading:

- Cryer requires all-around inward normal traction `p0`.
- Existing AccInput/top-load style routes are not equivalent to this spherical
  traction.
- Native spherical traction support is not yet proven.

Boundary:

- Mode `0` remains production default for reduced workflows but is not strict
  curved drained boundary treatment.
- Mode `1` is GPU-supported experimental.
- Mode `2` is CPU-only experimental and is the closest current boundary-
  particle-aware candidate, but it should not be ported before a Cryer-specific
  CPU result justifies it.

Next recommended step:

- C4-A: implement and validate the independent Cryer reference script.

## E1 Constitutive Note

Strict Cryer must use the new linear elastic skeleton switch:

```xml
<SoilConstitutiveModel value="0" />
```

This bypasses Drucker-Prager yield, return mapping, `Kplastic` accumulation,
and softening. The reduced baseline may remain on the default Drucker-Prager
path, but any analytical Cryer comparison should explicitly use model `0`.

## C4-A Reference Script Notes

`strict_reproduction_plan/cryer_reference_solution.py` now implements the
PDF-transcribed Cryer center-pressure series.

Default run:

```powershell
py strict_reproduction_plan\cryer_reference_solution.py --make-plot
```

Default outputs:

- reference curves for `nu=0.1`, `0.2`, `0.3`, `0.45`;
- roots and root residual diagnostics;
- root-truncation convergence;
- peak pressure and peak `T_v` metrics;
- self-check JSON;
- SVG/PNG/PDF reference plots.

Observed reference behavior:

- all four curves show nonmonotonic Mandel-Cryer peaks;
- lower Poisson ratio gives stronger overshoot;
- all curves decay toward zero by long dimensionless time.

Validation limitation:

- no digitized Figure 7B data is available yet, so the reference remains a
  checked implementation candidate rather than a fully verified paper-plot
  reproduction.

## C4-B Loading Audit Notes

C4-B checked whether existing native mechanisms can impose the strict Cryer
load: uniform all-around inward normal traction `p0` on a spherical exterior.

Findings:

- `AccInput` works for reduced top-layer / marker acceleration cases, but it is
  not a pressure traction because it has no per-particle radial normal or
  surface-area weighting.
- Floating-body `linearforce` and `angularforce` are total rigid-body inputs,
  not deformable-material surface traction on the poroelastic sphere.
- Existing prescribed motion routes can compress a body kinematically, but do
  not reproduce the traction boundary condition.
- mDBC/cDBC boundary normals are useful infrastructure, but there is no current
  XML path that maps `p0` to `F_i=-p0 A_i n_i`.

Strict Cryer simulation remains paused. The original C4-B idea of a CPU-first
area-weighted radial/spherical traction block has been superseded by C4-B2.

## C4-B2 Revised Loading Route

C4-B2 rejects the `AccInput` patchwise spherical surrogate. `AccInput` remains
useful for reduced marker-acceleration workflows, but it cannot be promoted to a
strict Cryer pressure boundary because it does not apply a continuous
all-around normal traction `p0`.

The strict loading route is now the flexible confining stress method described
for triaxial simulations in the drained/undrained SPH framework paper. The
future source term should add an isotropic confining stress
`sigma_conf = -p0 I` to the conservative mechanical momentum summation. Interior
contributions should cancel by kernel symmetry; exterior particles should feel
an inward pressure because their kernel support is truncated at the free
surface.

This route has not been implemented yet. The next task should be CPU-first
C4-B3 implementation with diagnostics:

- net confining force vector;
- center-of-mass acceleration;
- surface radial acceleration sign;
- interior cancellation;
- symmetry residual;
- compression-induced pore-pressure sign check.

The drained curved pore-pressure boundary remains separate, and strict Cryer
simulation is still paused.
