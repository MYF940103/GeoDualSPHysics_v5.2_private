# M3f MCC Return and Staging Refinement Plan

## Why M3f Is Needed

M3d3 confirmed that opt-in substepping and admissibility guards improve
diagnostics, but the original-rate mild MCC case is not yet clean. The baseline
and tighter-return paths finish with local `ReturnStatus=-3` particles. Fixed
and adaptive substepping at the original rate do not remove the problem. The
partial fallback path removes final `-3` only by marking `-5`, which is not a
validation setting.

The half-speed adaptive case is the cleanest final-frame route, but it is a
loading/staging diagnostic rather than proof that the original-rate return is
robust.

## Likely Causes

The current evidence points to a local return/staging problem rather than a
global MCC failure:

- failed particles are concentrated near the bottom platen/interior transition;
- all cases finish `code=0`, `excluded=0`, `DtMin=0`;
- most particles converge normally;
- increasing return iterations and tightening tolerance did not change the
  final failed set;
- slower loading removes the final failed set.

Likely mechanisms:

1. local boundary/platen strain concentration;
2. local strain increment too large for the current MCC return;
3. line search not permissive or predictive enough for the local stress path;
4. `p'` / `pc` states approach admissibility limits during some substeps;
5. abrupt loading/stress-path changes near the platen layer.

## Candidate Fixes

### Earlier Adaptive Substepping

Trigger substepping before the local return fails. Candidate triggers:

- norm of strain increment;
- trial yield overshoot;
- predicted plastic multiplier size;
- local `p'` or `pc` admissibility margin.

### Smoother Platen Velocity Ramp

The half-speed case suggests the local return is sensitive to loading rate or
increment size. A short platen velocity ramp can reduce the abrupt early local
strain concentration without changing the constitutive model.

### Local Strain-Increment Guard

Add a MCC-only diagnostic limiter for constitutive integration increments. This
must be opt-in and reported as a numerical integration guard, not a physical
change.

### Improved Line Search

Improve the local Newton line search by:

- increasing backtracking depth;
- projecting only admissible candidate states;
- rejecting candidates with nonfinite stress/state values;
- retaining last converged substep only with explicit status.

### Better Admissibility Projection

The current guard detects invalid states. M3f can test a more conservative
projection before Newton begins, especially for `p'`, `pc`, void ratio, and
plastic multiplier bounds.

### Staged Material Loading

Use a short elastic or high-pc pre-stage before mild MCC activation only as an
engineering diagnostic. This must not be presented as strict validation unless
it has a physical experimental analogue.

## Recommended Minimal Next Test

The smallest useful M3f test is:

1. original-rate mild MCC;
2. adaptive substepping enabled;
3. admissibility guard enabled;
4. an earlier substep trigger based on trial yield overshoot or strain
   increment norm;
5. no partial fallback for validation cases;
6. a separate fallback case retained only as a safety diagnostic.

The target is zero `ReturnStatus=-3` and zero `ReturnStatus=-5` in all saved
frames, not only the final frame.

## No-Go Criteria

M3f should not progress to clean validation if any validation candidate has:

- `excluded > 0`;
- `DtMin` burst;
- `ReturnStatus=-3` in any saved frame;
- `ReturnStatus=-5` in a validation run;
- nonfinite `pc`, void ratio, stress, or plastic strain;
- negative or collapsing `pc`;
- uncontrolled pore pressure growth;
- strong reaction-force discontinuity relative to M3d/M3d3;
- hidden elastic fallback.

Full pore-pressure feedback and GPU remain deferred.
