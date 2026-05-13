# M3d2 MCC Return Robustness Design

## Problem

The M3d mild-yield MCC feedback-off platen case is numerically stable at the
SPH level (`code=0`, `excluded=0`, `DtMin=0`) but not locally clean: the final
frame has `MccReturnStatus=-3` for 8 of 407 material particles. The failed
particles are localized near the bottom interior/cap transition.

The goal is not to hide these failures. The next route should either remove
them by improving the constitutive update or clearly scope the current curves
as diagnostic only.

## Option 1: Smaller Global Loading Increment

Reduce the prescribed top-platen velocity or shorten the effective strain
increment.

Result in M3d2:

- half velocity removes final `-3` failures: final status `0:8|1:399`;
- it does not remove all intermediate `-3` episodes;
- velocity, DivVel, and PorePressRate are reduced, but mean negative pore
  pressure becomes more negative because the run lasts longer for the same
  approximate displacement.

Interpretation: the failure is increment-sensitive, but relying on global
loading reduction is a workflow workaround, not a robust constitutive fix.

## Option 2: Constitutive Substepping

Split the MCC local stress update into smaller subincrements when the strain
increment or trial-yield violation is large.

Advantages:

- directly targets the local return failure mechanism;
- preserves the global SPH time step and loading workflow;
- can be enabled only for `SoilConstitutiveModel=3`;
- provides a clear diagnostic path: substep count, retry count, failed-substep
  status, last-converged state.

Risks:

- more source work than line-search tuning;
- requires careful state rollback and output status semantics;
- may increase CPU cost in yielded regions.

This is the most defensible next patch if M3e wants clean MCC state evolution.

## Option 3: Improved Line Search / Admissibility Guard

Increase backtracking robustness and enforce admissible intermediate
`p'`, `pc`, and void-ratio states during Newton updates.

M3d2 result:

- increasing max iterations and tightening tolerance did not change the final
  failed set;
- this suggests the current issue is not just a too-low iteration cap.

A better guard is still useful, but by itself it may not be enough. It should
be bundled with substepping rather than used as the only fix.

## Option 4: Safe Failure Fallback

If return mapping fails, keep the last converged substep, mark the particle
with an explicit failure/recovered status, and do not silently fall back to
elastic.

This is a safety mechanism, not validation. It prevents one bad local return
from poisoning state variables, but any curve containing recovered failures
must be labeled accordingly.

## Recommendation

Do not proceed directly to M3e clean package consolidation. The minimal next
technical step should be M3d3:

1. Add opt-in MCC constitutive substepping.
2. Add admissibility guards for `p'`, `pc`, and void ratio during local Newton
   line search.
3. Preserve explicit return statuses and never silently use elastic fallback.
4. Re-run the M3d2 baseline and half-velocity diagnostics to confirm that
   `ReturnStatus=-3` disappears or is converted into a clearly marked
   recovered state.

M3d2 curves remain useful as reduced diagnostics, but not as clean MCC
validation curves.

