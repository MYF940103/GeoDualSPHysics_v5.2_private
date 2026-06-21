# Cryer Stage1 center-pressure issue: root-cause analysis

Date: 2026-06-18

## Question

During Cryer Stage1, the internal pore-pressure field shows strong radial
layering and the center pressure is too low for the FrDraw case, even though
the external spherical load has been verified to enter `Ace` with the expected
direction and magnitude.

The aim of this note is to explain why this happens, using:

- the u-pw paper;
- the current Cryer XML files;
- the current external-load implementation;
- previous retained test conclusions;
- the new particle-mode comparison performed in
  `refinement/geometry_compare_20260618`.

## Reference condition from the paper

The paper describes Cryer's problem as a poroelastic sphere with a drained
exterior boundary subjected to a uniform normal traction `p0` on the surface.
At the sphere center, pore pressure initially reaches `p0`, then rises beyond
`p0` due to the Mandel-Cryer effect before dissipating.

This is a smooth continuum boundary-value problem:

- the boundary is a smooth sphere;
- the traction is a uniform normal traction on that sphere;
- the early response is effectively a quasi-static undrained loading state;
- the later peak is caused by drainage along the exterior boundary and load
  transfer toward the center.

## Current SPH implementation

The current `SphereNormal` mode applies the load as a particle acceleration on
detected free-surface particles:

```text
a_i = -p0 * A_i * n_i / m_i
A_i = 4*pi*R_eff^2 / N_surface
```

The CPU and GPU implementations compute an effective radius and an equal area
per detected surface particle, then apply a radially inward acceleration. The
recent `HydroMechLoadAce` diagnostic confirmed that, for FrDraw:

- all detected surface particles receive the load;
- no interior particles receive the load;
- the load vectors point inward;
- load magnitudes are uniform;
- the resultant imbalance is very small.

Therefore, the current first-order load-vector implementation is not the main
problem for the FrDraw case.

## Current XML differences that matter

The formal case root and the area-load test configuration are not identical.

Formal Stage1:

- uses FrDraw;
- `HydroMechDrainage = 1` with delayed drainage;
- `HydraulicConductivity = 0`;
- `SoilDampingCoef = 0.2`;
- `HydroMechTopLoadRampTime = 0.005`.

Corrected area-load Stage1:

- uses FrDraw;
- `HydroMechDrainage = 0`;
- `HydraulicConductivity = 0`;
- `SoilDampingCoef = 0.02`;
- area-normalized `SphereNormal` load.

The corrected Stage1 is the better diagnostic configuration. The formal case
still contains a high damping coefficient (`0.2`) and should not be treated as
the best current parameter set.

## Previous retained conclusions

The retained refinement notes showed:

- uniform pore-pressure initialization was abandoned because it did not
  initialize the matching effective stress field;
- the better physical path is two-stage undrained loading followed by drainage;
- extending Stage1 to about `0.078-0.082 s` improved the restart state, but
  `dp=0.003` still plateaued around `p_center/q0 ~= 0.94`;
- `k=1e-4 m/s` gave the best full-cycle Cryer peak so far, although late
  dissipation was slow;
- radius/thickness SphereSurface drainage was less reliable than FreeSurface
  drainage for the regular volumetric sphere;
- FrDraw improves the exterior sphere but can create shell-like interior
  layers.

The `k=0` versus `k=1e-8` short Stage1 comparison showed that a tiny non-zero
permeability does not materially improve the center pore pressure or radial
distribution. This argues against `k=0` being the main cause.

## New particle-mode comparison

A short Stage1-only comparison was run in:

```text
refinement/geometry_compare_20260618
```

Both variants used:

- `dp = 0.003 m`;
- `R = 0.05 m`;
- `q0 = 10000 Pa`;
- `HydroMechDrainage = 0`;
- `SoilDampingCoef = 0.02`;
- area-normalized `SphereNormal` load;
- `TimeMax = 0.006 s`;
- `TimeOut = 0.003 s`.

Only the particle generation mode differed.

### FrDraw geometry

- fluid particles: `22483`;
- max radius: about `0.050000 m`;
- detected load surface particles: `3630`;
- `R_eff = 0.05`;
- load area sum: `0.0314159`;
- resultant load residual: `2.75e-4`;
- full load acceleration: `1526.37 m/s2`.

Stage1 at `t ~= 0.006 s`:

- center-nearest pressure: `3144 Pa` (`0.314 q0`);
- core mean pressure (`r <= 0.006 m`): `4741 Pa`;
- surface mean pressure: `16636 Pa`;
- center velocity magnitude: `2.39e-4 m/s`.

Interpretation:

- The geometric boundary and load balance are clean.
- The response is dynamically quiet.
- However, pressure remains strongly layered and the center lags.
- This points to internal volumetric particle layering and the transient
  propagation of compression from the loaded shell to the center.

### Regular `drawsphere` geometry

- fluid particles: `22887`;
- max radius: about `0.05439 m`;
- particles with `r > 0.05 m`: `3494`;
- particles with `r > 0.051 m`: `2302`;
- detected load surface particles: `3392`;
- `R_eff = 0.0514711`;
- load area sum: `0.0332918`;
- resultant load residual: `1.865e-2`;
- full load acceleration: `1731.0 m/s2`.

Stage1 at `t ~= 0.006 s`:

- center-nearest pressure: `14702 Pa` (`1.47 q0`);
- core mean pressure (`r <= 0.006 m`): `9379 Pa`;
- surface mean pressure: `21429 Pa`;
- center velocity magnitude: `2.11e-2 m/s`.

Interpretation:

- The center pressure is larger, but not because the model is more physical.
- The effective radius and total scalar load are larger than intended.
- The load resultant imbalance is two orders of magnitude larger than FrDraw.
- The pressure field and velocity indicate a strong transient impact response.
- Therefore, the regular case's higher center pressure should not be treated
  as better Cryer agreement.

## Why 1D consolidation works better

The 1D q0 Terzaghi verification has a much simpler loading geometry:

- flat top boundary;
- vertical surcharge;
- regular column/grid particle arrangement;
- one dominant strain direction;
- no curved all-around free surface;
- no need to distribute a spherical surface traction over a shell of particles.

Retained q0 notes show that delayed drainage can maintain a healthy near-10 kPa
pre-drainage excess pressure field in 1D. This means the u-pw formulation and
basic q0 pore-pressure generation path are capable of producing the expected
undrained response when the loading geometry and particle distribution are
well aligned.

Cryer is different:

- the external load acts on a curved surface;
- the load is converted to accelerations on detected free-surface particles;
- the surface particle layer must represent both boundary area and near-surface
  control volume;
- FrDraw gives a clean surface but changes the interior into shell-like layers;
- regular `drawsphere` gives a rough oversized exterior and a biased load
  resultant;
- the analytical solution assumes a smooth quasi-static continuum sphere, not
  a dynamically loaded shell of particles.

Thus, the difference between 1D and Cryer is not evidence that the u-pw
governing equation is wrong. It is evidence that Cryer is much more sensitive
to geometric and loading consistency.

## Current best explanation

The Stage1 issue is most likely caused by a mismatch between the analytical
Cryer boundary-value problem and the current SPH particle realization:

1. FrDraw correctly fixes the exterior sphere and makes the load direction and
   area balance good.
2. But FrDraw also creates a radially shell-like internal particle distribution.
3. The external load is applied to a surface shell; the interior only responds
   through dynamic stress/strain propagation.
4. This produces high surface pore pressure, strong radial layering, and a
   delayed center response.
5. Regular `drawsphere` can raise the center pressure quickly, but this occurs
   through a larger, imbalanced, oversized effective load and large velocity,
   not through a cleaner approximation of Cryer's problem.

## Recommended next direction

Without changing the u-pw equations, the next useful work should focus on the
particle model and load-path equivalence:

1. Do not use direct FrDraw for the whole Cryer volume as the final model.
2. Do not use regular `drawsphere` center pressure as proof of accuracy unless
   the effective radius, scalar load, and resultant imbalance are corrected.
3. Build or generate a hybrid sphere:
   - regular volumetric interior;
   - controlled smooth surface layer;
   - surface particles representing a known area and volume thickness.
4. Alternatively, use a pre-relaxation/particle-regularization step to produce
   a smooth spherical boundary without shell-like radial layering.
5. Keep using FreeSurface drainage for the current regular volumetric sphere
   unless a better surface marker is introduced.
6. Use `SoilDampingCoef = 0.02` rather than `0.2` for diagnostics unless a new
   damping sweep proves otherwise.

The most important conclusion is that the present evidence points to geometry
and load-path consistency, not to a defect in `PorePressRate`, `-divv`, seepage,
or the u-pw governing equations.
