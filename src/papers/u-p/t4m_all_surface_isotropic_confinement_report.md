# T4m All-Surface Isotropic Confinement Report

## Summary

T4m tests Zhao-style all-surface `f_i` confinement as an isotropic confinement
stage. It runs successfully and is clearly more hydrostatic than the T4l
lateral-plus-cap route with feedback off. However, delayed full feedback still
fails, so axial loading, DP, MCC, and GPU remain deferred.

## Cases

All cases used `SoilConstitutiveModel=0`, `InitialStressMode=1`,
`InitialEffectiveStressIso=50 Pa`, no axial loading, CPU Release, and
`Kplastic=0`.

| Case | Route | Feedback | Code | Excluded | DtMin |
| --- | --- | --- | ---: | ---: | ---: |
| T4l reference | lateral + cap support | off | 0 | 0 | 0 |
| All-surface | `f_i` all-surface confinement | off | 0 | 0 | 0 |
| All-surface | `f_i` all-surface confinement | delayed | 0 | 0 | 0 |

## Hydrostatic Equilibrium Result

| Metric | T4l lateral+cap, feedback off | all-surface, feedback off |
| --- | ---: | ---: |
| active confinement targets | `112` | `208` |
| final `p'` proxy | `38.90 Pa` | `46.38 Pa` |
| final `q` proxy | `53.50 Pa` | `15.65 Pa` |
| max velocity | `2.34e-3 m/s` | `1.10e-3 m/s` |
| max `DivVel` | `6.64e-2 1/s` | `5.98e-2 1/s` |
| max `PorePressRate` | `4.42e7 Pa/s` | `3.98e7 Pa/s` |
| final center pore pressure | `-62.9 Pa` | `329.0 Pa` |
| final mean pore pressure | `-4494 Pa` | `-2960 Pa` |

The all-surface route is much closer to a hydrostatic effective stress state.
It reduces final `q` by about 70 percent and moves `p'` closer to the `50 Pa`
target. It also removes the obvious T4l cap/edge over-compression pattern.

## Region-Wise Stress

Final feedback-off region metrics:

| Region | T4l `q` | all-surface `q` | T4l `p'` | all-surface `p'` |
| --- | ---: | ---: | ---: | ---: |
| interior | `77.9 Pa` | `8.03 Pa` | `51.9 Pa` | `45.0 Pa` |
| lateral | `36.1 Pa` | `18.1 Pa` | `45.1 Pa` | `47.4 Pa` |
| top cap | `99.6 Pa` | `16.2 Pa` | `106.7 Pa` | `41.9 Pa` |
| bottom cap | `99.6 Pa` | `16.2 Pa` | `106.7 Pa` | `41.9 Pa` |
| edge | `55.5 Pa` | `15.5 Pa` | `-1.15 Pa` | `46.7 Pa` |

This is the strongest positive result in T4m: using one Zhao-style pairwise
surface mechanism across lateral/cap/edge regions avoids the cap-force
discontinuity introduced in T4l.

## Pore Pressure

Negative pressure is improved but not eliminated. All particles still become
negative at some point, and the final specimen mean pore pressure remains
negative. The center core is much cleaner than T4l, but the pressure field is
not validation-ready.

## Feedback-On Gate

Delayed feedback remains unstable:

| Metric | all-surface delayed feedback |
| --- | ---: |
| code / excluded / DtMin | `0 / 0 / 0` |
| max velocity | `30.64 m/s` |
| max `DivVel` | `2442.42 1/s` |
| max `PorePressRate` | `1.63e12 Pa/s` |
| min pore pressure | `-6.33e7 Pa` |
| max feedback acceleration | `1.02e6 m/s2` |

This is not a pass. Although the run avoids exclusions and DtMin bursts, the
feedback-on physical stability gate fails.

## Answers

1. T4l's main imbalance came from mixing lateral pairwise confinement with an
   explicit cap force and skipping edge-ring support.
2. Zhao all-surface confinement is more hydrostatic than T4l in the
   feedback-off stage.
3. `q` is strongly reduced.
4. `p'` moves closer to the `50 Pa` target.
5. Feedback-off all-surface confinement is numerically stable.
6. Delayed feedback is still unstable and does not pass the gate.
7. Negative pressure and `PorePressRate` improve in feedback-off mode but not
   when full feedback is restored.
8. `CapConfiningStress` remains useful as a diagnostic, but it should not be
   the first isotropic equilibrium route.
9. A staged selector switch or restart is likely needed: all-surface isotropic
   equilibrium first, then lateral-only confinement plus axial loading.
10. T4n should investigate staged switch/restart equilibrium only after deciding
    how to handle the feedback-on instability.
11. DP and MCC remain deferred.
12. GPU remains deferred.

## Next Recommendation

Do not reintroduce axial loading yet. T4m establishes that all-surface
confinement is the better isotropic pre-equilibrium route, but the u-pw feedback
loop still destabilizes the sample. The next narrow step should either add a
restart/selector-switch workflow for all-surface to lateral confinement, or
revisit feedback activation after a cleaner all-surface equilibrium state.
