# LIT-B Original u-pw Paper Boundary Audit

Date: 2026-05-12

## Scope

This note audits the boundary treatment described in the converted main u-pw
paper text:

`src/papers/u-p/converted/u_pw_paper_text.md`

and the implementation notes:

`src/papers/u-p/u_pw_sph_implementation_notes.md`

The goal is to decide whether the current Cryer mode-3 spherical ghost and
quadrature path is aligned with the paper before adding another source patch.

## General Boundary Statement

The original u-pw paper explicitly partitions boundary conditions into:

- Neumann traction boundaries;
- Dirichlet solid-velocity boundaries;
- Dirichlet pore-pressure boundaries;
- Neumann pore-fluid-flux boundaries.

For pore pressure, the paper writes the Dirichlet condition as a prescribed
`p_w` and the flux boundary as a prescribed normal flux. The notes also record
that undrained boundaries correspond to

```text
grad(p_w) dot n = 0
```

or zero fluid flux.

## Drained Boundary

The paper says pore-pressure Dirichlet conditions are applied by first
identifying free surfaces and then either:

1. setting pore pressure to zero at the free surfaces; or
2. setting a desired pore-pressure value at boundary/dummy particles.

This means the drained boundary is not described as only a post-update material
layer clamp. It is connected to free-surface detection and/or boundary-particle
pore-pressure states.

The paper does not give a detailed Cryer-specific algorithm such as "for every
spherical surface material particle, build N ghost samples." The general method
instead points to free-surface detection and boundary/dummy particle pressure
values.

## Undrained / No-Flux Boundary

For pore-pressure Neumann boundaries, including undrained/no-flux boundaries,
the paper states that additional treatment is needed to enforce
`grad(p_w) dot n = 0`.

The implementation note and converted text both point to a moving least-squares
formulation from Chow et al. The purpose is to extrapolate pore pressure from
domain particles to boundary particles using a corrected MLS kernel that is
zero- and first-order consistent, so linear pressure fields can be recovered.

This is important: the original paper's no-flux route is not described as a
simple total-pressure mirror, a layer mean copy, or a material-only SPH
operator with no boundary state.

## Cryer-Specific Information

The Cryer section states the physical benchmark:

- poroelastic sphere;
- drained exterior surface boundary;
- uniform normal traction `p0` at the surface;
- center pressure `p_w(r=0,t)/p0`;
- comparison to the analytical Mandel-Cryer response.

However, the Cryer section does not appear to add a separate implementation
recipe for the drained spherical boundary beyond the general boundary section.
The likely intended implementation is therefore the paper's general
free-surface / dummy-particle pore-pressure boundary treatment.

## Boundary Particles / Ghost / MLS Evidence

The converted main paper gives direct evidence for:

- dummy/boundary particles around solid boundaries;
- boundary stress extrapolation from domain particles;
- flexible confined boundary conditions for Neumann traction / confining stress;
- free-surface detection for pore-pressure Dirichlet boundaries;
- MLS extrapolation of pore pressure to boundary particles for Neumann
  pore-pressure boundaries.

It does not provide evidence that the Cryer drained boundary was implemented
with the local spherical ghost or local five-point virtual quadrature now used
by our mode `3`.

## Can This Be Directly Mapped To Current PR LapPorePress / LapZ?

Only partially.

The paper's PR operator needs neighbor pore-pressure values, and the paper
therefore supplies boundary pore-pressure states through dummy/boundary
particles or MLS extrapolation. Our current mode `3` supplies virtual sample
values directly to `LapPorePress`/`LapZ`, but it does not reconstruct a
consistent boundary-particle hydraulic state from the domain.

For a faithful implementation, the closer route is:

```text
boundary/free-surface detection
-> boundary hydraulic state assignment/extrapolation
-> include those boundary states in the PR operator
```

rather than continuing to add stronger material-side spherical ghost samples.

## Difference From Current Mode 3

| Item | Original paper direction | Current mode 3 |
|---|---|---|
| Drained surface | free-surface zero `p_w` or boundary/dummy value | prescribed virtual spherical samples |
| Boundary particles | part of boundary machinery | not required by quadrature mode |
| Neumann/no-flux | MLS extrapolation to boundary particles | not implemented for curved Cryer in mode 3 |
| Consistency | MLS zero/first-order for pressure extrapolation | no MLS reconstruction |
| Cryer surface | drained exterior physical surface | local near-surface shell approximation |
| Material pressure | not stated as clamp | not clamped except diagnostic mode `2` |

## Audit Conclusion

C5d did not fail simply because its numerical weights were too weak. It also
does not follow the boundary implementation direction described in the original
u-pw paper. The paper points toward boundary-particle pore-pressure state and
MLS/free-surface treatment, whereas C5d is a material-side virtual quadrature
around an ideal sphere.

Before another mode-3 source patch, the Cryer path should pivot toward a
faithful boundary-particle / MLS-style hydraulic reconstruction design.
