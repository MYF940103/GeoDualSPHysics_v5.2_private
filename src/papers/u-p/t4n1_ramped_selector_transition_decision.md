# T4n1 Ramped Selector Transition Decision

## Question

T4n showed that an abrupt all-surface-to-lateral selector switch is execution
stable but not mechanically neutral. This note decides whether the next step
should be a ramped selector transition.

## Direct Literature Support

There is no direct Zhao or u-pw reference for a time-ramped selector transition
from all-surface `f_i` confinement to lateral-only confinement.

Zhao supports:

- all-surface confinement through kernel truncation;
- `f_i` near-boundary selection for large deformation;
- initial hydrostatic confinement;
- damping when confinement is suddenly applied;
- smooth particle layouts;
- `l0/ln` rescaling for confinement magnitude.

The references do not prescribe:

- a lateral selector start time;
- a continuous selector weight;
- a ramp from cap/edge/lateral support to lateral-only support.

## What A Ramped Selector Would Solve

A ramped selector would solve a numerical target-set discontinuity introduced
by our staged workflow. In T4n the active set changes from `208` all-surface
particles to `112` lateral particles. The abrupt removal of cap and edge
confinement support raises `q`, shifts `p'`, and reintroduces negative pore
pressure even with feedback disabled.

This is a real numerical problem, but it is not the same as proving a physical
triaxial boundary condition. A ramp would smooth the transition between two
discrete boundary target sets.

## Does It Pollute Validation?

It can pollute validation if the ramp itself is used during the period being
compared against theory or experiment. It is safer if used only as a
pre-loading staging protocol:

1. equilibrate under all-surface isotropic confinement;
2. transition smoothly or through restart to a lateral-only triaxial boundary;
3. wait until `q`, velocity, `DivVel`, and pore-pressure rate settle;
4. begin axial loading only after the ramp is finished.

Even then, the protocol must be reported as an engineering staging choice, not
as a Zhao boundary law.

## Alternatives

### Restart-Based Equilibrium

This is more defensible conceptually: Stage A produces an equilibrated state,
then Stage B restarts with lateral-only confinement and checks whether the
state survives. The risk is practical: restart must preserve stress, pore
pressure, velocity, particle classification, and relevant history fields.

### Initial Stress + Damping + All-Surface Only

This is most reference-supported, but it does not by itself provide the
lateral-only condition needed for axial triaxial loading with top/bottom
platens. It should remain the isotropic pre-equilibrium state.

### Improved Geometry / Smooth Cylinder

This is directly supported by Zhao and may reduce cap/edge sensitivity. It is
not a quick continuation of the current reduced-cylinder case, but it addresses
a root source of selector discontinuity.

### `l0/ln` Rescaling

This is reference-supported for maintaining confinement magnitude during large
deformation, but it does not directly solve the all-surface-to-lateral target
set discontinuity.

## Decision

Do not make ramped selector transition the next main source task. It is too
numerical to become the formal validation path at this point.

It is acceptable as a diagnostic if tightly constrained:

- off by default;
- used only before axial loading;
- reported as a staging protocol;
- followed by a no-ramp observation window to verify the final lateral-only
  state is stable;
- not combined with feedback caps or reduced feedback scale as a validation
  claim.

## Recommendation

Prefer restart/equilibration and reference-supported stabilization before a
ramped selector patch:

1. audit and validate restart-based Stage A -> Stage B transfer;
2. keep Stage A as Zhao all-surface `f_i` confinement with initial stress and
   damping;
3. restart or switch to lateral-only only after equilibrium;
4. do not reintroduce axial loading until the lateral-only, feedback-off state
   remains hydrostatic enough and full-feedback behavior is understood.

If restart fidelity is blocked, then a ramped selector transition can be used
as T4n2 strictly as a diagnostic staging protocol, not as the formal
paper-faithful route.
