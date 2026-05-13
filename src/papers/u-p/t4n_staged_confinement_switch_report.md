# T4n Staged Confinement Switch Report

## Summary

T4n implements and tests a CPU-only staged selector switch from Zhao all-surface
`f_i` confinement to lateral-only selected confinement. The switch runs
successfully at the execution level, but it is not mechanically neutral and it
does not unlock full-feedback or axial loading.

## Implementation

Added parameter:

```xml
<parameter key="ConfiningStressLateralSelectorStartTime" value="0.003" />
```

Default behavior is unchanged. Values `<=0` keep the old immediate/static
lateral selector behavior. When the value is positive and
`ConfiningStressUseLateralSelector=1`, the run starts all-surface and switches
to lateral-only at the requested time. GPU hard-errors for non-default
scheduling.

## CPU Runs

All cases used `SoilConstitutiveModel=0`, `InitialStressMode=1`,
`InitialEffectiveStressIso=50 Pa`, `FlexibleConfiningStress=1`,
`ConfiningStressUseFiSelector=1`, no axial loading, and CPU Release.

| Case | Code | Excluded | DtMin | Active targets | Max `PorePressRate` |
| --- | ---: | ---: | ---: | ---: | ---: |
| all-surface reference, feedback off | 0 | 0 | 0 | 208 | `3.98e7 Pa/s` |
| all-surface -> lateral, feedback off | 0 | 0 | 0 | `208 -> 112` | `5.46e7 Pa/s` |
| all-surface -> lateral, delayed feedback | 0 | 0 | 0 | `208 -> 112` | `9.15e9 Pa/s` |

`Kplastic=0` in all cases.

## Switch Result

The target switch works as intended. Diagnostics show the lateral selector is
inactive before the switch and active afterward, with targets dropping from
`208` low-`f_i` particles to `112` lateral particles.

The mechanical state is not preserved. In the feedback-off switch case:

| Metric | all-surface reference | switched feedback-off |
| --- | ---: | ---: |
| final `p'` proxy | `46.38 Pa` | `19.08 Pa` |
| final `q` proxy | `15.65 Pa` | `46.29 Pa` |
| final center pore pressure | `329 Pa` | `-9736 Pa` |
| final mean pore pressure | `-2960 Pa` | `-13381 Pa` |

The switch removes cap/edge confinement support abruptly. That reintroduces
deviatoric stress and negative pore pressure even with feedback disabled.

## Feedback Gate

Delayed feedback after the switch is improved relative to T4m delayed feedback
but still fails the physical gate.

| Metric | T4m all-surface delayed feedback | T4n switch delayed feedback |
| --- | ---: | ---: |
| excluded / DtMin | `0 / 0` | `0 / 0` |
| max velocity | `30.64 m/s` | `0.339 m/s` |
| max `DivVel` | `2442 1/s` | `13.7 1/s` |
| max `PorePressRate` | `1.63e12 Pa/s` | `9.15e9 Pa/s` |
| final `q` proxy | failed | `220 Pa` |

This is a substantial improvement in numerical severity, but still not a pass:
negative pressure remains strong and `q` grows badly after feedback activates.

## Answers

1. Pure XML could not implement the switch before T4n.
2. T4n implements selector scheduling through
   `ConfiningStressLateralSelectorStartTime`.
3. Default behavior is preserved.
4. The all-surface -> lateral switch is execution-stable (`code=0`,
   `excluded=0`, `DtMin=0`), but not hydrostatically stable.
5. `q` is not controlled after the switch; it rises from the all-surface
   reference level to about `46 Pa` without feedback and `220 Pa` with delayed
   feedback.
6. `PorePressRate`, `DivVel`, and velocity remain bounded in feedback-off mode,
   but delayed feedback still produces large excursions.
7. Delayed feedback is much improved versus T4m, but does not pass the gate.
8. No axial smoke was run.
9. T4o axial loading baseline is not recommended yet.
10. DP and MCC remain deferred.
11. GPU remains deferred.

## Next Recommendation

Do not add axial loading yet. The next step should make the switch less abrupt
or use a restart/relaxation strategy that preserves hydrostatic support while
transitioning to lateral-only confinement. A time-ramped selector weight or a
validated restart from all-surface equilibrium are better candidates than
turning on axial loading from the current switched state.

