# T4n2 Restart Equilibrium Audit Report

## Summary

T4n2 confirms that the existing restart machinery can preserve the current
u-pw state needed for staged triaxial confinement, but the restart-based
all-surface-to-lateral transition does not solve the hydrostatic-balance or
full-feedback instability.

No source was modified. No GPU simulation was run.

## Cases

| Case | Route | Result |
| --- | --- | --- |
| Stage A | all-surface `f_i`, feedback off | `code=0`, `excluded=0`, `DtMin=0` |
| Stage B | restart from Stage A, lateral-only, feedback off | `code=0`, `excluded=0`, `DtMin=0` |
| Fresh lateral | fresh lateral-only, feedback off | `code=0`, `excluded=0`, `DtMin=0` |
| Stage C | restart from Stage A, lateral-only, delayed interior feedback | `code=0`, `excluded=0`, `DtMin=0` |

`Kplastic=0` in all cases.

## Restart Fidelity

Stage B and Stage C restored:

- `Sigma_kk`, `Sigma_ij`, and `Kplastic` for `407/407` particles;
- `PorePress` for `407/407` particles;
- density and velocity through the core Part restart data.

The field-by-field comparison of Stage A final `PartCsv_0023` and Stage B
initial `PartCsv_0023` gives zero max difference in saved CSV precision for
position, velocity, density, stress, `Kplastic`, and `PorePress`.

`ExcessPorePress`, `PorePressRate`, `DivVel`, `LapPorePress`, and feedback
acceleration diagnostics are not separately restored. For the current
`HydraulicElevationSource=0` cases, `ExcessPorePress` equals `PorePress`; the
rate and diagnostic fields are recomputed.

## Stage A Equilibrium

Stage A reproduces the T4m all-surface feedback-off behavior:

| Metric | Final value |
| --- | ---: |
| `p'` proxy | `46.38 Pa` |
| `q` proxy | `15.65 Pa` |
| mean pore pressure | `-2960 Pa` |
| min pore pressure | `-9329 Pa` |
| max `PorePressRate` | `3.98e7 Pa/s` |
| max velocity | `1.10e-3 m/s` |

This is stable at the execution level and remains the best hydrostatic
pre-equilibrium route found so far, but it is not a perfectly quiet or
pore-pressure-neutral equilibrium.

## Stage B Restart Lateral-Only Result

The restart itself is exact, but the immediate lateral-only continuation still
changes the mechanical state:

| Metric | Stage A final | Stage B final |
| --- | ---: | ---: |
| `p'` proxy | `46.38 Pa` | `13.50 Pa` |
| `q` proxy | `15.65 Pa` | `37.89 Pa` |
| mean pore pressure | `-2960 Pa` | `-15465 Pa` |
| negative-pressure particles | `354` | `407` |
| max `PorePressRate` | `3.98e7 Pa/s` | `4.02e7 Pa/s` |
| max velocity | `1.10e-3 m/s` | `1.26e-3 m/s` |

The `q` increase from the restart state is about `22.24 Pa`. This is smaller
than the T4n single-run instant-switch final `q` of about `46.29 Pa`, but it is
still not a pass. The lateral-only support removes cap/edge confinement and
reintroduces strong negative pore pressure.

Against the fresh lateral-only case, restart is better in stress balance:

| Route | Final `p'` | Final `q` | Final mean pore pressure |
| --- | ---: | ---: | ---: |
| Stage B restart lateral | `13.50 Pa` | `37.89 Pa` | `-15465 Pa` |
| Fresh lateral-only | `17.11 Pa` | `51.47 Pa` | `-14223 Pa` |

The restart improves `q` relative to fresh lateral-only, but not enough to
restore a usable hydrostatic state.

## Delayed Feedback After Restart

Stage C does not pass. It stays executable (`code=0`, `excluded=0`,
`DtMin=0`) but delayed interior feedback produces a new runaway:

| Metric | Stage C final / max |
| --- | ---: |
| max `PorePressRate` | `1.84e12 Pa/s` |
| max velocity | `28.23 m/s` |
| max `DivVel` | `2767 1/s` |
| final `p'` proxy | `-3250 Pa` |
| final `q` proxy | `4049 Pa` |
| final mean pore pressure | `-1.35e6 Pa` |
| min pore pressure | `-2.42e7 Pa` |

This is worse than the T4n delayed single-run switch in `PorePressRate` and
stress response. Restart fidelity is not the blocker; the blocker is the
unbalanced lateral-only state plus full feedback.

## Answers

1. Current restart supports the required u-pw fields for this elastic stage:
   position, velocity, density, `Sigma_kk`, `Sigma_ij`, `Kplastic`, and
   `PorePress`.
2. Stage A all-surface equilibrium is execution-stable and relatively close to
   hydrostatic (`p'~46.38 Pa`, `q~15.65 Pa`), but pore pressure remains
   negative in much of the specimen.
3. Stage B restart lateral-only is technically feasible and restart continuity
   is exact, but the lateral-only continuation is not mechanically stable
   enough.
4. Stress, pore pressure, velocity, density, and `Kplastic` are continuous
   across restart in saved precision.
5. The Stage B `q` increase is lower than the T4n instant-switch final `q`, but
   it is still substantial and not acceptable as a gate pass.
6. Feedback after restart does not improve. It produces order `1e12 Pa/s`
   `PorePressRate`, large velocity, large negative pressure, and huge `q`.
7. Axial loading should not be reintroduced.
8. No restart source enhancement is needed for the currently saved u-pw fields;
   future diagnostics could benefit from restoring `DivVel`/`PorePressRate`,
   but those are not the current blocker.
9. DP and MCC remain deferred.

## Next Recommendation

Do not proceed to axial loading or DP/MCC. The next useful CPU task should
address the mechanical state change when moving from all-surface confinement
to lateral-only confinement. The two defensible routes are:

- add a reference-supported hold/equilibration strategy after restart while
  keeping feedback off; or
- revisit specimen geometry / cap and edge support so lateral-only triaxial
  confinement does not discard too much of the hydrostatic support.

Selector smoothing remains an engineering fallback, not a paper-faithful
validation route.
