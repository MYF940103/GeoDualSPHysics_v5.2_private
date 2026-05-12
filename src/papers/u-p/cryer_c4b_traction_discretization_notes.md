# Cryer C4-B Traction Discretization Notes

Date: 2026-05-12

## Continuum Boundary Condition

The strict Cryer mechanical load is a uniform pressure-like traction on the
spherical boundary:

```text
t(x) = -p0 n(x),  |x-center| = a
```

where `n(x)` is the outward unit normal and `p0 > 0` is the compression
magnitude.

## Particle Force Mapping

A particle implementation should convert the continuum traction into a
mechanical force:

```text
F_i = -p0 A_i n_i
```

where:

- `n_i = (x_i-center)/|x_i-center|`;
- `A_i` is the associated surface area of boundary/surface particle `i`;
- the total area should satisfy `sum_i A_i ~= 4 pi a^2`;
- the net vector force should satisfy `|sum_i F_i| << sum_i |F_i|`.

If the solver stores acceleration rather than force, use:

```text
a_i = F_i / m_i
```

with the relevant particle mass. The area estimate must therefore be consistent
with the mass/volume represented by the target shell.

## Candidate Area Estimates

Initial CPU prototype options:

1. Uniform area per selected surface particle:

   ```text
   A_i = 4 pi a^2 / N_surface
   ```

   This is simple and gives exact total area by construction, but it assumes
   nearly uniform surface sampling.

2. Voronoi / nearest-neighbour surface area:

   More accurate for irregular sampling, but more complex.

3. Kernel-weighted area estimate:

   Potentially compatible with SPH quadrature, but needs careful normalization
   and diagnostics.

For a first strict Cryer CPU prototype, option 1 is acceptable if the generated
spherical surface particles are nearly uniform and diagnostics are reported.

## Diagnostics Required

A traction implementation should report at least:

| Diagnostic | Purpose |
|---|---|
| `N_surface` | Confirms selected particle count. |
| `sum(A_i)` | Should be close to `4 pi a^2`. |
| `sum(F_i)` | Net force should be near zero by symmetry. |
| `sum(|F_i|)` | Tracks total absolute applied load. |
| `max |F_i/A_i - p0|` | Checks traction magnitude. |
| radial direction error | Checks `F_i` is parallel to `-n_i`. |
| center-of-mass acceleration | Should be small for a symmetric sphere. |
| pressure normalization `p0` | Used for `p_w(0,t)/p0`. |

## Analytical Normalization

The Cryer comparison uses:

```text
p_w(0,t) / p0
```

The numerical `p0` used in the traction block must be the same scalar used in
postprocessing. A practical draft value such as `p0=10000 Pa` is acceptable
because the comparison is normalized, but the exact value must be logged and
kept in the XML/report.

## Symmetry Expectations

For a well-sampled full sphere:

- net force vector should approach zero with increasing resolution;
- stress state should begin as hydrostatic-like compression;
- center-of-mass motion should remain negligible;
- any residual net force should be reported as a discretization error.

Large net-force residuals would indicate poor surface particle distribution or
incorrect area weighting and should block strict comparison.

## Why Acceleration-Only Loading Is Not Enough

An acceleration on selected particles gives:

```text
F_i = m_i a_i
```

This is not equivalent to `F_i = p0 A_i n_i` unless the mass/area ratio is
constant and the acceleration direction is the local radial normal. Existing
`AccInput` does not provide that per-particle radial normal and area mapping.

## First Prototype Recommendation

If source development is accepted later, implement a CPU-only diagnostic-first
radial traction block:

1. select particles by marker and/or radius tolerance;
2. compute `n_i` from center to particle;
3. assign `A_i = 4 pi a^2 / N_surface`;
4. add `F_i/m_i` to mechanical acceleration;
5. print/store all diagnostics above;
6. keep feature disabled unless explicitly enabled.

GPU support should wait until the CPU diagnostics and pressure response are
credible.
