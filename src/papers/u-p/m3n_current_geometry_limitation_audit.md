# M3n Current Geometry Limitation Audit

## Scope

M3n audits why the current reduced triaxial specimen geometry is a weak basis
for clean MCC return validation.  This is a geometry/workflow audit only.  No
solver source, MCC return mapping, PR pressure update, or
FlexibleConfiningStress physics is changed.

## Current Generation Route

The current specimen is generated directly in the XML with GenCase
`drawcylinder` commands:

- bottom platen: `mkbound=2`, cylinder radius `Rplate`;
- top platen: `mkbound=1`, cylinder radius `Rplate`, prescribed vertical
  motion through `<motion>`;
- specimen: `mkfluid=0`, cylinder radius `R=0.03 m`, height `H=0.10 m`;
- nominal spacing: `Dp=0.01 m` in the established M3m baseline;
- smoothing length: `h=1.8*Dp`.

GenCase rasterizes these shape commands on a Cartesian point lattice.  The
surface is therefore a cut-cell style cylinder rather than a ring/fan-aligned
particle cloud.

## Dp=0.01 Particle Set

For the self-contained M3n `overhang045_ref` case, GenCase produces:

```text
specimen particles       = 407
fixed bottom platen      = 254
moving top platen        = 194
edge/corner specimen     = 112
cap/edge specimen        = 148
measurement core         = 25
```

The top/bottom edge is represented by a small number of Cartesian lattice
points.  This is enough for a reduced diagnostic but coarse for a local
plastic return problem whose difficult particles are exactly at the
platen/cap/edge transition.

## Why M3m Trimmed/Stepped Geometry Did Not Realize

M3m attempted XML-level cap trimming and stepped cap transitions.  At
`Dp=0.01 m`, those shape edits did not change the generated material particle
set:

```text
specimen particle count          = 407
cap-zone particle count          = 148
added/removed vs reference       = 0 / 0
max cap radius                   = 0.03162 m
```

The intended trim/step radii fell between the available Cartesian particle
locations, so the same lattice points remained inside the generated shapes.
The XML geometry changed, but the realized particle cloud did not.

## Edge Support Limitation

M3n postprocessing confirms that the reduced Cartesian boundary has lower
edge/cap support than the interior.  For the `Dp=0.01` overhang045 reference:

```text
edge support/core ratio          = 0.8078
edge specimen-neighbor proxy     = 68.1
core specimen-neighbor proxy     = 158.0
cap support/core ratio           = 0.8529
cap specimen-neighbor proxy      = 77.2
```

The edge ring is the same region where M3k/M3l/M3m localized the hard
`ReturnStatus=-3` particles.  Its lower neighbor/support completeness gives a
credible boundary-induced mechanism: local strain/stress paths near the
platen/cap/lateral-surface intersection are less regular than the measurement
core.

## Suitability for Clean Validation

The current `Dp=0.01` Cartesian cylinder is suitable for reduced diagnostic
work because it is small, stable, and easy to compare across XML variants.
It is not a strong candidate for clean MCC return validation because:

- edge/corner support is truncated;
- cap/edge smoothing attempts may not alter the realized particle cloud;
- difficult return states are localized exactly where the Cartesian layout is
  least smooth;
- the measurement core is clean, but validation cannot rely only on excluding
  the failure source.

## Required Level of Geometry Change

A meaningful geometry change must alter the actual particle support near the
cap/lateral/platen intersection, not merely the XML shape boundary.  Practical
options are:

1. lower `Dp` enough that rounded/trimmed edge geometry is represented by a
   different particle set;
2. generate a radial/fan-like ring layout for the specimen boundary;
3. use a hybrid Cartesian core plus smoother boundary shell;
4. accept a caveated reduced MCC route without claiming clean validation.

M3n tests option 1 as the smallest executable diagnostic.
