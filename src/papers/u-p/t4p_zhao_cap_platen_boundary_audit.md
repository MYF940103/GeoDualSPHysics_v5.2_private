# T4p Zhao Cap / Platen Boundary Audit

## Purpose

T4o showed that the current `CapConfiningStress` acceleration patch does not
preserve the all-surface hydrostatic confinement state. This audit revisits the
Zhao flexible confinement paper to separate two different boundary roles:

- flexible lateral confinement;
- top/bottom loading platen boundary conditions.

## Zhao Top / Bottom Boundary Treatment

The Zhao paper's triaxial section describes a cylindrical specimen with radius
`25 mm` and height `100 mm`. The loading platens are not represented by a
single cap acceleration patch. They are represented by extra particle layers:

- five additional particle layers are created at the top and bottom of the soil
  domain;
- the bottom platen remains fully fixed;
- the top platen is assigned a constant downward velocity of `10 mm/s`;
- the paper considers fixed-cap and free-cap variants for the top loading
  platen.

This is a displacement/velocity boundary construction, not a stress-control cap
force construction.

## Lateral Confinement Versus Platens

Zhao's flexible confinement method is intended for confining stress applied to
free or flexible boundaries. It uses the kernel truncation of a stress-like
confining term to create boundary-normal traction without explicitly tracking
surface normals or areas.

For strict triaxial loading this maps most naturally to the lateral membrane or
free cylindrical surface. The top and bottom platens are a different mechanical
boundary:

- the bottom platen supplies a fixed support;
- the top platen supplies prescribed axial motion;
- the axial reaction is measured through the platen/contact response;
- the platen layers are not simply another place to apply the same isotropic
  flexible confinement term.

The Zhao review already captured this implication: lateral flexible confinement
should be restricted to the lateral membrane/free surface, not the top/bottom
loading platens.

## Isotropic And Axial Stages

Zhao supports starting from a hydrostatic confinement state. The paper also
notes that sudden confinement can launch stress waves, so damping or equivalent
initial hydrostatic stress is important during confinement equilibration.

The triaxial loading path is therefore best interpreted as:

1. prepare an initially confined specimen;
2. maintain lateral confining pressure through the flexible confinement term;
3. hold the bottom platen fixed;
4. prescribe top platen velocity for axial compression;
5. measure global and local stress paths during loading.

Zhao does not describe a production route where a separate cap-normal
acceleration patch is applied directly to soil cap particles.

## Extra Boundary Layers

The extra top/bottom layers matter. They provide a platen-like kinematic
boundary and keep the axial loading mechanism separate from the soil material
measurement region. This is different from the current reduced T4 cases, where
the top "cap" is actually a soil `mkfluid=1` material layer that participates in
stress update and pore-pressure update.

## Missing Pieces In The Current Branch

The current branch has useful building blocks:

- `FlexibleConfiningStress` with `f_i` selection;
- `InitialStressMode=1`;
- restart of stress and pore pressure;
- `AccInput` for body acceleration on a material group;
- fixed/moving/floating boundary infrastructure inherited from DualSPHysics.

The pieces missing for a Zhao-like triaxial cap/platen workflow are:

- a clean top/bottom platen layer separated from soil material;
- prescribed top platen velocity/displacement rather than body acceleration on
  soil particles;
- fixed bottom platen support;
- cap/platen exclusion from pore-pressure/stress-path measurement;
- axial reaction/force output from the platen;
- an explicit decision about whether platen layers are boundary particles,
  floating/moving bodies, or a special material/platen proxy.

## Direct Transfer To GeoDualSPHysics

Directly transferable:

- lateral flexible confinement via Zhao-style `f_i` boundary selection;
- smooth/fan-shaped cylinder layout target;
- initial hydrostatic effective stress;
- damping/equilibration before loading;
- restart-based staging if restart fidelity is maintained.

Not directly transferable without design:

- top/bottom platen contact and prescribed velocity;
- axial reaction force measurement;
- free-cap versus fixed-cap platen behavior;
- whether current mDBC/fixed/moving boundary machinery is adequate for solid
  skeleton triaxial contact.

## Conclusion

Zhao does not support the current `CapConfiningStress` patch as a production
triaxial cap formulation. The next production-like route should model
top/bottom platens as kinematic boundary layers and use
`FlexibleConfiningStress` for lateral confinement.
