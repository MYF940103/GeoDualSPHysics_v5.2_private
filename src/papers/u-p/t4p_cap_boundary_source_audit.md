# T4p Cap Boundary Source Audit

## Fixed, Moving, Floating, And Fluid Particles

DualSPHysics already has fixed, moving, floating, and fluid particle types. The
case parser and `JCaseParts` infrastructure distinguish `mkbound` and
`mkfluid`, and the standard interaction loop can include fluid-bound and
fluid-floating interactions.

The current T4 reduced cylinder does not use this capability for platens. It
defines only `mkfluid` soil groups.

## AccInput

`JDsAccInput` can target `mkfluid` or `mkbound`, but the `mkbound` path is
checked as a floating body path. In the current triaxial XMLs, AccInput targets
`mkfluid=1`.

In `JSphCpu::PreInteractionVars_Forces`, AccInput is applied before the main
interaction loop:

```text
AccInput->RunCpu(..., Acec)
```

`JDsAccInput::RunCpu` then adds the configured linear/angular acceleration to
all selected particles. This is not a prescribed-displacement or
prescribed-velocity platen constraint. It is a body acceleration source.

Implication: AccInput is suitable for smoke testing axial response, but it is
not sufficient for strict platen loading.

## Existing Mechanical Boundary Capability

The codebase has:

- fixed boundary particles;
- moving boundary particles through motion/refmotion machinery;
- floating bodies and external/floating acceleration paths;
- mDBC/slip boundary support inherited from DualSPHysics.

However, the current u-pw triaxial workflow has not verified a platen built
from fixed/moving `mkbound` particles interacting with the deformable soil
skeleton.

## CapConfiningStress

`CapConfiningStress` is a CPU-only diagnostic patch added during T4l. It:

- classifies material particles by cylinder region;
- selects top and bottom material cap particles;
- computes total cap force as `p0*pi*R^2`;
- distributes that force as an acceleration over selected top/bottom cap
  material mass;
- skips edge-ring particles;
- does not create a boundary/platen layer;
- does not write stress;
- does not measure a reaction force from contact.

This explains the T4o result. It can be symmetric and numerically clean while
still being mechanically incompatible with the all-surface Zhao confinement
state.

## Pore Pressure And Stress Update

The PR pressure update and stress update are applied to normal fluid/material
particles. Since the current "top cap" is `mkfluid=1`, it remains part of the
soil material update. There is no source-level declaration that `mkfluid=1` is a
platen.

## Reaction / Axial Force Output

The current reduced triaxial workflow does not have a strict axial reaction
measurement. AccInput does not provide a clean platen reaction, and
`CapConfiningStress` only reports imposed cap force/acceleration diagnostics.

For a strict triaxial path, the code should output at least:

- top platen reaction force;
- bottom platen reaction force or support force;
- axial displacement/velocity;
- specimen-only stress path excluding platen particles.

## Source Enhancement Needs

A paper-faithful T4q platen workflow likely needs either:

1. an XML-only prototype using existing moving/fixed boundary layers if those
   interactions are adequate for the soil skeleton; or
2. a small source feature for prescribed velocity/displacement on a material or
   boundary platen group, with clean measurement exclusion and reaction output.

The lower-risk next step is an XML/source audit prototype with explicit
platen groups before implementing new physics.

## Audit Answers

1. Fixed boundary particles are supported generally.
2. Moving/prescribed boundary particles are supported generally through the
   motion/refmotion infrastructure, but not yet used for the T4 cylinder
   platen.
3. There is no current strict top/bottom platen group in the reduced triaxial
   XMLs.
4. AccInput is a body acceleration source, not a platen boundary condition.
5. Motion constraints and frozen particles exist for boundary particle types,
   but their use as u-pw triaxial platens is not yet validated.
6. A cap group can currently transmit stress only if it is material, but then
   it is also soil for update/measurement purposes.
7. Strict cap reaction output is missing.
8. Source enhancement is likely needed unless an existing moving-boundary XML
   route can be proven adequate in T4q.
