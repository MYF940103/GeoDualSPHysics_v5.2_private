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

## C4-B3 Flexible Confining Stress Implementation Notes

C4-B3 adds a CPU-only implementation of the flexible confining stress route.
The new parameters live under `<execution><special><soils>`:

```xml
<FlexibleConfiningStress value="1" />
<ConfiningStressP0 value="50" />
<ConfiningStressRampStart value="0" />
<ConfiningStressRampEnd value="0" />
<ConfiningStressTargetMk value="0" />
<ConfiningStressMode value="0" />
```

Default is `FlexibleConfiningStress=0`, so existing cases are unchanged.
Positive `ConfiningStressP0` is external compression. In the current SPH
stress-divergence sign convention, the implementation adds a positive
isotropic stress-like contribution to the CPU pairwise mechanical momentum
summation. It is not stored in the material stress tensor and it does not alter
`PorePress`, `PorePressRate`, `LapPorePress`, `LapZ`, or `HydraulicGravity`.

GPU is unsupported for this feature in C4-B3. A GPU run with the switch enabled
throws a hard error.

The C4-B3 smoke folder is:

`strict_reproduction_plan/flexible_confining_stress_C4B3/`

The no-load, sign, and ramp smokes all completed with `code=0` and `excluded=0`.
Loaded runs produced inward surface radial velocity and force symmetry
residuals of order `1e-08`. These are loading-source sanity checks only, not
Cryer validation.

## C4-B4 Free-Sphere Flexible Confining Stress Smoke

C4-B4 retained a small CPU-only free-sphere smoke under:

`strict_reproduction_plan/flexible_confining_stress_C4B4_FreeSphere/`

Geometry and run scope:

- free 3D sphere, `R=0.05 m`, `dp=0.01 m`, `739` material particles;
- `SoilConstitutiveModel=0`;
- no-load regression plus ramped `FlexibleConfiningStress` with `p0=50 Pa`;
- CPU Release only;
- no GPU and no strict Cryer comparison.

Results:

- no-load: `code=0`, `excluded=0`;
- ramp: `code=0`, `excluded=0`;
- final surface radial velocity mean `=-6.28e-04 m/s`;
- final surface radial displacement mean `=-1.09e-06 m`;
- final net/absolute force `=1.94e-08`;
- final COM acceleration estimate `=2.08e-08 m/s2`;
- compression increased center and mean excess pore pressure relative to the
  no-load baseline;
- `Kplastic=0`.

This supports the flexible confining stress source as the CPU traction
candidate. The drained curved pore-pressure boundary remains the next blocker,
GPU support remains unsupported, and strict Cryer simulation remains paused.

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

## C4-C Drained Curved Boundary Notes

C4-C adds a CPU-only experimental drained curved hydraulic boundary:

```xml
<parameter key="PorePressureBoundaryOperator" value="3" />
<parameter key="PorePressureCurvedDrained" value="1" />
<parameter key="CurvedDrainedBoundaryCenterX" value="0" />
<parameter key="CurvedDrainedBoundaryCenterY" value="0" />
<parameter key="CurvedDrainedBoundaryCenterZ" value="0" />
<parameter key="CurvedDrainedBoundaryRadius" value="0.05" />
<parameter key="CurvedDrainedBoundaryTargetMk" value="0" />
<parameter key="CurvedDrainedBoundaryValue" value="0" />
<parameter key="CurvedDrainedBoundaryUseExcess" value="1" />
<parameter key="CurvedDrainedBoundaryThickness" value="0.018" />
<parameter key="CurvedDrainedBoundaryMode" value="0" />
```

Mode `3` is a spherical Dirichlet ghost prototype. It contributes to
`LapPorePress` and `LapZ` before the PR pressure rate is computed. It does not
overwrite `PorePress` after the update.

Smoke folder:

`strict_reproduction_plan/drained_curved_boundary_C4C/`

Results:

- zero/no-source smoke: `code=0`, `excluded=0`;
- pressure-only diffusion smoke: `code=0`, `excluded=0`;
- compression plus drained boundary smoke: `code=0`, `excluded=0`;
- diffusion surface excess decreased during the short run;
- compression produced early positive center excess and `Kplastic=0`.

GPU remains unsupported for mode `3` and hard-errors if requested. The
prototype is sufficient for a future coarse CPU strict-Cryer smoke, but not for
claiming strict Figure 7 reproduction.

## C4-D Hydraulic No-Elevation Notes

C4-D adds `HydraulicElevationSource`:

- `1` default: legacy hydrostatic/elevation behavior;
- `0`: CPU-only gravity-free Cryer convention. `HydraulicGravity` remains
  positive only for `k/(rho_w*g_h)` scaling, while hydrostatic reference is zero
  and `k*LapZ` is omitted from `PorePressRate`.

The retained smoke package is:

`strict_reproduction_plan/hydraulic_no_elevation_C4D/`

Results:

- source-on regression: `code=0`, `excluded=0`;
- no-elevation pressure diffusion: `code=0`, `excluded=0`;
- no-elevation compression plus curved drainage: `code=0`, `excluded=0`,
  `Kplastic=0`.

GPU remains unsupported for `HydraulicElevationSource=0` and hard-errors during
XML loading. The next step can be C5 coarse CPU strict-sphere smoke combining
linear elasticity, flexible confining stress, curved drained boundary, and
no-elevation hydraulics.

## C5 Coarse CPU Strict-Sphere Notes

C5 retained a short coarse sphere run:

`strict_reproduction_plan/C5_StrictSphere_CoarseSmoke/`

Result:

- `code=0`, `excluded=0`;
- particles: `739`;
- `SoilConstitutiveModel=0`, `Kplastic=0`;
- `FlexibleConfiningStress=1`, `p0=50 Pa`;
- `PorePressureBoundaryOperator=3`, curved drained ghost active;
- `HydraulicElevationSource=0`, so `LapZ` is not used in `PorePressRate`;
- averaged center pressure peak: `383.6 Pa` (`7.67 p0`) at `t=0.002011 s`;
- final retained averaged center pressure: `146.2 Pa` (`2.92 p0`) at
  `t=0.006032 s`.

The response is qualitative only. Longer exploratory windows showed coarse
free-sphere oscillation and out-check risk, so C5 is not sufficient for strict
Figure 7B validation. Recommended next step: C5b geometry/time-window
refinement before C6 quantitative comparison.

## C5b Strict-Sphere Refinement Notes

C5b kept the same coarse sphere and tested only targeted changes:

- slower loading ramp;
- lower `p0` for linearity;
- a longer slow-ramp window;
- center averaging radii from `0.1R` to `0.4R`.

Short baseline, slow-ramp, and lower-p0 cases all completed with `code=0`,
`excluded=0`, and `Kplastic=0`. The long slow-ramp case was not accepted:
particle exclusion began near `t=0.025 s` and ended at `425` excluded
particles.

Key conclusions:

- lower `p0` scales almost exactly with the baseline, so the high normalized
  response is not a load-magnitude nonlinearity;
- slower ramp lowers the early response near `t=0.002 s`, but the pressure
  later rises back to about the same normalized level;
- center averaging reduces the baseline peak from about `8.45 p0` to
  `7.67 p0`, which is meaningful but not decisive;
- near-surface material excess remains high even when the curved ghost
  residual is zero.

The next step should be drained curved boundary/material-surface refinement
before C6 quantitative comparison. GPU remains deferred.

## C5c Curved Boundary Coupling Notes

C5c refined only the CPU curved drained boundary prototype. It did not run GPU
and did not attempt Figure 7B comparison.

New `CurvedDrainedBoundaryMode` meanings for
`PorePressureBoundaryOperator=3`:

- `0`: old first-order spherical drained ghost;
- `1`: strengthened image-style drained ghost;
- `2`: diagnostic material surface clamp, not production.

The old ghost surface residual is systematic. At the final retained frame, the
`r>0.85R` material shell has mean excess `179.37 Pa`, median `178.06 Pa`, p95
absolute excess `218.47 Pa`, and max absolute excess `263.15 Pa`. The previous
zero ghost residual only described the prescribed ghost state, not the material
surface layer.

All C5c CPU Release runs completed with `code=0`, `excluded=0`, and
`Kplastic=0`. The strengthened ghost slightly reduces the compression response
and improves pressure-only diffusion, but it does not fix the high center
pressure. The diagnostic clamp proves surface drainage is influential, but it
is too intrusive and creates pressure-rate artifacts.

Recommended next step: improve the mode-3 boundary quadrature / multi-sample
Dirichlet coupling before dp refinement or C6 quantitative comparison. GPU
remains deferred.

## C5d Boundary Quadrature Notes

C5d adds `CurvedDrainedBoundaryMode=3` for
`PorePressureBoundaryOperator=3`. It is CPU-only and experimental.

The mode creates five spherical drained Dirichlet samples per near-surface
material particle and contributes them to the hydraulic operator. It is not a
material clamp and it does not change the PR pressure equation.

Results from `strict_reproduction_plan/C5d_BoundaryQuadrature/`:

- all old/strong/quadrature/clamp compression tests completed with `code=0`,
  `excluded=0`, and `Kplastic=0`;
- all pressure-only diffusion comparison tests completed with `code=0`,
  `excluded=0`, and `Kplastic=0`;
- quadrature reduced the final `r>0.85R` surface p95 excess from `218.47 Pa`
  to `208.90 Pa`;
- quadrature reduced the center peak only from `7.672 p0` to `7.657 p0`;
- pressure-only diffusion was more active than old ghost but not better than
  the strengthened ghost in the short test window;
- the diagnostic clamp remains the upper-bound proof that surface drainage is
  important, but it is still not a valid production method.

Decision: C5d is stable but insufficient. C6 quantitative comparison remains
premature. The next step should be a stronger, more physically normalized
boundary quadrature/MLS treatment or a narrowly scoped geometry refinement
after the boundary rule is improved. GPU remains deferred.

## LIT-B Boundary Literature Notes

LIT-B reviewed the original u-pw paper, Supporting Materials, and the
drained/undrained SPH framework before further Cryer source changes.

Key points:

- Original u-pw paper: pore-pressure Dirichlet boundaries are applied by
  free-surface zero pressure or prescribed dummy/boundary pressure; Neumann
  pore-pressure boundaries use MLS extrapolation to boundary particles.
- Supporting Materials: useful for 1D top-drained/bottom-no-flux self-weight
  references, but they do not provide a Cryer curved-boundary operator.
- Drained/undrained SPH paper: dummy boundary particles carry pore pressure
  extrapolated from soil particles with an Adami-style normalized kernel and
  hydrostatic smoothing term, but that paper is a penalty drained/undrained
  framework rather than transient PR diffusion.

Decision: do not keep tuning current spherical mode-3 ghost/quadrature as the
main path. The next step should design a boundary-particle hydraulic state with
paper-style MLS/Adami extrapolation for the spherical drained Cryer surface.
Only after that should pressure-only spherical diffusion and C5/C6 be revisited.

## C5e Boundary-Particle Drained Boundary Notes

C5e implements `CurvedDrainedBoundaryMode=4` for the CPU-only
`PorePressureBoundaryOperator=3` path. This is the first Cryer boundary attempt
after the LIT-B recommendation to move from material-side spherical samples
toward boundary-particle hydraulic state.

Mode 4:

- selects boundary particles using spherical geometry, optional `mkbound`, and
  `CurvedDrainedBoundarySelectionTolerance`;
- prescribes drained `p_w=0` (`excess=0` under `HydraulicElevationSource=0`);
- adds selected boundary-particle contributions to `LapPorePress` and `LapZ`;
- does not clamp material particles;
- computes Adami-style boundary pressure only as a diagnostic.

Retained tests are in:

`strict_reproduction_plan/C5e_BoundaryParticleDrained/`

All four CPU Release tests completed with `code=0`, `excluded=0`, and
`Kplastic=0`. Compression center peak decreased from `7.657 p0` in the mode-3
control to `6.908 p0` in mode 4, and final `r>0.85R` surface p95 decreased
from `208.90 Pa` to `195.08 Pa`.

The pressure-only diffusion test shows the current boundary-particle volume is
too strong: final center pressure overshot to `-97.17 Pa`, and
`PorePressRate` maxAbs rose to about `9.38e5 Pa/s`. C5e therefore supports the
boundary-particle route conceptually but does not provide a C6-ready boundary.

Next step: MLS/Adami-normalized boundary-particle operator weighting before
dp refinement or C6. GPU remains deferred.

## C5f Boundary-Particle Weighting Notes

C5f keeps the C5e boundary-particle drained boundary but adds
`CurvedDrainedBoundaryWeighting` for `CurvedDrainedBoundaryMode=4`.

Values:

- `0`: raw boundary-particle volume weighting, the C5e behavior;
- `1`: Adami-style local partition normalization;
- `3`: diagnostic missing-support capped weighting.

All C5f CPU Release tests passed with `code=0`, `excluded=0`, and
`Kplastic=0`. The raw mode-4 over-drainage is explained by the selected
boundary shell contributing a large local kernel partition (`mean S_b=2.700`)
relative to the material support (`mean S_m=0.760`). Normalized weighting uses
a mean effective boundary scale of `0.297`.

Observed effects:

- pressure-only raw final center pressure `=-97.17 Pa`;
- pressure-only normalized final center pressure `=529.96 Pa`;
- final pressure-rate maxAbs drops from about `9.38e5 Pa/s` to about
  `3.33e5 Pa/s`;
- compression surface p95 residual improves from `195.08 Pa` to `131.56 Pa`;
- compression center peak remains high at about `7.45 p0`.

C5f is therefore a useful stabilization/diagnostic step, not a final Cryer
boundary. C6 remains paused; dp refinement remains deferred; GPU support for
this strict path remains unsupported.

## C5g Geometry / dp Diagnostic Notes

C5g tests whether the C5f center peak is mainly a coarse-sphere artifact. It
does not change source and does not run GPU.

Retained package:

`strict_reproduction_plan/C5g_GeometryDpDiagnostic/`

Cases:

- coarse compression, `dp=0.010`;
- finer compression, `dp=0.008`;
- coarse pressure-only diffusion, `dp=0.010`;
- finer pressure-only diffusion, `dp=0.008`.

All four CPU Release cases completed with `code=0`, `excluded=0`, and
`Kplastic=0`. The finer sphere increased material particles from `739` to
`1213` and reduced the surface roughness std from `0.00358` to `0.00303`.

Main observations:

- center peak decreased from `7.448 p0` to `7.058 p0`;
- center averaging sensitivity at the peak frame decreased substantially;
- pressure-only diffusion improved, with final center pressure decreasing from
  `529.96 Pa` to `468.25 Pa`;
- compression surface p95 residual did not materially improve (`131.56 Pa` to
  `131.42 Pa`).

Decision: geometry resolution matters, but it is not the main blocker. Do not
move to C6 yet. The next Cryer step should return to MLS / flux-consistent
drained-boundary coupling before a broader dp study.
