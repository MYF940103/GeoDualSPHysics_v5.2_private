# T4o Cap-Support-Preserving Staged Loading Report

## Summary

T4o tested whether restarting from all-surface isotropic confinement and
retaining cap support during the lateral-confinement stage would preserve the
hydrostatic state better than the T4n2 lateral-only restart.

The result is a no-go for axial loading. The runs completed numerically, but
Stage B with lateral confinement plus explicit cap support did not preserve
hydrostatic equilibrium. It increased `q` beyond the T4n2 lateral-only restart
and moved `p'` farther from the target. Delayed feedback was less violent than
T4n2 in peak `PorePressRate`, but it still failed the physical stability gate.

## Cases

| Case | Result | Final `p'` | Final `q` | Max `PorePressRate` | Max velocity |
| --- | --- | ---: | ---: | ---: | ---: |
| Stage A all-surface, feedback off | `code=0`, `excluded=0`, `DtMin=0` | `46.38 Pa` | `15.65 Pa` | `3.98e7 Pa/s` | `1.10e-3 m/s` |
| Stage B restart lateral+cap, feedback off | `code=0`, `excluded=0`, `DtMin=0` | `23.87 Pa` | `61.92 Pa` | `5.06e7 Pa/s` | `2.09e-3 m/s` |
| Stage C restart lateral+cap, delayed feedback | `code=0`, `excluded=0`, `DtMin=0` | `-1761.08 Pa` | `4866.39 Pa` | `9.32e11 Pa/s` | `23.37 m/s` |

`Kplastic` remained `0` in all cases.

## Restart Continuity

Restart continuity remained exact in saved CSV precision. Stage B restored the
Stage A `Part_0023` state with zero maximum absolute difference for:

- position;
- velocity;
- density;
- `Sigma_kk`;
- `Sigma_ij`;
- `Kplastic`;
- `PorePress`.

This confirms again that restart fidelity is not the current blocker.

## Stage B Equilibrium

Stage B was numerically stable in the narrow code-health sense:

- `code=0`;
- `excluded=0`;
- `DtMin=0`;
- `Kplastic=0`;
- cap support targets: `18` top and `18` bottom particles;
- edge particles skipped by cap support: `112`;
- cap support net force remained zero by symmetry;
- lateral selected confinement stayed coherent with `112` active targets.

However, it failed the hydrostatic-equilibrium gate:

- `q` rose from `15.65 Pa` in Stage A to `61.92 Pa`;
- this is worse than the T4n2 lateral-only restart (`q approx 37.89 Pa`);
- `p'` dropped from `46.38 Pa` to `23.87 Pa`;
- all `407` particles were negative in pore pressure at the final frame;
- center-core pore pressure changed from positive in Stage A to about
  `-7804 Pa` at final Stage B.

Region-wise final `q` shows the mismatch clearly:

| Region | Stage A `q` | Stage B `q` |
| --- | ---: | ---: |
| interior | `8.03 Pa` | `99.24 Pa` |
| lateral | `18.08 Pa` | `42.35 Pa` |
| top cap | `16.20 Pa` | `121.34 Pa` |
| bottom cap | `16.20 Pa` | `121.34 Pa` |
| edge | `15.51 Pa` | `56.06 Pa` |

The explicit cap support preserves a symmetric cap force, but it does not
match the all-surface Zhao confinement state. The cap/interior stress mismatch
becomes stronger than the T4n2 lateral-only restart.

## Stage C Feedback Gate

Delayed feedback after the lateral+cap restart still failed:

- max `PorePressRate = 9.32e11 Pa/s`;
- max velocity `= 23.37 m/s`;
- final `q = 4866.39 Pa`;
- final mean pore pressure `= -7.25e5 Pa`;
- final minimum pore pressure `= -4.56e6 Pa`;
- feedback acceleration reached `4.46e5 m/s2` while confinement acceleration
  was only about `1.92 m/s2`.

Compared with T4n2 Stage C (`~1.84e12 Pa/s` and `~28.23 m/s`), cap support
reduced the peak `PorePressRate` and velocity somewhat, but not enough to pass
the gate. The instability remains feedback-dominated once full feedback is
restored.

## Axial Loading

No axial smoke was run. Stage C did not produce a stable feedback-on
confinement-only state, so adding axial loading would not test a meaningful
triaxial baseline.

## Conclusions

1. T4n2 lateral-only switch failed because removing cap/free-surface support
   after all-surface equilibrium destroyed hydrostatic balance.
2. T4o showed that simply adding the current explicit `CapConfiningStress`
   after restart does not solve the transition; it worsens the `q` imbalance.
3. The all-surface Zhao confinement stage remains the best feedback-off
   hydrostatic pre-equilibrium route.
4. The current explicit cap support is useful diagnostically but is not
   mechanically compatible enough with the all-surface equilibrium state for a
   strict staged triaxial workflow.
5. Delayed full feedback remains unstable, even though peak `PorePressRate` is
   lower than in T4n2.

## Next Step

Do not proceed to T4p axial loading, DP, or MCC. The next work should return to
the confinement support formulation:

- either keep all-surface Zhao confinement through a longer equilibrium and
  design a paper-supported cap/loading transition;
- or audit a restart/staged workflow that preserves all-surface confinement
  until an actual cap displacement/loading stage is introduced;
- or revisit cap support as a stress-compatible boundary mechanism rather than
  a separate acceleration patch.

GPU remains deferred.
