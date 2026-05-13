# T4q Platen Source Patch Plan

## Trigger

This plan is only needed if the XML-only `mkbound` platen route is not
adequate. T4q should not implement this patch unless the smoke tests show a
specific blocker.

## Minimal Patch Scope

Any source patch should be limited to platen boundary control and diagnostics:

- top platen prescribed velocity or displacement override;
- bottom platen fixed constraint;
- reaction force accumulation;
- measurement exclusion tags or output;
- optional platen motion schedule.

The patch must not modify:

- PR pore-pressure update;
- soil constitutive model;
- Cryer boundary logic;
- `FlexibleConfiningStress` physics;
- DP/MCC paths.

## Candidate Interface

Possible future XML keys:

| Parameter | Meaning |
| --- | --- |
| `PlatenBoundaryMode` | `0`: off, `1`: CPU prescribed platen control |
| `TopPlatenMkBound` | top moving boundary mk |
| `BottomPlatenMkBound` | bottom fixed boundary mk |
| `TopPlatenVelocityX/Y/Z` | prescribed top platen velocity |
| `TopPlatenStartTime` | time to start top motion |
| `TopPlatenEndTime` | time to stop top motion |
| `SavePlatenDiagnostics` | output motion/reaction summaries |

Defaults must preserve old behavior.

## Diagnostics Needed

The source patch should output:

- top platen displacement and velocity;
- bottom platen displacement;
- accumulated top/bottom reaction force if available;
- net platen force balance;
- specimen-only axial strain proxy;
- particle counts by platen/specimen group.

## GPU Status

If implemented, this should be CPU-only first. GPU should hard-error for
non-default platen controls until the CPU formulation passes elastic smoke
tests and reaction/stress diagnostics are defined.

## No-Go Criteria

Do not proceed to DP/MCC or paper reproduction if:

- prescribed platen motion cannot deform the specimen coherently;
- bottom platen drifts;
- measurement regions include platen particles;
- reaction force cannot be measured or at least reliably estimated;
- lateral confinement and platen motion are incompatible.
