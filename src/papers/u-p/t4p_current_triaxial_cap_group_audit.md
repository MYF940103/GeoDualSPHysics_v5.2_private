# T4p Current Triaxial Cap Group Audit

## Scope

This audit checks the current T1/T3/T4/T4o reduced triaxial XMLs and how their
particle groups are used. No simulation was run for T4p.

## Current Reduced Cylinder Layout

The recent cylindrical T4 cases define only material particles:

```xml
<setmkfluid mk="0" />
<drawcylinder ... z="0" to z="#Hcyl-Dp" />
<setmkfluid mk="1" name="AxialLoadLayer" />
<drawcylinder ... z="#Hcyl-Dp" to z="#Hcyl" />
```

Therefore:

- the specimen bulk is `mkfluid=0`;
- the top axial/load layer is `mkfluid=1`;
- the bottom cap region is not a separate mk; it is a geometric subset of
  `mkfluid=0`;
- there are no true top/bottom `mkbound` platen layers in the T4 cylinder XMLs.

## Original Smoke Scaffold

The older `CaseUndrainedTriaxial_PR_Smoke_Def.xml` contains boundary geometry
for a reduced rectangular/column smoke and also splits material into
`mkfluid=0` and `mkfluid=1`. That scaffold is useful historically, but it is
not the current strict cylindrical triaxial platen workflow.

## AccInput Target

`AccInput` in the current T1/T3/T4 axial cases targets `mkfluid=1`. This means
the top layer is not a rigid platen. It is deformable soil material receiving a
body acceleration.

Consequences:

- the layer participates in stress update;
- it participates in pore-pressure update;
- it can participate in pore-pressure feedback unless class filters exclude it;
- it can enter measurement/postprocessing unless explicitly excluded;
- it does not automatically provide a clean platen reaction force.

## FlexibleConfiningStress Participation

Depending on the case:

- all-surface confinement selects low-`f_i` particles across lateral, cap, and
  edge regions;
- lateral-only confinement selects only the cylinder lateral class;
- cap and edge regions may be excluded by lateral selection.

In the current reduced cylinder, these are still material particles. The
selection is a force/diagnostic filter, not a separate boundary type.

## PorePressureFeedback Participation

The feedback class-filter infrastructure can exclude caps, edges, confinement
targets, or apply interior-only feedback. Without those filters, top/bottom and
edge material particles are eligible for feedback because they are normal fluid
particles.

This is appropriate for diagnostic studies but not yet a clean platen model.

## Stress Update Participation

`mkfluid=0` and `mkfluid=1` are both material particles. They both participate
in the skeleton/effective stress update and in the PR pore-pressure update.
There is no source-level separation saying "this top group is a platen, not
soil".

## Measurement Contamination Risk

Any p-q proxy that includes cap/top-layer particles will mix platen/loading
behavior with soil response. T4 postprocessing already mitigates this by using
center-core and class-filtered regions, but the XML itself does not create a
clean platen/non-platen distinction.

## Audit Answers

1. Top cap particles in current T4 cylinder XMLs are `mkfluid=1` material
   particles.
2. Bottom cap particles are geometric bottom-cap subsets of `mkfluid=0`
   material particles.
3. Lateral specimen particles are mostly `mkfluid=0` material particles.
4. AccInput is applied to the top material layer, not to a boundary/platen
   layer.
5. Top/bottom particles can participate in `FlexibleConfiningStress` depending
   on selectors.
6. Top/bottom particles can participate in `PorePressureFeedback` unless
   filtered.
7. Top/bottom particles participate in stress update because they are material.
8. For strict triaxial testing, top/bottom should be treated as platen boundary
   layers rather than soil measurement particles.
9. Current cap groups can contaminate measurement regions if the region is not
   carefully defined.
10. The current reduced cylinder does not yet have a clear specimen/platen
    separation.
