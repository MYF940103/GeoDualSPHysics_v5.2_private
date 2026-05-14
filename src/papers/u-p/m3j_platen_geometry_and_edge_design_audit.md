# M3j Platen Geometry and Edge Design Audit

## Objective

M3j audits whether the reduced explicit-platen geometry is likely to amplify
local MCC return failures near cap and edge regions.  This is a design audit,
not a new simulation.

## Current Workflow Geometry

The current T4q/T5/M3 workflow uses:

- specimen soil as `mkfluid=0`;
- top platen as a separate moving `mkbound`;
- bottom platen as a fixed `mkbound`;
- selected lateral FlexibleConfiningStress on specimen free-surface particles;
- measurement region excluding platens.

This is already a large improvement over the earlier AccInput/material-layer
route.  However, it remains a reduced explicit-platen workflow.

## Platen Layers and Interface

The current workflow uses explicit top and bottom platen particle groups, but
the retained audit data do not include a full geometric-neighbor dump.  From
the failed-return maps, the critical issue is not the existence of platens; it
is the local transition zone where:

- material particles are adjacent to a fixed or prescribed platen;
- lateral surface/free-boundary selection changes;
- cap/lateral edge rings have truncated support and mixed kinematics.

## Fixed Bottom Boundary

The bottom fixed platen is mechanically plausible, but it is also the most
rigid local support in the model.  Persistent failures in bottom cap and
bottom-edge regions indicate that local material particles can see an
unusually sharp strain path relative to the specimen interior.

This does not mean the bottom platen is wrong.  It means the reduced geometry
needs better edge/interface conditioning before strict clean MCC validation.

## Top Prescribed Velocity

The top prescribed platen motion is the correct direction for triaxial loading
workflow, but the reduced geometry may still impose localized shear or strain
concentration near the top-cap/lateral-edge intersection.  M3f ramp/adaptive
variants show prominent top-cap failures, so the top interface is also part of
the issue.

## Edge Ring

The edge ring is the most consistent failure location.  It is where:

- cap/platen boundary kinematics;
- lateral confinement/free-surface selection;
- SPH kernel support truncation;
- material return mapping

all interact.  The aggregate failed-return data show edge-corner records as the
largest class across M3d2/M3f/M3h.

## Smooth / Fan-Like Layout

Zhao-style flexible confinement workflows emphasize careful particle layout,
smooth circular/fan-like distributions, and explicit loading/fixed boundary
layers for biaxial/triaxial paths.  That matters here because a sharp reduced
cylinder edge can create local neighbor-support and strain-path artifacts that
do not represent the intended homogeneous triaxial material response.

The current reduced cylinder is useful as a development benchmark, but it is
not yet a strict paper-reproduction geometry.

## Measurement and Validation Implication

The measurement core is already cleanly separated and has very few failed
records.  That supports using core/specimen proxy curves as reduced diagnostics.
It does not justify ignoring boundary failures for clean validation, because
the solver still updates all material particles and local failures can affect
stress redistribution.

## Missing Diagnostics

The retained outputs do not include:

- neighbor count near failed particles;
- local particle distribution metrics;
- local velocity-gradient tensors;
- failed-vs-nearby-nonfailed comparison;
- per-edge contact/reaction distribution.

These should be captured in a future very-short dense-output diagnostic if the
boundary-first route is pursued.

## Conclusion

The explicit platen workflow is mechanically better than AccInput, but the
current reduced specimen/platen/edge geometry likely induces local MCC return
stress paths.  A strict MCC validation route should address the interface and
edge geometry before more return-mapping patches are layered on top.
