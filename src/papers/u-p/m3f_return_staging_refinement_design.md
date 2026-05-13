# M3f MCC Return and Staging Refinement Design

## Goal

M3f tries to convert the M3d3 mild MCC feedback-off platen case into a clean
reduced validation candidate without changing the MCC physical model.

Clean means:

- `code=0`;
- `excluded=0`;
- `DtMin=0`;
- no `ReturnStatus=-3` in any saved frame;
- no `ReturnStatus=-5` partial fallback;
- smooth `pc`, void ratio, and plastic strain histories;
- bounded pairwise reaction, p'-q, velocity, and pore pressure.

## Route 1: Smoother Platen Loading Ramp

This route changes only the XML motion staging. It ramps the top platen
velocity from zero to the target value before continuing at the target
prescribed velocity.

Expected benefit:

- reduce abrupt early local strain changes near the platen/specimen interface;
- avoid changing MCC return equations.

Risk:

- it is a workflow/staging change, not a constitutive fix;
- it may prolong the early transition window and create more intermediate
  admissibility failures.

M3f result:

- not clean;
- original-rate ramp reduces final `-3` but introduces final `-1`;
- half-speed ramp worsens transient failures relative to half-speed without
  ramp.

## Route 2: Earlier Adaptive Substepping

This route improves `MccSubstepMode=2` so substeps can be triggered before a
failed return:

- `MccMinSubsteps`;
- `MccSubstepStrainThreshold`;
- `MccSubstepYieldDistanceThreshold`;
- `MccSubstepTriggerReason` output.

Trigger reasons are:

| code | meaning |
| ---: | --- |
| 0 | single-step/no trigger |
| 1 | fixed substepping |
| 2 | strain-increment threshold |
| 3 | trial yield-distance threshold |
| 4 | minimum substep count |
| 5 | retry after failed return |

Expected benefit:

- split hard local increments before Newton fails;
- keep the failure path explicit and avoid partial fallback.

Risk:

- more substeps can expose more admissibility failures if the trial path itself
  is locally poor;
- thresholds need careful interpretation and cannot be tuned into a hidden
  constitutive limiter.

M3f result:

- implemented;
- not clean with the tested thresholds;
- original-rate improved adaptive cases worsen final and transient negative
  status counts.

## Route 3: Improved Line Search and Admissibility Projection

This would change the local Newton/return implementation more deeply:

- reject non-admissible trial candidates before residual evaluation;
- use a more conservative projected step for `p'`, `pc`, and plastic
  multiplier;
- retain monotone progress in yield residual where possible;
- avoid stepping into tension-cutoff states.

Expected benefit:

- targets the observed `-1` and `-3` failure mechanisms directly.

Risk:

- larger source change;
- requires renewed single-point parity and SPH smoke regression.

M3f does not implement this route. It is the likely next source-level path if
clean MCC validation remains the goal.

## Route 4: Local Boundary-Region Staging

This route would smooth the platen-near deformation path or modify the
boundary workflow. It should not introduce region-specific constitutive
behavior.

Expected benefit:

- addresses edge/platen strain concentration.

Risk:

- can become too numerical or geometry-specific;
- hard to justify as validation unless tied to a physical platen/contact
  model.

M3f does not implement this route.

## Recommended Interpretation After M3f

The M3f minimal combination of smoother loading and improved adaptive
substepping does not yield a clean candidate. The best diagnostic route is
quarter-speed adaptive because it has the fewest bad frames, but it still has
transient `-3` failures.

If the goal is clean validation, the next step should not be M3g clean
consolidation. It should be a targeted local-return improvement stage:

1. strengthen admissible Newton projection;
2. retest single-point parity;
3. rerun the mild MCC platen case without partial fallback;
4. keep full feedback and GPU deferred.

