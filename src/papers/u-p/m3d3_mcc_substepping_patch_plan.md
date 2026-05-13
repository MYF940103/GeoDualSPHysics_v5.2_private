# M3d3 MCC Substepping Patch Plan

## Objective

M3d3 should make the CPU MCC return mapping robust enough for the feedback-off
platen baseline without changing the PR pore-pressure equation, Flexible
ConfiningStress physics, GPU code, or non-MCC constitutive branches.

## Proposed XML Parameters

All defaults must preserve M3c/M3d behavior.

```text
MccSubstepMode=0
  0 = disabled, old behavior
  1 = fixed local substeps when plastic trial is detected
  2 = adaptive local substeps based on trial violation / strain increment

MccMaxSubsteps=1
  default 1 keeps old behavior

MccSubstepStrainThreshold=0
  <=0 disabled
  >0 trigger adaptive subdivision when local strain invariant exceeds threshold

MccSubstepYieldThreshold=0
  <=0 disabled
  >0 trigger adaptive subdivision when trial normalized yield violation exceeds threshold

MccFailedReturnRecovery=0
  0 = hard failure status only, old behavior
  1 = keep last converged substep and mark recovered failure
```

## CPU Algorithm

For `SoilConstitutiveModel=3` only:

1. Compute the full strain increment for the particle.
2. Choose `nsub` from fixed or adaptive rules.
3. Store a local copy of stress and MCC state before the first substep.
4. For each substep:
   - apply `strain_increment / nsub`;
   - run the existing MCC local Newton return;
   - reject non-admissible intermediate states (`p' <= cutoff`, `pc <= 0`,
     invalid void ratio);
   - update the local copy only after convergence.
5. If a substep fails:
   - retry with increased substep count if still below `MccMaxSubsteps`;
   - if recovery is enabled, write the last converged state and a non-silent
     return status;
   - otherwise keep the explicit failure status and do not pretend convergence.

## Diagnostics

Add or extend MCC outputs:

- `MccSubstepCount`;
- `MccSubstepRetryCount`;
- `MccRecoveredFailureFlag`;
- `MccLastFailedSubstep`;
- `MccReturnStatus` values that distinguish true convergence, recovered
  partial convergence, tension cutoff, line-search failure, and max-substep
  failure.

## Regression Tests

1. M3a standalone parity should remain unchanged when substepping is disabled.
2. Existing elastic, DP, and DP-softening smoke cases should be unchanged.
3. M3c high-pc MCC should remain elastic-like.
4. M3d2 mild baseline should remove or explicitly recover the final `-3:8`
   failures.
5. Half-velocity M3d2 should not regress.
6. GPU Release should still compile and hard-error for `SoilConstitutiveModel=3`.

## No-Go Criteria

- Silent fallback to elastic.
- Changes to non-MCC model behavior.
- Changes to PR pore-pressure update.
- Changes to FlexibleConfiningStress force formula.
- Treating recovered-failure curves as strict MCC validation.

