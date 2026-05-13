# T4n1 Zhao Confinement Staging Audit

## Scope

This audit reviews the converted Zhao flexible confinement paper and the local
implementation review to decide which confinement-staging treatments are
directly supported by the reference and which are our own engineering workflow.
No source code or simulations were run in T4n1.

Primary local sources:

- `zhao_flexible_confined_boundary_conditions_sph.md`
- `zhao_flexible_confined_boundary_conditions_review.md`
- T2 Zhao audit/design notes
- T4k, T4l, T4m, and T4n reports

## Zhao's Core Confinement Mechanism

Zhao et al. formulate confinement as an isotropic stress-like pair contribution
in the SPH momentum equation. The key point is not an explicit surface search:
for a constant confinement field, complete kernel support cancels the
contribution in the interior, while truncated support near a free boundary
produces an inward surface traction.

This is why the T4m all-surface route is closer to Zhao than T4l's mixed
lateral pair force plus explicit cap support. The paper's confinement term is
intended to be one mechanism acting on the currently free surface, not a
patchwork of separately discretized cap and lateral force routes.

## Initial Hydrostatic Confining Stress

Zhao explicitly tests confinement with and without imposing an initial stress
state equivalent to the confining pressure. In the initial-stress case, the
specimen reaches the target confinement immediately. Without it, the specimen
requires many numerical cycles and damping to settle after the sudden
application of confining stress.

This supports our `InitialStressMode=1` direction. It also explains why T4k
found that writing the initial hydrostatic effective stress was not enough by
itself: the initial stress must be externally balanced by a compatible
confinement mechanism. A free-surface particle cloud with initialized stress
but incomplete external support is not a quiet equilibrium.

## Sudden Confinement Stress Waves

Zhao discusses excessive stress wave propagation when confinement is suddenly
applied without the matching initial stress condition. The reference treatment
is not to tune a feedback limiter; it is to either impose the equivalent
initial stress or use damping while the specimen equilibrates.

This supports a pre-axial confinement-equilibration stage. It does not directly
support arbitrary feedback caps or a reduced pore-pressure feedback scale as a
final validation workflow.

## Damping

Zhao uses viscous damping in the no-initial-stress confinement verification to
stabilize stress waves. The paper states that the damping improves numerical
stability and does not change the final confinement result in that verification.

For GeoDualSPHysics, damping during the confinement stage is reference
supported as long as it is documented as an equilibration aid and removed or
held fixed consistently before validation loading. Damping should not be used
to hide an unresolved feedback instability in the final stress-path comparison.

## Kernel Completeness Selector `f_i`

For large deformation, Zhao limits the confinement term to particles on or near
the free boundary using the kernel completeness index:

```text
f_i = sum_j (m_j / rho_j) W_ij
```

The reported empirical thresholds are about `f_i <= 0.55` in 2D and
`f_i <= 0.70` in 3D. This strongly supports the T3 `f_i` diagnostic and the
T4 all-surface `f_i` confinement stage.

The threshold is empirical. It is reference supported as a starting selector,
not as a universal calibrated constant.

## Large-Deformation `l0/ln` Rescaling

Zhao proposes rescaling the confinement contribution by an initial/current
confining-term magnitude ratio, commonly summarized as an `l0/ln` correction.
The purpose is to preserve confinement magnitude as particle separation evolves
under large deformation.

This is a reference-supported future enhancement. It has not yet been tested in
the current GeoDualSPHysics triaxial line. It is more defensible than an
arbitrary force cap because it is tied to Zhao's confinement-magnitude
argument.

## Smooth / Fan-Shaped Particle Layout

Zhao's circular and cylindrical specimens use fan-shaped particle layouts to
create smooth boundaries and reduce boundary roughness from orthogonal cut
cells. The paper explicitly links the smooth layout to lower numerical noise.

This is directly relevant to our reduced cylinder. Current T4 results show
class/edge/cap sensitivity; a smoother cylinder layout is reference supported
and should be considered before treating selector smoothing as the only cure.

## All-Surface To Lateral-Only Selector Transition

Zhao does not describe a time-ramped selector transition from all-surface
isotropic confinement to lateral-only confinement. The triaxial setup is
organized as a confined specimen with loading platens, but the paper does not
spell out a staged target-set switch algorithm or a ramped selector weight.

Therefore, a ramped selector transition is not directly reference supported.
It can still be a reasonable numerical staging protocol if it is framed as a
way to avoid a discontinuous target-set change after isotropic equilibrium, not
as a validated physical boundary condition.

## Zhao's Triaxial Workflow

The Zhao triaxial simulations use:

- a cylindrical specimen;
- fan-shaped particle layout;
- top and bottom platen particle layers;
- fixed or free cap boundary variants;
- a constant downward top-platen speed for axial compression;
- flexible confinement to maintain lateral confinement;
- initial hydrostatic confinement state as the starting loading point in the
  reported stress paths.

The paper does not present a full u-pw coupled pore-pressure feedback loop.
It is a mechanical confinement and elastoplasticity reference, not a direct
guide for our PR pore-pressure feedback instability.

## Directly Migratable Elements

The following are directly useful for GeoDualSPHysics:

- stress-like flexible confinement via kernel truncation;
- initial hydrostatic effective stress before axial loading;
- damping during confinement equilibration;
- `f_i` near-boundary selection, with `0.70` as a 3D starting threshold;
- smooth/fan-shaped cylinder particle layout;
- `l0/ln` confinement-magnitude rescaling as a later source task.

## Not Directly Migratable

The following cannot be copied directly:

- a complete u-pw feedback activation protocol, because Zhao's paper is not a
  u-pw pore-pressure feedback paper;
- ramped all-surface-to-lateral selector transitions;
- restart-state handling for GeoDualSPHysics;
- validation of our reduced cylinder geometry, because Zhao's specimen uses a
  smoother particle layout and many more particles;
- any claim that feedback limiters are part of Zhao's method.

## T4n1 Conclusion

Zhao strongly supports initial hydrostatic stress, damping, `f_i` boundary
selection, smooth cylinder layout, and all-surface kernel-truncation
confinement for isotropic pre-equilibrium. Zhao does not directly support a
ramped selector transition. If we use such a transition, it must be labeled as
an engineering staging protocol and should be bounded by conservation and
stress-path diagnostics.
