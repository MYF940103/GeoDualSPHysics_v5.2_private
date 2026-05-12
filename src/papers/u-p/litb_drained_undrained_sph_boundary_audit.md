# LIT-B Drained/Undrained SPH Boundary Audit

Date: 2026-05-12

## Scope

This note audits:

`src/papers/u-p/an_sph_framework_for_drained_and_undrained_loading.md`

The paper is useful because it describes dummy boundary particles, Adami-style
pressure extrapolation, and flexible confining stress. It is not the same as
the transient PR u-pw paper and must not be copied blindly.

## Drained and Undrained Meaning

In this paper:

- drained conditions are represented by `p_w=0`, so total stress reduces to
  effective stress;
- undrained conditions use a penalty relation
  `p_w = -K_w tr(eps)`;
- the method targets end-member drained/undrained loading behavior, not a
  transient diffusion/consolidation PR equation.

This is a major distinction from our strict Cryer route, which uses transient
PR diffusion and must dissipate pore pressure through a drained boundary.

## Self-Weight / Top Drainage

The self-weight test is an undrained loading test. The paper states that the
bottom is fixed and the sides are free-slip or periodic. It validates the
undrained penalty formulation against analytical self-weight distributions.

This does not provide a transient top-drained / bottom-no-flux PR boundary
operator. It is therefore only indirect evidence for how boundary particles may
be assigned pressure.

## Dummy Boundary Particles

The paper uses dummy/fixed boundary particles:

- three to four layers are placed at solid walls;
- boundary particle density and mass are kept constant;
- effective stress tensor and pore-water pressure are evolved/assigned over
  time;
- stresses of boundary particles are determined from neighboring domain
  particles using a previous boundary formulation.

This is directly relevant to our current question: boundary particles should
carry a meaningful hydraulic state, not remain absent from the pore-pressure
operator.

## Pore Pressure Extrapolation

The paper states that pore-water pressures in boundary particles are
extrapolated from neighboring soil particles using Adami et al.'s normalized
kernel formulation. The expression includes a hydrostatic smoothing term based
on gravity and vertical distance, so hydrostatic pressure fields remain smooth.

In plain implementation terms:

```text
p_w(boundary) = normalized weighted average of
                p_w(soil neighbor) + hydrostatic correction
```

This is not a drained Dirichlet condition by itself. It is a wall/dummy
boundary pressure reconstruction for a smooth pressure field.

## Bottom No-Flux / Neumann Diffusion

This paper does not give a transient PR no-flux diffusion operator. Its
undrained behavior comes from the penalty formulation rather than from
explicitly enforcing `grad(p_w) dot n = 0` in a diffusion equation.

Therefore it can inspire boundary pressure extrapolation, but it cannot be
used as the complete answer for Cryer PR drained/no-flux boundary conditions.

## Curved Drained PR Diffusion Boundary

No curved drained PR diffusion boundary formula was found in this paper. It
does not solve Cryer with a transient PR boundary operator; it uses the
drained/undrained framework and flexible confining stress in triaxial and fault
examples.

## Useful Lessons For H1 / Mode 2 / Mode 3

Directly useful:

- boundary particles should have hydraulic state;
- normalized kernel extrapolation is a credible way to assign boundary pressure
  from neighboring material particles;
- hydrostatic correction should be part of boundary pressure extrapolation when
  gravity/hydrostatic reference is active;
- flexible confining stress is a good mechanical loading route because it
  avoids explicit surface normals/areas.

Not directly transferable:

- the penalty undrained law is not the PR transient diffusion equation;
- Adami wall pressure extrapolation alone is not a drained Dirichlet `p_w=0`
  boundary;
- no explicit curved drained PR operator or Cryer boundary implementation is
  provided;
- no bottom no-flux PR Neumann formula is given.

## Audit Conclusion

The drained/undrained paper supports a boundary-particle hydraulic-state
strategy. It does not support further ad hoc spherical material-ghost
strengthening as the most faithful next step. The best borrowing is not the
whole formulation, but the idea of assigning boundary-particle pore pressure
through normalized kernel/Adami-style or MLS-style extrapolation and then using
those boundary states in the hydraulic operator.
