# Cryer C3-B Analytical Reference

Date: 2026-05-12

## Status

C3-B switches Cryer from a reduced launch workflow to a strict reproduction
track. This document records the clean analytical reference recovered from the
available paper PDF/converted text and identifies what still needs verification
before the numerical curve can be called paper-grade.

No DualSPHysics simulation was run for this task.

## Source Check

The local paper PDF and converted text identify Cryer's problem in Section 4.2,
Figure 7. The formula was checked against the rendered PDF page containing
Equations (46)-(47). The OCR text was not used blindly.

The paper states:

- geometry: poroelastic sphere of radius `R=a`;
- loading: uniform all-around normal traction `p0`;
- hydraulic boundary: drained exterior surface;
- comparison quantity: normalized center pressure `p_w(R=0,t)/p0`;
- independent variable: `T_v = c_v t / a^2`;
- Poisson sweep: `nu = 0.1`, `0.2`, `0.3`, `0.45`;
- material constants: same elastic and material parameters as the
  one-dimensional Terzaghi consolidation simulation, except for `nu`;
- simulation settings in the Figure 7 caption: `Delta t = 1e-6 s`,
  artificial viscosity `alpha = 0.1`, damping `xi = 4e-5`.

## Clean Formula From the Paper

The center-pressure solution printed in the paper is:

```text
p_w(R=0,t) / p0 =
  eta * sum_{j=1..infinity}
    [ (sin(xi_j) - xi_j)
      / (eta * xi_j * cos(xi_j) / 2 + (eta - 1) * sin(xi_j)) ]
    * exp(-xi_j^2 * c_v * t / a^2)
```

where `xi_j` are the positive roots of:

```text
(1 - eta * xi_j^2 / 2) * tan(xi_j) = xi_j
```

and:

```text
eta = (1 - nu) / (1 - 2 * nu)
T_v = c_v * t / a^2
```

The paper states this `eta` form for the incompressible-fluid and
incompressible-solid-matrix case.

## Numerical Evaluation Design

A strict reference script should:

1. solve the positive roots `xi_j` in the stable intervals
   `((j-1/2) pi, j pi)` for `j=1..N`;
2. evaluate the series for a log-spaced and linear `T_v` grid;
3. expose `N` as a convergence parameter;
4. generate curves for `nu=0.1`, `0.2`, `0.3`, and `0.45`;
5. report peak pressure, peak `T_v`, final residual, and convergence with `N`;
6. compare the generated curves against either digitized Figure 7B or another
   trusted Cryer reference before they are used as validation data.

## Required Checks

The reference script should reject or flag:

- root-count sensitivity larger than the target plotting tolerance;
- non-decay at large `T_v`;
- incorrect overshoot ordering;
- final pressure not approaching zero;
- `nu` values too close to `0.5` without adequate numerical safeguards.

Expected qualitative checks:

- `p_w(0,t)/p0` initially approaches the load scale;
- the center pressure overshoots above `1`;
- lower `nu` gives a stronger overshoot;
- all curves dissipate toward zero.

## Remaining Reference Gaps

The formula is now clean enough for a C4-A reference script, but it is not yet
validated against Figure 7B data. The remaining tasks are:

- implement the independent script;
- digitize or otherwise obtain Figure 7B reference points;
- confirm the `c_v` mapping used by the paper against the current material
  constants;
- choose the physical radius `a` used by the XML draft;
- document `p0` if the paper does not provide a Cryer-specific value.
- audit the current code's use of `HydraulicGravity`: Cryer has no elevation
  head source term, while the current PR implementation uses hydraulic gravity
  both for conductivity units and for the `LapZ` contribution. Strict Cryer may
  need a CPU-only option that keeps the hydraulic diffusion coefficient while
  disabling the elevation-source term.

Until those checks are complete, any generated analytical curve should be
called an implemented reference candidate, not a verified reproduction target.
