# T4e Feedback-Gated Confinement Report

## Purpose

T4e tests whether the reduced selected-confinement triaxial sample can first
equilibrate with pore-pressure feedback disabled or delayed, and then remain
stable when feedback is restored before axial loading.

This is still a linear-elastic diagnostic stage. It does not enter DP, MCC,
full triaxial reproduction, GPU execution, or Cryer work.

## Interface Change

The repository did not previously provide feedback timing controls, so T4e
adds a narrow CPU feedback-gating interface:

- `PorePressureFeedbackStartTime`;
- `PorePressureFeedbackRampEndTime`;
- `PorePressureFeedbackScale`.

The defaults preserve old behavior. The gate scales only the feedback
acceleration applied to the mechanical momentum equation; it does not alter the
PR pore-pressure update. GPU Release builds, but non-default feedback gating
hard-errors on GPU.

## Cases

All cases use raw-gradient selected flexible confinement, no axial AccInput,
`SoilConstitutiveModel=0`, `PorePressureBoundaryOperator=0`, and
`HydraulicElevationSource=0`.

| Case | Feedback schedule | Result |
| --- | --- | --- |
| feedback off | `PorePressureFeedback=0` | Stable over `0.005 s`. |
| delayed abrupt | start `0.003 s`, scale `1` | Unstable after feedback activation. |
| delayed short ramp | start `0.003 s`, ramp to `0.0035 s`, scale `1` | Unstable after ramp. |
| delayed long ramp | start `0.003 s`, ramp to `0.0045 s`, scale `1` | Delayed but still unstable. |
| delayed long ramp, scale 0.25 | start `0.003 s`, ramp to `0.0045 s`, scale `0.25` | No exclusions or DtMin burst, but pressure still reverses at the final frame. |

## Summary Metrics

| Case | Excluded | DtMin adjustments | Max `PorePressRate` | Reversal time | Stable gate |
| --- | ---: | ---: | ---: | ---: | --- |
| feedback off | `0` | `0` | `2.11e7 Pa/s` | none | yes |
| delayed abrupt full feedback | `391` | `469` | `1.55e13 Pa/s` | `0.004001 s` | no |
| delayed short ramp full feedback | `365` | `383` | `1.16e13 Pa/s` | `0.004253 s` | no |
| delayed long ramp full feedback | `164` | `256` | `1.30e13 Pa/s` | `0.004503 s` | no |
| delayed long ramp scale `0.25` | `0` | `0` | `1.00e11 Pa/s` | `0.005015 s` | no |

The feedback-off case extends the stable confinement-only response without
pressure reversal, particle exclusion, or DtMin adjustment. This confirms that
selected confinement can be equilibrated when the feedback acceleration is
disabled.

Restoring full feedback remains unstable even after a long ramp. Reducing the
feedback scale to `0.25` avoids exclusions in this short run and lowers the
artifact by roughly two orders relative to full feedback, but it still produces
pressure reversal at the final frame and remains several orders above the
feedback-off `PorePressRate` level.

## Interpretation

The T4d conclusion is strengthened: the immediate blocker is the active u-pw
feedback acceleration during selected-confinement equilibration. It is not
primarily axial AccInput onset, because no T4e confinement-only full-feedback
variant reaches a stable coupled state.

The full-feedback ramp result also suggests that the problem is not just a
time-discontinuity at feedback activation. The ramp delays the blow-up but does
not remove it. The scaled-feedback diagnostic points to feedback magnitude /
operator coupling as the next blocker, not lateral selection geometry.

Cap leakage remains controlled by the T3 selector infrastructure. Lateral
confinement remains coherent before the feedback-driven failure.

## Axial Loading Decision

No axial-loading T4e variant was run. The rule was to restore axial loading
only after obtaining a stable feedback-on confinement-only state. Full feedback
did not pass that gate, and the `0.25` scaled feedback case still reversed.

## Answers

1. Feedback gating did not exist before T4e; `PorePressureFeedbackStartTime`,
   `PorePressureFeedbackRampEndTime`, and `PorePressureFeedbackScale` were
   added.
2. Default behavior is preserved when these parameters are absent.
3. Confinement-only equilibration is stable with feedback off.
4. Re-enabling full feedback still triggers reversal and particle loss.
5. Full-feedback PorePressRate excursions are not reduced enough by delay or
   ramping; scale `0.25` reduces them but still reverses.
6. DtMin adjustments vanish only for feedback off and the scaled `0.25`
   diagnostic; full feedback still causes large adjustment bursts.
7. Axial loading should not be reintroduced yet.
8. Source-level confinement magnitude normalization alone is not the first
   fix; the next blocker is the feedback acceleration/operator coupling under
   selected confinement.
9. DP and MCC remain too early.
10. Next step should be a narrow feedback-stability source study: feedback
    relaxation / acceleration limiting / operator audit under confinement-only
    equilibrium, followed by output enhancement only after the coupled
    feedback-on state is stable.
