# M3j Boundary-First Fix Recommendation

## Objective

M3j-B asks whether the next clean-MCC step should continue return-mapping
patches or address the platen/specimen/edge boundary first.  Based on the
localization evidence, the next step should be boundary-first.

## Option 1: Platen/Specimen Interface Smoothing

Concept:

- add or redesign a transition layer between platen and specimen;
- check platen/specimen spacing and contact support;
- reduce abrupt bottom fixed-platen strain spikes;
- retain explicit top/bottom platen workflow.

Pros:

- directly targets the recurring bottom/top cap and edge zones;
- remains physically interpretable;
- does not alter MCC constitutive physics.

Cons:

- may require XML/geometry changes or regenerated particle layouts;
- needs dense output to verify local neighbor and strain improvements.

## Option 2: Exclude Edge/Cap-Adjacent Particles From Clean Metrics

Concept:

- keep all particles in the simulation;
- report clean validation only on a core/measurement material set;
- track boundary failures separately.

Pros:

- useful for reporting reduced diagnostics;
- easy to implement in postprocessing.

Cons:

- does not fix the physical/numerical local return failure;
- cannot support a strict clean solver validation claim.

This can be used as diagnostic reporting only.

## Option 3: Smooth Cylinder / Fan-Like Particle Layout

Concept:

- rebuild the specimen with smoother circular/fan-like layout;
- reduce sharp edge/corner support artifacts;
- align better with Zhao-style confinement examples.

Pros:

- most consistent with a strict triaxial benchmark route;
- addresses support truncation and edge geometry at the source.

Cons:

- higher setup cost;
- may need GenCase/layout tooling work;
- should be staged after a small diagnostic confirms neighbor/strain issues.

## Option 4: Local Strain Increment Regularization Near Platen

Concept:

- locally limit strain increment entering MCC near platen/edge particles.

Pros:

- may reduce return failures quickly.

Cons:

- physically ambiguous;
- can hide boundary artifacts;
- should not be a validation route unless strongly justified.

This is not recommended as the first fix.

## Option 5: Continue Return Mapping Patches

Concept:

- continue improving admissible Newton, closest-point return, or projection.

Pros:

- still useful because the local return must be robust.

Cons:

- M3d3/M3f/M3h already show that substepping, ramping, and admissible
  backtracking do not clean the reduced platen geometry;
- risks treating a boundary/geometry-induced strain path as a constitutive
  algorithm problem.

This should be secondary unless boundary diagnostics disprove the boundary
cause.

## Recommended Minimal Next Task

The next task should be:

```text
M3k: very-short dense-output platen/edge diagnostic
```

Recommended contents:

1. reuse mild MCC feedback-off platen case;
2. run only through first failure onset;
3. output dense PartCsv around early failure frames;
4. compute neighbor count, kernel support/completeness proxy, local velocity
   gradient, failed-vs-nearby-nonfailed state differences;
5. do not change MCC physics;
6. do not use fallback;
7. do not enable full feedback or GPU.

If M3k confirms local neighbor/strain concentration, then proceed to:

- platen/specimen interface smoothing; or
- smoother/fan-like cylinder layout.

If M3k disproves boundary concentration, then return to a deeper MCC local
return mapping redesign.

## Recommendation

Do not continue piling return-mapping patches onto the current geometry as the
primary route.  The evidence now supports a boundary-first investigation.
