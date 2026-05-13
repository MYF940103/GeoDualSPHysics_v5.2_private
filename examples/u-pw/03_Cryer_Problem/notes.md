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

## C5h Higher-Resolution Sphere Notes

C5h adds one more CPU-only sphere resolution after C5g:

- `dp=0.010`: `739` material particles;
- `dp=0.008`: `1213` material particles;
- `dp=0.0065`: `2601` material particles.

Retained package:

`strict_reproduction_plan/C5h_HigherResolutionSphere/`

Both C5h CPU Release cases completed with `code=0`, `excluded=0`, and
`Kplastic=0`.

Observations:

- center peak decreases from `7.448 p0` to `7.058 p0` to `6.731 p0`;
- center particle counts improve, but center averaging does not converge
  cleanly;
- the generated `dp=0.0065` surface is not smoother than `dp=0.008`;
- compression surface p95 worsens to `244.34 Pa`;
- pressure-only diffusion worsens, with final surface p95 `1023.40 Pa` and
  pressure-rate maxAbs about `1.55e6 Pa/s`.

Decision: simple dp refinement is not a clean path forward. The next strict
Cryer task should focus on MLS / flux-consistent drained spherical boundary
calibration, using pressure-only diffusion as the first acceptance gate. C6 and
GPU remain deferred.

## C5i Spherical Diffusion Flux Calibration Notes

C5i establishes the pressure-only spherical diffusion gate:

`strict_reproduction_plan/C5i_SphericalDiffusionFluxCalibration/`

It is postprocessing-only. It reads committed pressure-only diffusion CSVs from
C5e/C5f/C5g/C5h and solves a matching 1D finite-volume radial diffusion
reference. No source files were changed, no GPU run was performed, and no new
Cryer compression case was run.

Reference setup:

- `R=0.05 m`;
- `u0=1000 Pa`;
- `c_v=0.0067957866 m2/s`;
- drained boundary `u(R)=0`;
- symmetry `du/dr=0` at `r=0`.

At `t~0.00603 s`, the FV reference has center pressure `~999.998 Pa`, volume
mean `~615.7 Pa`, and surface-shell mean `~85.9 Pa`. The normalized mode-4 SPH
cases drain the center much too early while leaving the near-surface shell too
pressurized. Their median apparent flux ratios are about `1.63`, `2.26`, and
`2.18` for `dp=0.010`, `0.008`, and `0.0065`, respectively; the highest
resolution also shows a late flux reversal.

Decision:

- mode 3 is weak/under-drained;
- raw mode 4 is over-drained;
- normalized mode 4 is over-strong and nonuniform, not a true Dirichlet
  boundary;
- further dp refinement should pause;
- C6 remains blocked;
- next source task should be a CPU-only MLS / flux-consistent drained
  spherical boundary prototype with integrated flux diagnostics;
- GPU remains deferred.

## C5j MLS Boundary Flux Notes

C5j adds the first CPU-only source prototype for the C5i recommendation:

`strict_reproduction_plan/C5j_MLSBoundaryFlux/`

Source scope:

- added `CurvedDrainedBoundaryMode=5`;
- added MLS/flux diagnostics parameters;
- kept mode `0` to mode `4` behavior unchanged;
- kept the PR governing equation, `FlexibleConfiningStress`,
  `SoilConstitutiveModel`, and `HydraulicElevationSource` unchanged;
- did not add GPU support.

Mode `5` is a shell-averaged radial MLS flux correction. It fits a constrained
radial linear profile to nearby material samples using the physical spherical
surface value `p_b=0`, then converts the integrated normal flux to a
`LapPorePress` correction over the near-surface shell. It does not clamp
material pressure and does not volume-count selected dummy boundary particles.

Pressure-only CPU Release results:

- `dp=0.008`: `code=0`, `excluded=0`, `Kplastic=0`, median flux ratio
  `2.220`, final flux ratio `4.101`;
- `dp=0.010`: `code=0`, `excluded=0`, `Kplastic=0`, median flux ratio
  `1.494`, final flux ratio `4.029`;
- MLS fallback count was zero in both runs.

The shell-average correction removes the tested mode-5 flux reversal and
negative-pressure overdrain. It improves center/volume RMSE compared with the
retained mode-4 normalized rows. However, it does not pass the pressure-only
gate because the `0.95R-1.0R` surface shell remains far too pressurized and
late-time flux remains too strong.

Decision:

- no Cryer compression smoke was run;
- C6 remains blocked;
- further dp refinement remains deferred;
- the next source task should add radial shell/FV flux matching or a transfer
  law that constrains volume decay, surface-shell pressure, and center pressure
  together;
- GPU remains deferred.

## C5k Radial-Shell Flux Boundary Notes

C5k adds the radial shell/FV flux prototype:

`strict_reproduction_plan/C5k_RadialShellFluxBoundary/`

Source scope:

- added `CurvedDrainedBoundaryMode=6`;
- kept mode `0` to mode `5` behavior unchanged;
- kept the PR governing equation, `FlexibleConfiningStress`,
  `SoilConstitutiveModel`, and `HydraulicElevationSource` unchanged;
- did not add GPU support.

Mode `6` computes the outer radial shell mean pressure and mean radius,
estimates the spherical drained flux against `p_b=0`, and applies the
integrated `4*pi*R^2*q_R` loss as a `LapPorePress` correction over the same
outer material shell. It does not clamp material pressure and does not
volume-count dummy boundary particles.

Pressure-only CPU Release results:

- `dp=0.008`: `code=0`, `excluded=0`, `Kplastic=0`, median flux ratio
  `1.907`, final flux ratio `-14.20`, final shell mean `873.84 Pa`;
- `dp=0.010`: `code=0`, `excluded=0`, `Kplastic=0`, median flux ratio
  `1.078`, final flux ratio `0.784`, final shell mean `577.06 Pa`.

The coarse `dp=0.010` case improves center RMSE and median flux ratio, but the
surface shell remains much too pressurized. The finer `dp=0.008` case develops
late apparent flux reversal and a large pressure-rate artifact.

Decision:

- no Cryer compression smoke was run;
- C6 remains blocked;
- further dp refinement remains deferred;
- the next source task should couple the boundary flux with near-boundary
  radial redistribution and interior Laplacian consistency;
- GPU remains deferred.

## C5l Radial Operator Audit Notes

C5l is a no-source-change postprocessing audit:

`strict_reproduction_plan/C5l_RadialOperatorAudit/`

It reconstructs the static sphere clouds and applies the CPU material-material
`LapPorePress` formula to radial manufactured fields. It also checks retained
C5i/C5j/C5k pressure-only diffusion outputs with radial shell storage balance.

Manufactured-field findings:

- constant field residual is exactly zero;
- `u=r^2` gives good interior Laplacian behavior;
- near-boundary quadratic p95 error is large and non-convergent:
  `12.24`, `14.06`, `17.08` for `dp=0.010`, `0.008`, `0.0065`;
- the drained-like `R-r` field has the same boundary-shell failure pattern.

Shell-exchange findings:

- normalized shell residual p95 is worst for mode `6` `dp=0.008` and mode `4`
  `dp=0.0065`;
- mode `6` `dp=0.010` can get median flux ratio close to `1`, but the surface
  shell remains far above the FV reference because shell-to-shell exchange is
  inconsistent.

Decision:

- C6 remains blocked;
- GPU remains deferred;
- next source task should be C5m conservative multi-shell radial exchange,
  with pressure-only FV radial diffusion as the acceptance gate.

## C5m Conservative Shell Exchange Notes

C5m adds the conservative multi-shell radial exchange prototype:

`strict_reproduction_plan/C5m_ConservativeShellExchange/`

Source scope:

- added `CurvedDrainedBoundaryMode=7`;
- kept mode `0` to mode `6` behavior unchanged;
- kept the PR governing equation, `FlexibleConfiningStress`,
  `SoilConstitutiveModel`, and `HydraulicElevationSource` unchanged;
- did not add GPU support.

Mode `7` partitions the sphere into radial shells, computes FV interface
fluxes, and applies a shell-average correction to `LapPorePress` so shell
storage changes match `F_in-F_out`. The C5m gate used
`CurvedDrainedShellCorrectionMode=1`, not a material pressure clamp.

Pressure-only CPU Release results:

- `dp=0.008`: `code=0`, `excluded=0`, `Kplastic=0`, median flux ratio
  `1.927`, final flux ratio `-19.36`, final shell mean `969.08 Pa`;
- `dp=0.010`: `code=0`, `excluded=0`, `Kplastic=0`, median flux ratio
  `1.929`, final flux ratio `2.31`, final shell mean `381.88 Pa`.

The shell storage residual is essentially zero by construction, which confirms
the conservative correction is active. The pressure-only gate still fails:
`dp=0.010` improves surface-shell RMSE but damages center/volume behavior, and
`dp=0.008` develops late flux reversal and a strong pressure-rate artifact.

Decision:

- no Cryer compression smoke was run;
- C6 remains blocked;
- GPU remains deferred;
- next source task should be a corrected near-boundary SPH Laplacian /
  consistency operator, with C5m shell balance retained as a diagnostic.

## C5n Corrected Laplacian Notes

C5n adds the corrected near-boundary Laplacian prototype:

`strict_reproduction_plan/C5n_CorrectedLaplacian/`

Source scope:

- added `CurvedDrainedBoundaryMode=8`;
- kept mode `0` to mode `7` behavior unchanged;
- kept the PR governing equation, `FlexibleConfiningStress`,
  `SoilConstitutiveModel`, and `HydraulicElevationSource` unchanged;
- did not add GPU support.

Mode `8` uses a local quadratic MLS fit near the spherical drained boundary:

`nabla^2 p = 2(a_xx+a_yy+a_zz)`

The fit includes material samples and spherical Dirichlet samples. For the
pressure-only Cryer gate, `p_b=0`. It replaces near-boundary `LapPorePress`,
not material `PorePress`.

Static manufactured audit:

- constant field remains zero-residual;
- `u=r^2` near-boundary p95 error at `dp=0.008` drops from `13.81` to roundoff
  when exact manufactured boundary values are supplied;
- drained-like `R-r` p95 error drops from `121.32` to `5.23`;
- fallback count is zero for the dp=0.008 reconstructed cloud.

Pressure-only CPU Release result:

- `dp=0.008`: `code=0`, `excluded=0`, `Kplastic=0`;
- final center pressure `47.38 Pa`, FV `999.998 Pa`;
- final volume mean `232.26 Pa`, FV `615.76 Pa`;
- final surface shell mean `431.67 Pa`, FV `85.88 Pa`;
- negative pressure and apparent flux reversal occurred;
- final `PorePressRate` maxAbs was `9.37e6 Pa/s`.

Decision:

- no Cryer compression smoke was run;
- C6 remains blocked;
- GPU remains deferred;
- next work should be a stabilization/limiting gate for the corrected
  Laplacian rather than another shell bookkeeping or scalar flux correction.

## C5o Corrected Laplacian Stabilization Notes

C5o adds limiter controls inside the existing corrected Laplacian mode:

`strict_reproduction_plan/C5o_CorrectedLaplacianStabilization/`

Source scope:

- kept `CurvedDrainedBoundaryMode=8`;
- added `CurvedDrainedCorrectedLaplacianLimiter`;
- added `CurvedDrainedLimiterCFL`, `CurvedDrainedLimiterBlend`, and
  `CurvedDrainedLimiterPreventNegative`;
- kept mode `0` to mode `7`, the PR governing equation,
  `FlexibleConfiningStress`, `SoilConstitutiveModel`, and
  `HydraulicElevationSource` unchanged;
- did not add GPU support.

Pressure-only CPU Release result:

- limiter cases: positivity, blend `0.25`, blend `0.50`, blend `0.50` plus
  positivity;
- all cases: `code=0`, `excluded=0`, `Kplastic=0`;
- blend `0.25` was best for center pressure (`center RMSE=104.83 Pa`) and
  reduced final `PorePressRate` maxAbs to `2.62e6 Pa/s`;
- surface shell remained far too high (`1038.91 Pa` for blend `0.25` versus
  FV `85.88 Pa`);
- all limiter cases still had apparent flux reversal;
- negative pressure was reduced but not eliminated.

Decision:

- pressure-only FV gate still failed;
- no Cryer compression smoke was run;
- C6 remains blocked;
- GPU remains deferred;
- local limiter/blend tuning should not be promoted as the next strict Cryer
  path. Either pause the strict route in this SPH boundary-operator family or
  redesign the drained sphere as a true dynamic boundary value problem.

## C5p Strict Route Freeze Notes

C5p freezes the current strict Cryer route and synthesizes the no-go decision.
It is documentation-only: no source, GenCase, CPU/GPU run, or PartVTK step was
performed.

The evidence chain is now clear:

- geometry refinement lowered the center peak only modestly and did not fix the
  surface residual;
- boundary-particle normalization improved raw over-drain but remained
  nonuniform and too strong;
- the FV pressure-only reference showed that current mode `4` is not a clean
  Dirichlet condition;
- mode `5`, mode `6`, and mode `7` proved that local flux and shell
  bookkeeping fixes are insufficient;
- mode `8` proved that static polynomial consistency can be recovered, but the
  dynamic pressure-only gate over-drains and reverses flux;
- C5o limiters reduced some artifacts but did not produce the FV radial
  pressure profile.

Decision:

- strict Cryer reproduction is deferred;
- C6 remains blocked and should not be started;
- the current Cryer case should not be cited as a validation figure;
- useful components are retained: linear elastic skeleton, flexible confining
  stress, no-elevation pressure mode, analytical reference, FV radial diffusion
  gate, and boundary diagnostics;
- do not continue local Cryer boundary patching unless the route is redesigned
  as a true dynamic drained-boundary value problem;
- GPU remains deferred.

Next benchmark recommendation: start T1 undrained triaxial baseline first.
Use L2 external-load 1D full reproduction only if the immediate goal shifts
back to consolidation parameter validation.

## C5q Interface Cleanup Notes

C5q audits the interface surface left by the Cryer strict-route work. It does
not delete source or experiment directories and does not run GenCase, CPU/GPU,
or PartVTK.

Classification:

- keep stable: `SoilConstitutiveModel`, `HydraulicElevationSource`,
  `HydraulicGravityX/Y/Z`, `FlexibleConfiningStress`, and `ConfiningStress*`;
- keep experimental: `PorePressureBoundaryOperator=1/2/3`,
  `PorePressureCurvedDrained`, common curved geometry/value parameters,
  `CurvedDrainedBoundaryMode=0/1/4`, and
  `CurvedDrainedBoundaryWeighting=0/1`;
- deprecate/archive: diagnostic clamp mode `2`, quadrature mode `3`, modes
  `5/6/7/8`, mode-5 MLS parameters, mode-7 shell parameters, mode-8 corrected
  Laplacian parameters, and C5o limiter parameters;
- delete now: none.

The selected cleanup strategy is conservative: document deprecation and keep
source unchanged before T1. The failed modes remain readable for archived C5
evidence, but they are not recommended for new cases.
