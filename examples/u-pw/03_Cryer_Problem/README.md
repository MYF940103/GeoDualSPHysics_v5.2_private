# 03 Cryer Problem

Reduced launch workflow and CPU smoke scaffold for the PR-formulation Cryer benchmark.

This directory now contains a runnable **Cryer-like strict/minimal smoke** case.
It is not a strict Cryer reproduction because the exact paper geometry/radius
and particle-consistent drained curved boundary treatment are still TODO.

It also contains an example-style **baseline launch workflow** for manual CPU/GPU
Release reruns. This workflow is intended to make Cryer setup exploration
reproducible before strict analytical reproduction is attempted.

## Files

- `CaseCryer_PR_Smoke_Def.xml`: reduced 2D column-style smoke using u-pw PR settings.
- `xCaseCryer_PR_Smoke_win64_CPU_debug.bat`: CPU Debug smoke runner.
- `CaseCryer_PR_Baseline_Def.xml`: reduced Cryer baseline launch XML using production `PorePressureBoundaryOperator=0`.
- `xCaseCryer_PR_Baseline_win64_CPU_release.bat`: example-style CPU Release workflow.
- `xCaseCryer_PR_Baseline_win64_GPU_release.bat`: example-style GPU Release workflow.
- `analyze_cryer_smoke.py`: near-center pore-pressure history helper.
- `cryer_smoke_center_pressure.csv`: latest smoke postprocessing summary.
- `CaseCryer_PR_TODO_Def.xml`: historical strict-reproduction placeholder.
- `smoke_status.md`: latest reduced smoke result.

## Current Status

- Cryer-like strict/minimal smoke is CPU runnable.
- Latest smoke: GenCase `code=0`, DualSPHysics `code=0`, `excluded=0`.
- Key pore-pressure fields are written.
- No NaN/Inf was detected in the generated `PartCsv_*.csv` files.
- The analysis helper reports a bounded near-center pore-pressure proxy.
- Baseline CPU/GPU Release BATs are prepared but were not run in C1-revised.
- Strict Cryer reproduction is still feature-blocked.

## Baseline Launch Workflow

The new baseline BATs follow the normal example pattern:

`GenCase -> DualSPHysics Release -> PartVTK`

CPU:

```bat
xCaseCryer_PR_Baseline_win64_CPU_release.bat
```

GPU:

```bat
xCaseCryer_PR_Baseline_win64_GPU_release.bat
```

The BATs generate complete raw output folders and complete fluid/material
particle VTK output for visualization. They do not run Python analysis, extract
selected frames, generate previews, or create metadata packages.

The baseline uses:

- `HydromechCoupling=1`
- `PorePressureModel=1`
- `SavePorePressure=1`
- `PorePressureBoundaryOperator=0`
- `PorePressureFeedback=1`
- `PorePressureFeedbackMode=1`
- `PorePressureFeedbackOperator=1`
- `PorePressureShepard=1`
- `PorePressureShepardInterval=10`
- `PorePressureShepardMode=1`
- `PorePressureDtSafety=0.20`

This remains a reduced workflow. It should not be cited as strict Cryer
analytical reproduction.

## Strict Reproduction Reclassification

This Cryer-like smoke must not be counted as strict Cryer reproduction complete.
It does not yet include the paper Cryer geometry, a drained spherical/curved
pore-pressure boundary, boundary ghost / MLS pressure reconstruction, or center
pore-pressure analytical postprocessing. Under the full CPU pre-GPU gate, Cryer
still blocks full strict reproduction until these gaps are implemented or
explicitly deferred.

## Missing Before Strict Cryer Reproduction

- Paper geometry/radius and exact benchmark parameters.
- 3D spherical or validated axisymmetric geometry.
- Drained pore-pressure boundary around the specimen.
- Pore-pressure ghost / MLS boundary treatment or another strict drained boundary strategy.
- Analytical center-pressure postprocessing.
- Likely GPU support for useful resolution.

## Minimum Future Strict Smoke Standard

A future strict smoke should be coarse and short:

- `code=0`;
- `excluded=0`;
- no NaN;
- pressure fields written;
- symmetric qualitative pressure response;
- center pore-pressure history available for later comparison.

## C2 Strict-Reference Audit

C2 added a documentation-only audit of the strict Cryer requirements. No
GenCase, CPU, GPU, or PartVTK run was performed.

The audit confirms that strict Cryer requires:

- a 3D sphere of radius `R=a` or a validated axisymmetric equivalent;
- all-around normal traction `p0`;
- a drained curved exterior pore-pressure boundary;
- center pressure output normalized as `p_w(r=0,t)/p0`;
- a verified Mandel-Cryer analytical reference and dimensionless time mapping;
- the Poisson-ratio sweep `0.1`, `0.2`, `0.3`, `0.45`.

The converted paper text contains the Cryer center-pressure analytical form and
root equation, but the extraction is not clean enough to use directly as a
trusted implementation. A clean PDF/manual formula check or digitized reference
curve is still needed before strict comparison.

## Next Step Options

- **C3-A reduced manual-run path:** keep the current baseline XML/BAT, prepare a
  center-pressure extraction script, and let users run the reduced workflow
  manually for qualitative response and visualization.
- **C3-B strict setup path:** recover the analytical reference, lock the sphere
  geometry and normalization, then decide whether CPU boundary/loading source
  work is needed before any GPU route.

Current recommendation: use C3-A for quick workflow progress, or C3-B if the
next milestone must be strict paper reproduction.

## C3-B Strict Route Preparation

C3-B starts the strict reproduction route. It does not run the baseline and it
does not claim validation. New planning files are under
`strict_reproduction_plan/`.

C3-B decisions:

- strict geometry should start from a true 3D sphere, not the reduced column;
- the analytical center-pressure formula has been transcribed from the local
  PDF, but still needs a C4 reference script and Figure 7B check;
- all-around traction `p0` must not be faked as gravity or top compression;
- drained curved pore-pressure boundary remains a strict blocker;
- GPU should wait until CPU reference, geometry, loading, and boundary are
  credible.

Draft files:

- `strict_reproduction_plan/CaseCryer_PR_StrictSphere_Draft_Def.xml`
- `strict_reproduction_plan/strict_reference_notes.md`
- `strict_reproduction_plan/strict_geometry_notes.md`
- `strict_reproduction_plan/strict_loading_boundary_notes.md`

The draft XML is intentionally marked as not validated and not ready to run.
It does not replace `CaseCryer_PR_Baseline_Def.xml`.

## C4-A Analytical Reference Script

C4-A implemented the standalone analytical reference generator:

```powershell
py strict_reproduction_plan\cryer_reference_solution.py --make-plot
```

Outputs are written to `strict_reproduction_plan/`:

- `cryer_reference_curves.csv`
- `cryer_reference_roots.csv`
- `cryer_reference_convergence.csv`
- `cryer_reference_peak_metrics.csv`
- `cryer_reference_selfcheck.json`
- `figures/cryer_reference_center_pressure_curves.*`
- `figures/cryer_reference_root_convergence.*`
- `figures/cryer_reference_peak_vs_nu.*`
- `figures/cryer_reference_long_time_decay.*`

The script generates curves for `nu=0.1`, `0.2`, `0.3`, and `0.45`, and it
shows the expected Mandel-Cryer peak ordering. No Figure 7B digitized data is
currently available, so the curves are analytical reference candidates rather
than a completed paper-figure validation.

## E1 Linear Elastic Skeleton Switch

E1 added `SoilConstitutiveModel` under `<execution><special><soils>`:

- `0`: linear elastic skeleton;
- `1`: Drucker-Prager elastoplastic skeleton, default;
- `2`: Drucker-Prager + exponential softening.

The strict sphere draft now explicitly sets `SoilConstitutiveModel=0`, because
Cryer is a linear poroelastic benchmark. This only resolves the constitutive
consistency blocker; it does not resolve all-around spherical traction or the
drained curved hydraulic boundary.

Strict simulation is still not started. The next strict task is C4-B:
all-around spherical traction support audit.

## C4-B Spherical Traction Audit

C4-B audited existing loading routes for the strict Cryer all-around traction
`p0`.

Conclusion:

- no native XML route currently applies `F_i = -p0 A_i n_i` on a spherical
  exterior;
- `AccInput` is not strict Cryer traction because it applies marker-wise
  linear/angular acceleration rather than per-particle radial surface force;
- floating `linearforce` / `angularforce` are rigid-body total force routes and
  are not suitable for the deformable poroelastic sphere;
- prescribed motion is displacement control, not traction control;
- mDBC/cDBC normals may help a future implementation, but are not currently
  connected to an external spherical traction input.

This C4-B conclusion has been superseded by C4-B2 below. The earlier
area-weighted radial/spherical traction idea is no longer the recommended
strict route.

## C4-B3 Flexible Confining Stress CPU Smoke

C4-B3 implemented the selected flexible confining stress route as a CPU-only
minimal source term. The XML switch is `FlexibleConfiningStress`; it defaults
to off. Positive `ConfiningStressP0` means external compression. The term is
added only to the CPU mechanical momentum summation and is not written into the
material stress state or the pore-pressure equation.

GPU support is intentionally not available yet. A GPU run with
`FlexibleConfiningStress=1` hard-errors so that no case can silently run without
the requested traction source.

The smoke cases are in:

`strict_reproduction_plan/flexible_confining_stress_C4B3/`

They are tiny mechanics sanity checks:

- no-load regression;
- immediate small compressive load;
- ramped small compressive load.

All three CPU smokes completed with `code=0` and `excluded=0`. The loaded
smokes showed inward surface radial velocity and near-zero net force/center-of-
mass acceleration. These tests are not strict Cryer simulations. The next
loading step is a traction-only free-sphere smoke, while the drained curved
hydraulic boundary remains a separate blocker.

## C4-B4 Free-Sphere Flexible Confining Stress Smoke

C4-B4 checks the CPU-only loading source on a small free 3D sphere:

`strict_reproduction_plan/flexible_confining_stress_C4B4_FreeSphere/`

Retained cases:

- free-sphere no-load regression;
- free-sphere ramped `FlexibleConfiningStress` with `ConfiningStressP0=50 Pa`;
- optional stronger-load draft, not run by default.

The no-load and ramped CPU Release smokes both completed with `code=0` and
`excluded=0`. The ramped sphere showed inward radial compression, near-zero net
force / center-of-mass acceleration, positive pore-pressure response under
compression, and zero `Kplastic` with `SoilConstitutiveModel=0`.

This supports `FlexibleConfiningStress` as the current CPU traction candidate
for strict Cryer. It is still not a strict Cryer reproduction. GPU support is
unsupported, and the drained curved pore-pressure boundary remains a separate
blocker.

Next: C4-C drained curved pore-pressure boundary audit/development. Strict
Cryer simulation remains paused.

## C4-B2 Flexible Confining Stress Route

C4-B2 revises the loading decision. The `AccInput` patchwise surrogate is now
formally rejected for strict Cryer because it remains a marker-wise
acceleration/body-force equivalent, even if many shell patches and CSV files are
used.

The selected strict loading route is a future flexible confining stress source
based on the triaxial loading strategy in the drained/undrained SPH framework
paper. The intended source adds an isotropic compressive confining stress to the
mechanical momentum summation. Kernel symmetry cancels the term inside the
material domain, while free-surface truncation leaves an effective confining
pressure on the exterior.

Status:

- source implementation was not done in C4-B2 itself, but the follow-up C4-B3
  CPU implementation and smoke are now recorded above;
- C4-B2 itself did not run GenCase, CPU, GPU, or PartVTK;
- the strict sphere draft remains non-runnable and now contains a CPU-only
  flexible confining stress TODO block;
- drained curved pore-pressure boundary remains a separate blocker;
- strict Cryer simulation remains paused.

Next recommended task: C4-B4 traction-only free-sphere smoke, then C4-C
drained curved pore-pressure boundary audit/development.

## C4-C Drained Curved Pore-Pressure Boundary

C4-C adds a CPU-only curved drained hydraulic boundary prototype:

`PorePressureBoundaryOperator=3`

with:

`PorePressureCurvedDrained=1`

The prototype selects material particles near a prescribed spherical exterior,
adds an outward drained Dirichlet ghost state, and contributes it to
`LapPorePress` and `LapZ` before `PorePressRate` is computed. It is not a
post-update clamp. GPU is unsupported for this mode and hard-errors if it is
requested.

The smoke package is:

`strict_reproduction_plan/drained_curved_boundary_C4C/`

Retained cases:

- no-source/zero-pressure stability smoke;
- pressure-only uniform-excess diffusion smoke;
- flexible confining stress plus drained curved boundary smoke.

All CPU Release smokes completed with `code=0` and `excluded=0`. The diffusion
case showed surface excess dissipation, and the compression smoke generated
early positive center excess with `Kplastic=0`.

This resolves a first CPU prototype for the drained curved boundary, but it is
still not strict Cryer reproduction. C4-D then added the CPU-only
`HydraulicElevationSource=0` mode for gravity-free Cryer: `HydraulicGravity`
keeps a positive magnitude for hydraulic scaling, while hydrostatic reference
and the `k*LapZ` elevation source are disabled. The C4-D short smokes are under:

`strict_reproduction_plan/hydraulic_no_elevation_C4D/`

All C4-D CPU smokes completed with `code=0`, `excluded=0`. GPU remains
unsupported for `HydraulicElevationSource=0` and hard-errors if requested.
Strict Cryer simulation should still be treated as a coarse future smoke, not as
validated Figure 7 reproduction.

## C5 Coarse Strict-Sphere Smoke

C5 adds a CPU-only coarse integration smoke in:

`strict_reproduction_plan/C5_StrictSphere_CoarseSmoke/`

It combines the current strict-Cryer modules in one filled sphere:

- `SoilConstitutiveModel=0`;
- `FlexibleConfiningStress=1`;
- `PorePressureBoundaryOperator=3` and `PorePressureCurvedDrained=1`;
- `HydraulicElevationSource=0`.

The retained run is intentionally short (`TimeMax=0.006 s`). It completed with
`code=0`, `excluded=0`, and `Kplastic=0`, and generated positive center pore
pressure under compression. It is not a strict Figure 7B reproduction.
Exploratory longer windows exposed coarse free-sphere oscillation/out-check
risk, so the next step should be C5b refinement rather than immediate C6
quantitative comparison.

## C5b Strict-Sphere Refinement

C5b retained a targeted CPU-only refinement package:

`strict_reproduction_plan/C5b_StrictSphere_Refinement/`

The variants were deliberately narrow:

- baseline `p0=50 Pa`, short ramp, `TimeMax=0.006 s`;
- slow ramp `p0=50 Pa`, longer ramp, `TimeMax=0.012 s`;
- lower `p0=10 Pa`, short ramp, `TimeMax=0.006 s`;
- long slow ramp `p0=50 Pa`, longer ramp, `TimeMax=0.05 s`.

The first three completed with `code=0` and `excluded=0`. The longer slow-ramp
case was not accepted because it ended with `425` excluded particles after
out-check warnings beginning near `t=0.025 s`.

C5b shows that the C5 pressure over-peak is not simply a load-magnitude or
plasticity effect: the `p0=10 Pa` run has essentially the same normalized
response as the `p0=50 Pa` baseline, and `Kplastic` remains zero. The slower
ramp delays the peak but does not remove the high normalized response. Center
averaging has a moderate effect, but the main unresolved issue is the material
near-surface drained behavior: the curved ghost residual is zero while the
near-surface material excess remains large.

The Cryer track is therefore still not ready for quantitative Figure 7B
comparison. Recommended next step: refine the drained curved boundary/material
surface coupling before C6; GPU remains deferred.

## C5c Curved Boundary Coupling Refinement

C5c adds a CPU-only refinement package:

`strict_reproduction_plan/C5c_CurvedBoundaryCoupling/`

It keeps `PorePressureBoundaryOperator=3` experimental and adds
`CurvedDrainedBoundaryMode` sub-modes:

- `0`: original spherical drained Dirichlet ghost;
- `1`: strengthened image-style drained ghost;
- `2`: diagnostic material surface drained clamp, not production.

All C5c CPU Release runs completed with `code=0`, `excluded=0`, and
`Kplastic=0`. The material surface audit confirms that the C5/C5b near-surface
excess is systematic, not a single-particle outlier: the old ghost has
`179.37 Pa` mean and `218.47 Pa` p95 absolute excess in the `r>0.85R` material
shell at the final retained frame.

The strengthened ghost only modestly improves the compression response
(`2.923 p0` final center pressure becomes `2.819 p0`) and is not sufficient for
C6 Figure 7 comparison. The diagnostic clamp strongly reduces center pressure,
but it is not operator-consistent and creates pressure-rate artifacts in
pressure-only diffusion.

Decision: C6 remains premature. The next Cryer work should be a principled
mode-3 boundary quadrature / multi-sample Dirichlet refinement, then modest
geometry/dp refinement. GPU remains deferred.

## C5d Boundary Quadrature Refinement

C5d adds a CPU-only experimental submode:

```xml
<CurvedDrainedBoundaryMode value="3" />
```

for `PorePressureBoundaryOperator=3`. The new submode builds five drained
spherical boundary samples near each near-surface material particle and adds
their Dirichlet contribution to `LapPorePress`/`LapZ` before `PorePressRate`.
It is an operator-level boundary quadrature, not the diagnostic material
surface clamp.

Retained package:

`strict_reproduction_plan/C5d_BoundaryQuadrature/`

All C5d CPU Release tests completed with `code=0`, `excluded=0`, and
`Kplastic=0`. The quadrature mode is stable but only marginally improves the
Cryer compression response: final `r>0.85R` surface p95 excess decreases from
`218.47 Pa` to `208.90 Pa`, while the center peak decreases from `7.672 p0` to
`7.657 p0`.

This is not enough for Figure 7B quantitative comparison. Strict Cryer remains
blocked by drained curved material-surface coupling; GPU remains deferred.

## LIT-B Boundary Literature Audit

LIT-B pauses source changes after C5d and audits the available paper/supporting
documents before another Cryer boundary patch.

New reports are in `src/papers/u-p/`:

- `litb_original_upw_boundary_audit.md`
- `litb_supporting_materials_boundary_audit.md`
- `litb_drained_undrained_sph_boundary_audit.md`
- `litb_boundary_method_comparison.md`
- `litb_recommendation_before_next_boundary_change.md`

Conclusion: the original u-pw paper points toward free-surface identification,
boundary/dummy particle pore-pressure states, and MLS pressure extrapolation for
pore-pressure boundary treatment. Current mode `3` ghost/quadrature experiments
are useful diagnostics, but they are not a faithful implementation of that
boundary-particle/MLS route.

Next recommended step: design a CPU boundary-particle hydraulic state and
MLS/Adami-style extrapolation path for the spherical drained Cryer boundary
before any C5e source changes. C6 and GPU remain deferred.

## C5e Boundary-Particle Drained Boundary Prototype

C5e adds a CPU-only experimental submode:

```xml
<parameter key="PorePressureBoundaryOperator" value="3" />
<parameter key="PorePressureCurvedDrained" value="1" />
<parameter key="CurvedDrainedBoundaryMode" value="4" />
```

This mode selects dummy/boundary particles on the spherical exterior and gives
them a prescribed drained hydraulic state (`p_w=0`, `excess=0` in
`HydraulicElevationSource=0`). The selected boundary particles contribute to
`LapPorePress` and `LapZ` before `PorePressRate`. It is not a material-surface
clamp and it does not change the PR governing equation.

Retained package:

`strict_reproduction_plan/C5e_BoundaryParticleDrained/`

All C5e CPU Release cases completed with `code=0`, `excluded=0`, and
`Kplastic=0`. Mode 4 selected `2418` boundary particles and reduced the
compression center peak from `7.657 p0` to `6.908 p0`. However, pressure-only
diffusion over-drained and produced pressure-rate artifacts, so C6 remains
premature.

Next recommended step: MLS/Adami-style boundary-particle normalization for the
operator contribution. GPU remains deferred.

## C5f Boundary-Particle Weighting Refinement

C5f adds a CPU-only weighting switch for the C5e boundary-particle drained
boundary:

```xml
<CurvedDrainedBoundaryMode value="4" />
<CurvedDrainedBoundaryWeighting value="1" />
```

The retained C5f package is:

`strict_reproduction_plan/C5f_BoundaryParticleWeighting/`

It compares raw mode-4 weighting, Adami-style local partition normalization,
and a diagnostic capped weighting. All six CPU Release smokes completed with
`code=0`, `excluded=0`, and `Kplastic=0`.

Main result:

- raw mode 4 over-drains because the boundary-particle kernel partition is too
  large (`mean S_b=2.700` versus `mean S_m=0.760`);
- normalized weighting removes the strong negative pressure-only over-drainage
  and reduces pressure-rate artifacts;
- normalized weighting improves the compression surface residual, but the
  center peak remains high (`~7.45 p0`).

Strict Cryer Figure 7B comparison is still not ready. The next boundary task
should be a true MLS / partition-of-unity boundary-particle refinement or a
narrow pressure-only spherical diffusion calibration. GPU support remains
deferred.

## C5g Sphere Geometry / dp Diagnostic

C5g is a no-source-change CPU diagnostic retained under:

`strict_reproduction_plan/C5g_GeometryDpDiagnostic/`

It repeats the C5f normalized boundary-particle drained setup and compares the
coarse sphere (`dp=0.010`, `739` material particles) with one modestly finer
sphere (`dp=0.008`, `1213` material particles). The physical settings were
kept fixed: `SoilConstitutiveModel=0`, `FlexibleConfiningStress=1`,
`HydraulicElevationSource=0`, `PorePressureBoundaryOperator=3`,
`CurvedDrainedBoundaryMode=4`, and `CurvedDrainedBoundaryWeighting=1`.

All four CPU Release runs completed with `code=0`, `excluded=0`, and
`Kplastic=0`. The finer sphere reduced the compression center peak from
`7.448 p0` to `7.058 p0` and improved pressure-only drainage, but the
compression surface p95 residual was essentially unchanged (`131.56 Pa` to
`131.42 Pa`). Center averaging sensitivity improved, but the center response is
still far too high for Figure 7B comparison.

Decision: coarse sphere geometry is a contributor but not the main blocker.
C6 remains paused. The next strict-boundary task should focus on MLS or
flux-consistent radial diffusion at the drained spherical surface. GPU remains
deferred.

## C5h Higher-Resolution Sphere Diagnostic

C5h is a no-source-change CPU diagnostic retained under:

`strict_reproduction_plan/C5h_HigherResolutionSphere/`

It extends C5g with one higher-resolution sphere, `dp=0.0065`, while keeping
the C5g normalized mode-4 physics unchanged. Both C5h CPU Release cases
completed with `code=0`, `excluded=0`, and `Kplastic=0`.

The center peak continues to decrease:

- `dp=0.010`: `7.448 p0`
- `dp=0.008`: `7.058 p0`
- `dp=0.0065`: `6.731 p0`

However, surface and diffusion metrics do not improve. The higher-resolution
surface roughness std is `0.00365`, worse than the `dp=0.008` sphere
(`0.00303`). Compression final surface p95 rises to `244.34 Pa`, and the
pressure-only diffusion final surface p95 rises to `1023.40 Pa`.

Decision: higher resolution confirms that geometry matters, but it does not
make the current boundary rule C6-ready. The next step should return to MLS or
flux-consistent drained spherical boundary calibration before further
resolution work. GPU remains deferred.

## C5i Spherical Diffusion Flux Calibration

C5i is a postprocessing-only pressure-only diffusion gate retained under:

`strict_reproduction_plan/C5i_SphericalDiffusionFluxCalibration/`

It adds a 1D finite-volume spherical radial diffusion reference and compares
the existing C5e/C5f/C5g/C5h pressure-only diffusion results. No source code
was changed, no GPU run was performed, and no new compression case was run.

The FV reference shows that at the retained final time the true drained sphere
should still have nearly unchanged center pressure (`~1000 Pa`), while the
volume mean has decayed to about `616 Pa` and the `0.95R-1.0R` surface shell
mean to about `86 Pa`.

The current normalized mode-4 boundary does not reproduce that structure:

- center pressure decays too early;
- surface shell pressure remains too high;
- apparent volume-storage flux is often too strong;
- `dp=0.0065` shows late flux reversal and a large pressure-rate artifact.

Decision: normalized mode 4 is an over-strong, nonuniform Robin-like boundary,
not a true drained Dirichlet boundary. C6 remains paused. The next strict
Cryer source task should be a CPU-only MLS / flux-consistent spherical drained
boundary prototype, with pressure-only radial diffusion as the first acceptance
gate. GPU remains deferred.

## C5j MLS Boundary Flux Prototype

C5j is a CPU-only source prototype retained under:

`strict_reproduction_plan/C5j_MLSBoundaryFlux/`

It adds `CurvedDrainedBoundaryMode=5` to the experimental
`PorePressureBoundaryOperator=3` route. The new mode uses a constrained radial
linear MLS fit against the physical spherical drained surface, keeps the
prescribed drained value `p_b=0`, and applies an integrated shell-average
`LapPorePress` flux correction. It does not clamp material pressure and does
not count dummy boundary-particle volumes.

The pressure-only gate ran for `dp=0.008` and `dp=0.010` with CPU Release only.
Both cases completed with `code=0`, `excluded=0`, and `Kplastic=0`. No GPU run
and no Cryer compression smoke were performed.

Gate result:

- median flux ratio improves slightly relative to normalized mode 4;
- tested flux reversal is removed;
- center/volume RMSE improves in the retained comparisons;
- surface shell pressure remains far above the FV reference;
- final SPH/FV flux ratio remains about `4`;
- `PorePressRate` artifacts remain the same order as mode 4.

Decision: mode 5 is implemented but does not pass the pressure-only spherical
diffusion gate. C6 remains blocked. The next source task should move from
local-gradient MLS toward radial shell/FV matched boundary flux before any
compression or GPU work.

## C5k Radial-Shell Flux Boundary Prototype

C5k is retained under:

`strict_reproduction_plan/C5k_RadialShellFluxBoundary/`

It adds `CurvedDrainedBoundaryMode=6`, a CPU-only radial-shell /
finite-volume drained boundary flux prototype for
`PorePressureBoundaryOperator=3`. Mode `6` computes an outer spherical shell
mean pressure, estimates the drained surface flux against `p_b=0`, and applies
the integrated flux as a `LapPorePress` correction over the same outer shell.
It does not clamp material pore pressure and does not count dummy boundary
particle volumes.

Pressure-only CPU Release runs completed for `dp=0.008` and `dp=0.010` with
`code=0`, `excluded=0`, and `Kplastic=0`. No GPU run and no Cryer compression
smoke were performed.

Gate result:

- `dp=0.010` improves median flux ratio to `1.078` and lowers
  `PorePressRate` maxAbs to `1.52e5 Pa/s`;
- `dp=0.010` still leaves final surface shell mean at `577.06 Pa`, far above
  the FV reference `85.9 Pa`;
- `dp=0.008` shows late apparent flux reversal with final flux ratio
  `-14.20` and a `3.13e6 Pa/s` pressure-rate artifact.

Decision: mode `6` is implemented but does not pass the pressure-only radial
diffusion gate. C6 remains blocked. The next source task should address
near-boundary radial redistribution/interior Laplacian consistency rather than
only adding an integrated outer-shell sink.

## C5l Radial Operator Audit

C5l is retained under:

`strict_reproduction_plan/C5l_RadialOperatorAudit/`

It is postprocessing-only. No source code was changed, no GPU run was
performed, and no Cryer compression run was performed.

The audit reconstructs the strict-sphere material clouds and applies the CPU
material-material `LapPorePress` formula to manufactured radial fields. It also
uses retained pressure-only diffusion CSVs to check radial shell storage
balance.

Key result:

- constant pressure gives zero material-only Laplacian residual;
- quadratic `u=r^2` is close to exact `nabla^2 u=6` in the interior;
- the curved near-boundary shell has a large negative bias;
- `dp=0.0065` improves the interior operator but worsens the boundary cloud and
  shell balance;
- mode `6` can have a good global flux ratio while the surface shell profile
  remains wrong.

Decision: C6 remains blocked. The next source task should be a conservative
multi-shell radial exchange prototype, not another dp refinement or local MLS
only.

## C5m Conservative Shell Exchange Prototype

C5m is retained under:

`strict_reproduction_plan/C5m_ConservativeShellExchange/`

It adds `CurvedDrainedBoundaryMode=7`, a CPU-only conservative multi-shell
radial exchange prototype for `PorePressureBoundaryOperator=3`. Mode `7`
computes radial FV shell interface fluxes and applies a shell-average
`LapPorePress` correction so the populated shells satisfy the finite-volume
storage balance. It does not clamp material pressure and does not volume-count
dummy boundary particles.

Pressure-only CPU Release runs completed for `dp=0.008` and `dp=0.010` with
`code=0`, `excluded=0`, and `Kplastic=0`. No GPU run and no Cryer compression
smoke were performed.

Gate result:

- shell storage/flux conservation residual is reduced to machine precision in
  the mode-7 diagnostics;
- `dp=0.010` improves surface-shell RMSE relative to modes `4`, `5`, and `6`,
  but center and volume-mean RMSE worsen;
- `dp=0.008` develops late apparent flux reversal (`final flux ratio=-19.36`)
  and a large `PorePressRate` artifact (`4.48e6 Pa/s`);
- neither case passes the pressure-only FV radial diffusion gate.

Decision: C6 remains blocked. The shell-conservative route is useful as a
diagnostic, but the next source task should move toward a corrected
near-boundary SPH Laplacian/consistency operator.

## C5n Corrected Laplacian Prototype

C5n is retained under:

`strict_reproduction_plan/C5n_CorrectedLaplacian/`

It adds `CurvedDrainedBoundaryMode=8`, a CPU-only boundary-aware quadratic MLS
Laplacian prototype for `PorePressureBoundaryOperator=3`. Mode `8` fits a local
quadratic pressure polynomial near the drained sphere and replaces
near-boundary `LapPorePress` by the recovered Laplacian. It keeps the drained
surface value `p_b=0`, does not clamp material pressure, and does not count
dummy boundary-particle volume.

Manufactured radial fields improved: for `dp=0.008`, near-boundary `u=r^2`
p95 error dropped from about `13.81` to roundoff when the manufactured boundary
value is consistent, and the drained-like `R-r` p95 error dropped from about
`121.32` to `5.23`.

The pressure-only FV gate still failed. The `dp=0.008` CPU Release case
completed with `code=0`, `excluded=0`, and `Kplastic=0`, but final center
pressure was `47.38 Pa` versus FV `999.998 Pa`, final volume mean was
`232.26 Pa` versus FV `615.76 Pa`, and final surface shell mean was
`431.67 Pa` versus FV `85.88 Pa`. The run developed negative pressure and
apparent flux reversal, with final `PorePressRate` maxAbs `9.37e6 Pa/s`.

Decision: no Cryer compression smoke was run. C6 remains blocked. The next
boundary task should stabilize or limit the boundary-constrained corrected
Laplacian before any compression, C6, or GPU work.

## C5o Corrected Laplacian Stabilization

C5o is retained under:

`strict_reproduction_plan/C5o_CorrectedLaplacianStabilization/`

It keeps `CurvedDrainedBoundaryMode=8` and adds mode-8-only limiter controls:
positivity limiting, fixed MLS/material Laplacian blending, and optional
positivity after blending. Defaults keep the C5n corrected Laplacian behavior.

Pressure-only CPU Release cases ran at `dp=0.008` for positivity, blend `0.25`,
blend `0.50`, and blend `0.50` plus positivity. All completed with `code=0`,
`excluded=0`, and `Kplastic=0`.

Gate result:

- blend `0.25` improved center RMSE to `104.83 Pa` and reduced final
  `PorePressRate` maxAbs from `9.37e6` to `2.62e6 Pa/s`;
- surface-shell behavior remained wrong: final blend `0.25` surface shell was
  `1038.91 Pa` versus FV `85.88 Pa`;
- all limiter cases still had apparent flux reversal;
- negative pressure was reduced by blend `0.25` but not eliminated;
- no Cryer compression smoke was run.

Decision: C6 remains blocked. Local limiter tuning is not enough for strict
Cryer; the current route should pause or be redesigned as a true dynamic
drained-boundary value problem. GPU remains deferred.
