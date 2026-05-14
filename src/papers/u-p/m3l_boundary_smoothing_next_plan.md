# M3l Boundary Smoothing Next Plan

## Why M3l Should Be Boundary-First

M3j-B and M3k both point to the same mechanism: remaining MCC return failures
are localized near cap/platen/edge regions.  M3k adds dense-output evidence that
the first hard `ReturnStatus=-3` particles have:

- reduced neighbor/support completeness;
- elevated local velocity-gradient and shear-rate proxies;
- positive `p'` but high yield residual and return burden;
- edge/cap/platen-adjacent locations.

That pattern is more consistent with a boundary-induced local strain path than
with a global MCC constitutive failure.

## Option 1: Platen / Specimen Interface Smoothing

Goal:

Reduce local strain concentration where moving/fixed platens interact with the
soil specimen.

Candidate changes:

- adjust initial platen/specimen spacing;
- add a short buffer/transition zone;
- test slightly softer or smoother platen contact geometry if available through
  XML;
- keep explicit top platen and fixed bottom platen;
- keep `PorePressureFeedback=0`.

Pros:

- directly targets the recurring platen-adjacent trigger;
- preserves the explicit platen workflow;
- can likely be tested with XML/GenCase changes before source work.

Cons:

- still reduced and geometry-specific;
- may require careful documentation so smoothing is not mistaken for MCC model
  validation.

This is the recommended first M3l task.

## Option 2: Edge / Corner Smoothing

Goal:

Reduce the sharp mixed-boundary corner where lateral confinement, cap zones, and
platen kinematics meet.

Candidate changes:

- round or soften the cylinder edge/corner geometry;
- add an edge transition ring;
- test whether failed `-3` records disappear before changing constitutive code;
- keep edge/cap particles excluded from strict measurement metrics.

Pros:

- directly targets the strongest dense-output `-3` onset zone;
- aligns with the idea that Zhao-style layouts avoid harsh support
  discontinuities.

Cons:

- may require geometry generation edits;
- edge exclusion improves reporting but does not solve the physics by itself.

Use this after the platen/specimen interface check, or combine it if the XML
geometry change is very small.

## Option 3: Smooth / Fan-Like Cylinder Layout

Goal:

Move toward the smoother particle layouts used in the reference-style triaxial
workflows.

Candidate changes:

- regenerate the reduced cylinder with smoother radial/fan-like particles;
- avoid sharp edge rings with low support completeness;
- retest the same mild MCC feedback-off case.

Pros:

- most physically faithful long-term route;
- addresses support truncation and anisotropy at their source.

Cons:

- higher cost than a local interface diagnostic;
- may change many baseline comparisons at once.

Keep this as the stricter follow-up if simple interface smoothing confirms the
boundary-induced mechanism.

## Option 4: Local Return Robustness Only

Further MCC return-mapping patches should not be the next primary route.  M3d3,
M3f, and M3h already showed that substepping, smoother loading, and admissible
line-search variants do not clean the original local failure pattern.

Return-mapping work should resume only if a smoothed platen/edge geometry still
produces the same failed particle locations and local strain-path signatures.

## Recommended M3l Task

Run a minimal XML/geometry diagnostic:

1. start from the M3k mild MCC dense-output case;
2. adjust only the platen/specimen interface spacing or add a small transition
   buffer;
3. keep `PorePressureFeedback=0`;
4. keep the same MCC parameters;
5. keep dense output around first failure onset;
6. compare failed particle locations, support ratio, velocity-gradient proxy,
   `p'`, `q`, and `ReturnStatus` timeline against M3k.

Success criterion:

```text
all saved frames have ReturnStatus=-3 count = 0
no new ReturnStatus=-5 fallback
pc/e/plastic strain remain smooth
reaction, p'-q, and pore pressure remain bounded
```

If this does not work, move to edge/corner smoothing or a smooth/fan-like layout
before making another MCC return-mapping patch.

Full pore-pressure feedback and GPU remain deferred.
