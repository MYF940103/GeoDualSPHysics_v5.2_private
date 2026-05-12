# Cryer C4 Implementation Decision

Date: 2026-05-12

## C3-B Outcome

C3-B establishes the strict route but does not claim reproduction. The clean
paper formula has been transcribed from the PDF, the strict geometry route is
defined as a true 3D sphere, and the main remaining blockers are loading and
curved drained hydraulic boundary support.

## Decision Table

| Item | Current status | C4 implication |
|---|---|---|
| Analytical reference | C4-A script implemented and self-checked; not yet validated against digitized Figure 7B. | Use generated CSVs for future postprocessing, but still collect/check Figure 7B data. |
| Geometry | True 3D sphere recommended. | Prepare strict sphere XML prototype after reference script. |
| Loading | Native spherical traction support not found. C4-B2 rejects `AccInput` patchwise surrogate and selects flexible confining stress as the strict loading route. | Implement CPU-first flexible confining stress before any strict Cryer run. |
| Drained boundary | Mode 0 not strict; mode 1 experimental; mode 2 CPU-only experimental. | CPU boundary decision needed before GPU. |
| Hydraulic gravity / elevation source | Classical Cryer has no gravity-driven elevation source, but current PR uses `HydraulicGravity` in both diffusion scaling and `LapZ`. | Audit whether a CPU-only no-elevation-source option is required. |
| Constitutive skeleton | E1 added `SoilConstitutiveModel=0` for linear elasticity. | Strict Cryer XML drafts should use model `0`; DP remains default for existing cases. |
| Center postprocessing | Design complete; no strict script yet. | Implement after reference CSV schema is fixed. |
| GPU | Not first priority. | Wait until CPU strict setup is credible. |

## Recommended C4 Path

### C4-A: Strict Reference Script First

Status: completed as
`examples/u-pw/03_Cryer_Problem/strict_reproduction_plan/cryer_reference_solution.py`.

The script now:

- solve roots of `(1 - eta xi^2 / 2) tan(xi) = xi`;
- generate reference CSV curves for all four Poisson ratios;
- run convergence checks;
- generate a Figure 7B-style reference-only plot;
- compare against digitized or manually extracted Figure 7B points if available.

The next action is not another reference-script task unless Figure 7B data is
provided. It is C4-B traction-route audit.

### C4-B: Spherical Traction Route Audit

Status: completed as a source/XML audit. No simulation was run.

C4-B found no existing native XML route that maps uniform pressure `p0` to
per-particle inward radial surface forces on a spherical exterior. `AccInput`,
floating total forces, and prescribed motion are not strict substitutes.

The recommended next loading implementation, if strict Cryer proceeds, is a
CPU-first generic radial/spherical traction block with explicit area weighting
and force-symmetry diagnostics. The strict sphere XML remains a draft until
loading and boundary are solved.

### C4-B2: Flexible Confining Stress Route

Status: completed as a design/source audit. No source was changed and no
simulation was run.

C4-B2 formally rejects the `AccInput` patchwise spherical-loading surrogate.
Even with many marker patches and external CSV files, it would remain a
patchwise shell body-force equivalent, not a continuous all-around pressure
traction.

The selected loading route is the flexible confining stress method described in
the drained/undrained SPH framework paper's triaxial section. A compressive
isotropic stress tensor is added to the mechanical momentum summation. Kernel
symmetry cancels the contribution inside the specimen, while free-surface
truncation leaves an effective confining pressure on the exterior. This avoids
explicit surface-particle detection, normal reconstruction, and area weighting
in the first implementation.

The next loading task should be C4-B3:

- CPU-first implementation;
- default off XML switch;
- no-load regression;
- static sphere sign/symmetry diagnostics;
- hard error on GPU while unsupported.

### C4-C: Boundary / Loading Source Development

Only if native routes are insufficient:

- implement and validate CPU flexible confining stress support;
- design CPU curved drained boundary support;
- if needed, add a CPU-only Cryer/no-elevation hydraulic option that preserves
  the diffusion coefficient but removes the `LapZ` source;
- avoid corrected-gradient production;
- avoid GPU until CPU behavior is clear.

### C4-B3: CPU Flexible Confining Stress Support

Status: completed as a minimal CPU implementation and tiny mechanics smoke.

C4-B3 added the XML-controlled `FlexibleConfiningStress` source with
`ConfiningStressP0`, ramp timing, target marker selection, and mode `0`
isotropic loading. The term is added to the CPU material-material mechanical
stress-divergence pair summation only. It is not written into the material
stress tensor and it does not change the PR pore-pressure equation,
`HydraulicGravity`, `AccInput`, `SoilConstitutiveModel`, or
`PorePressureBoundaryOperator`.

GPU support is intentionally unsupported in this phase: enabling
`FlexibleConfiningStress=1` on the GPU path hard-errors instead of silently
falling back.

The C4-B3 no-load, sign, and ramp smokes all completed with `code=0` and
`excluded=0`. The sign smoke confirmed inward surface velocity for positive
`ConfiningStressP0`, with symmetry residuals of order `1e-08`.

The next loading step should be C4-B4: a small traction-only free-sphere smoke.
Strict Cryer simulation is still paused because the drained curved
pore-pressure boundary remains unresolved.

### C4-B4: Free-Sphere Flexible Confining Stress Smoke

Status: completed as a CPU-only traction-source smoke.

C4-B4 moved the C4-B3 loading source from a tiny mechanics sanity check to a
small free 3D sphere (`R=0.05 m`, `dp=0.01 m`, `739` material particles). The
no-load free-sphere regression and the ramped `FlexibleConfiningStress` sphere
smoke both completed with `code=0` and `excluded=0`.

For the ramped case (`ConfiningStressP0=50 Pa`), the sphere moved inward:
surface radial velocity mean was `-6.28e-04 m/s` and surface radial displacement
mean was `-1.09e-06 m`. The symmetric load diagnostics remained near zero:
net/absolute force was `1.94e-08` and the center-of-mass acceleration estimate
was `2.08e-08 m/s2`. Center and mean excess pore pressure increased relative to
the no-load baseline, and `Kplastic` stayed zero with `SoilConstitutiveModel=0`.

This makes `FlexibleConfiningStress` the current CPU traction candidate for
strict Cryer. It does not validate strict Cryer by itself. GPU support remains
unsupported and the drained curved pore-pressure boundary remains the next
blocker.

Recommended next task: C4-C drained curved pore-pressure boundary
audit/development. Strict Cryer simulation remains paused.

### C4-C: CPU Drained Curved Pore-Pressure Boundary

Status: completed as a CPU-only operator-level prototype and short smoke.

C4-C adds `PorePressureBoundaryOperator=3` with
`PorePressureCurvedDrained=1`. The mode selects material particles in a
prescribed spherical near-surface shell, builds an outward drained Dirichlet
ghost state, and adds that contribution to CPU `LapPorePress` and `LapZ`
before `PorePressRate` is computed. It is not a post-update clamp.

GPU support is intentionally unsupported. A GPU run with mode `3` or
`PorePressureCurvedDrained=1` hard-errors during XML loading.

The smoke package is:

`examples/u-pw/03_Cryer_Problem/strict_reproduction_plan/drained_curved_boundary_C4C/`

Results:

- zero/no-source stability smoke: `code=0`, `excluded=0`;
- pressure-only uniform-excess diffusion smoke: `code=0`, `excluded=0`;
- flexible confining stress plus drained curved boundary smoke:
  `code=0`, `excluded=0`;
- surface excess in the diffusion smoke decayed from `1000 Pa` to about
  `963 Pa` over the short run;
- compression smoke generated early positive center excess while keeping
  `Kplastic=0`.

Limitations remain important: the prototype is first-order/spherical, not MLS
or general boundary quadrature, and the current PR formulation still requires a
positive hydraulic gravity magnitude for hydraulic scaling. Strict Cryer
simulation should still be treated as paused until the no-elevation-source
representation and center-pressure comparison plan are explicitly accepted.

### C4-D: Reduced Fallback

If strict loading or boundary support is blocked, keep the reduced baseline as
a launch workflow and record Cryer strict reproduction as blocked.

## User Input That Would Help

The next step would be faster with one of:

- clean PDF screenshot/crop of Equations (46)-(47) and Figure 7B;
- digitized Figure 7B data;
- confirmation of the intended physical sphere radius `a`;
- confirmation that `p0=10 kPa` is acceptable if no paper-specific `p0` is
  found.

## Stop/Proceed Criteria

Proceed to source changes only after:

- reference curves pass convergence and figure-level checks;
- Figure 7B digitization is available or the lack of digitized data is accepted
  as a documented limitation;
- strict sphere geometry is accepted;
- flexible confining stress CPU diagnostics pass;
- the `HydraulicGravity` / no-elevation-source representation is resolved;
- boundary strategy is selected for CPU.

## C4-D: No-Elevation Hydraulic Representation

C4-D is complete. The branch now has `HydraulicElevationSource`:

- `1` default: legacy hydrostatic/elevation convention, including
  `k*LapZ` in `PorePressRate`;
- `0`: CPU-only gravity-free Cryer convention. `HydraulicGravity` still
  supplies a positive magnitude for `k/(rho_w*g_h)`, but the hydrostatic
  reference is zero and `k*LapZ` is omitted from `PorePressRate`.

Short CPU smokes under
`examples/u-pw/03_Cryer_Problem/strict_reproduction_plan/hydraulic_no_elevation_C4D/`
passed with `code=0`, `excluded=0`:

- source-on regression;
- no-elevation pressure diffusion;
- no-elevation flexible-confining-stress compression plus curved drainage.

GPU support remains deferred and hard-errors if `HydraulicElevationSource=0` is
requested. The next recommended step is C5 coarse CPU strict-sphere smoke, not
GPU and not strict Figure 7 comparison yet.

## C5: Coarse CPU Strict-Sphere Smoke

C5 is complete as a CPU-only short integration smoke under:

`examples/u-pw/03_Cryer_Problem/strict_reproduction_plan/C5_StrictSphere_CoarseSmoke/`

The retained passing run combines `SoilConstitutiveModel=0`,
`FlexibleConfiningStress=1`, `PorePressureBoundaryOperator=3` with
`PorePressureCurvedDrained=1`, and `HydraulicElevationSource=0` in one coarse
filled sphere. It completed with `code=0`, `excluded=0`, `Kplastic=0`, and
showed positive center pore pressure under compression. `LapZ` remained
diagnostic-only in the pressure-rate terms.

The response is only qualitative: the averaged center pressure peaks at about
`383.6 Pa` (`7.67 p0`) at `t=0.002011 s` for `p0=50 Pa`, then begins to
dissipate/rebound in the short window. Exploratory longer windows entered a
coarse free-sphere oscillatory/out-check regime, so C5 should not proceed
directly to quantitative Figure 7 comparison.

Next recommended step: C5b geometry/time-window refinement before C6. GPU
remains deferred.

## C5b: Strict-Sphere Geometry and Time-Window Refinement

C5b is complete as a targeted CPU-only refinement under:

`examples/u-pw/03_Cryer_Problem/strict_reproduction_plan/C5b_StrictSphere_Refinement/`

No source code was changed and no GPU run was performed. The retained variants
were:

- baseline: `p0=50 Pa`, short ramp, `TimeMax=0.006 s`, `code=0`,
  `excluded=0`;
- slow ramp: `p0=50 Pa`, ten-times longer ramp, `TimeMax=0.012 s`,
  `code=0`, `excluded=0`;
- lower p0: `p0=10 Pa`, short ramp, `TimeMax=0.006 s`, `code=0`,
  `excluded=0`;
- long slow ramp: `p0=50 Pa`, slow ramp, `TimeMax=0.05 s`, `code=0` but
  `excluded=425`, so it is not a passing smoke.

The lower-p0 case scaled almost exactly with load: the normalized peak remained
about `8.18 p0`, and the final normalized center pressure remained about
`2.96 p0`. This points away from load-magnitude nonlinearity or plasticity.
The slow-ramp case reduced the very early pressure rise but reached about
`7.66 p0` by the end of its shorter run, so the C5 over-peak is not only a
fast-ramp artifact.

Center averaging changes the baseline peak from about `8.45 p0` for the
nearest particle to `7.67 p0` for a `0.4R` average. This is meaningful but not
enough to support quantitative Figure 7 comparison.

The main remaining blocker is the drained material surface: the curved ghost
boundary diagnostic residual is zero, but near-surface material excess remains
large (`263 Pa`, or `5.26 p0`, in the baseline final frame). C6 quantitative
comparison is therefore not recommended yet. The next task should refine the
drained curved boundary/material-surface coupling, with geometry/resolution
refinement after that. GPU remains deferred.

## C5c: Curved Drained Boundary / Material-Surface Coupling

C5c is complete as a CPU-only source and smoke refinement under:

`examples/u-pw/03_Cryer_Problem/strict_reproduction_plan/C5c_CurvedBoundaryCoupling/`

The source change is limited to `PorePressureBoundaryOperator=3`. Existing
modes `0`, `1`, and `2` keep their previous behavior, and mode `3` remains
experimental and CPU-only.

`CurvedDrainedBoundaryMode` now supports:

- `0`: previous first-order spherical Dirichlet ghost;
- `1`: strengthened image-style Dirichlet ghost;
- `2`: diagnostic material surface drained clamp, not production.

All six short CPU Release C5c runs completed with `code=0`, `excluded=0`, and
`Kplastic=0`. The surface residual audit showed that the C5b near-surface
excess is systematic rather than an outlier: for the old ghost at the final
frame, the `r>0.85R` material shell has mean excess `179.37 Pa`, p95 absolute
excess `218.47 Pa`, and max absolute excess `263.15 Pa`.

The strengthened ghost improves the pressure-only diffusion rate and slightly
reduces the compression residual, but not enough for quantitative Cryer
comparison:

- old ghost peak center pressure: `7.672 p0`;
- strengthened ghost peak center pressure: `7.663 p0`;
- old ghost final center pressure: `2.923 p0`;
- strengthened ghost final center pressure: `2.819 p0`.

The diagnostic material clamp reduces the compression peak to `2.218 p0` and
the final center pressure to `1.571 p0`, confirming that material-surface
drainage controls much of the response. However, the clamp creates non-operator
pressure-rate artifacts in the pressure-only diffusion smoke and must not be
used as a production boundary.

C6 Figure 7B comparison remains premature. The next strict-Cryer task should be
a more principled mode-3 boundary quadrature / multi-sample Dirichlet
refinement, followed by a modest geometry/dp refinement. GPU remains deferred.

## C5d: Curved Drained Boundary Quadrature

C5d is complete as a CPU-only experimental boundary-quadrature refinement under:

`examples/u-pw/03_Cryer_Problem/strict_reproduction_plan/C5d_BoundaryQuadrature/`

The source change remains limited to `PorePressureBoundaryOperator=3`. Existing
boundary modes `0`, `1`, and `2` are unchanged. The new
`CurvedDrainedBoundaryMode=3` constructs five virtual drained samples near the
local spherical projection of each near-surface material particle and adds
their Dirichlet contribution to `LapPorePress`/`LapZ` before `PorePressRate`.
It does not clamp material pore pressure.

All C5d CPU Release tests completed with `code=0`, `excluded=0`, and
`Kplastic=0`. For the compression smoke, mode `3` is stable but only mildly
improves the surface residual:

- old ghost final `r>0.85R` surface p95 excess: `218.47 Pa`;
- quadrature final `r>0.85R` surface p95 excess: `208.90 Pa`;
- old ghost center peak: `7.672 p0`;
- quadrature center peak: `7.657 p0`.

Pressure-only diffusion also remains incomplete: mode `3` increases the
boundary contribution but does not outperform the strengthened ghost in the
short window, and it has a higher pressure-rate/velocity response than modes
`0` and `1`. It is much better behaved than the diagnostic clamp, but it is not
yet a sufficient strict drained curved boundary.

C6 quantitative Figure 7B comparison is still premature. The next useful step
is either a more complete MLS/boundary-particle-aware surface quadrature or
carefully scoped geometry/dp refinement after the boundary rule is improved.
GPU remains deferred.

## LIT-B: Boundary Literature Audit Pause

LIT-B is complete as a documentation-only literature and implementation audit.
No source code was changed and no simulation was run.

The audit reviewed:

- the converted original u-pw paper text;
- the local Supporting Materials implementation notes;
- the converted drained/undrained SPH framework paper;
- the current H1/O1/C4-C/C5c/C5d implementation reports.

The main conclusion is that the original u-pw paper does not describe the
Cryer drained boundary as a material-side spherical ghost/quadrature rule.
Instead, the paper's boundary section points toward free-surface identification,
boundary/dummy particle pore-pressure states, and MLS extrapolation for
pore-pressure Neumann boundaries. The drained/undrained SPH paper independently
supports the idea that dummy boundary particles should carry pore pressure
through normalized-kernel extrapolation, although that paper uses a penalty
undrained formulation rather than transient PR diffusion.

Decision after LIT-B:

- pause further mode-3 quadrature source changes;
- do not start C6 quantitative comparison;
- defer dp refinement until boundary-state coupling is more faithful;
- next source-facing step should be a design task for a CPU
  boundary-particle hydraulic state with MLS/Adami-style extrapolation for the
  spherical drained Cryer boundary.
