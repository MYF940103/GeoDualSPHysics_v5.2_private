# Cryer C4-B2 Flexible Confining Stress Formulation

Date: 2026-05-12

## Source Idea

The drained/undrained SPH framework paper describes a flexible confining
boundary condition for triaxial simulations. The key idea is to add a confining
stress to the conservation of momentum equation for domain particles. The
compact, symmetric SPH kernel causes this contribution to cancel inside the
domain, while the truncation at free surfaces leaves an effective boundary
pressure.

This avoids explicitly identifying free-surface particles, computing normals,
and assigning particle surface areas.

## Cryer Loading Target

Strict Cryer requires a uniform all-around inward normal traction `p0` on the
spherical exterior. For the flexible stress route, define a compressive
confining stress tensor:

```text
sigma_conf = -p0 I,  p0 > 0 in compression
```

This follows the usual solid-mechanics convention used in the surrounding
documentation: compression is represented as negative normal stress. The sign
must still be verified in C4-B3 with a static sphere sign smoke:

- a positive `p0` should produce inward radial acceleration near the sphere
  surface;
- the net force should be near zero by symmetry;
- the initial coupled response should increase center pore pressure.

## Pairwise Contribution

The existing CPU/GPU mechanical stress contribution has the form:

```text
a_i += m_j * (sigma_i + sigma_j) / (rho_i rho_j) dot gradW_ij
```

For an isotropic confining stress:

```text
sigma_conf,i = -p0_i I
sigma_conf,j = -p0_j I
```

The additional diagonal-only pair contribution is:

```text
coef_conf = m_j * ( -p0_i - p0_j ) / (rho_i rho_j)
a_conf,i += coef_conf * gradW_ij
```

where `p0_i` is the ramped confining pressure assigned to particle `i` when it
belongs to the target material set, otherwise zero.

The first implementation should add this term only in material-material
interactions. Boundary-particle interactions should be excluded initially so the
free-surface kernel truncation remains the mechanism producing the confining
surface pressure.

## Scope of the Term

The confining stress term:

- is mechanical momentum only;
- does not modify the pore-pressure PR equation;
- does not modify `HydraulicGravity`;
- does not modify body gravity;
- does not write into the constitutive stress field unless a later design
  explicitly needs that;
- does not change effective stress state variables directly;
- is compatible with `SoilConstitutiveModel=0` and should be tested there first.

## Relation to mDBC/cDBC

For strict Cryer, the confining stress should act on the poroelastic material
sphere. If a future strict geometry uses mechanical boundary particles around
the sphere, the flexible stress mechanism must be reconsidered because boundary
particles may remove the free surface truncation that makes the method work.

Therefore the first C4-B3 loading smoke should use a free material sphere for
the loading-sign and symmetry tests. Drained hydraulic boundary support remains
a separate question.

## Relation to Drained Boundary

The flexible confining stress solves only the mechanical load. It does not
impose `p_w=0` on the curved exterior. A strict Cryer run still needs a drained
curved pore-pressure boundary route.

## Relation to Corrected Gradients

This route does not promote corrected-gradient production. The source paper
states that momentum uses the conservative kernel-gradient form to retain
linear and angular momentum conservation. Therefore the first implementation
should use the same kernel gradient as the existing mechanical stress term.

