# M3l Platen / Specimen Smoothing Report

## Objective

M3l tests whether small platen/specimen interface or edge/corner changes reduce
the MCC return failures captured in M3k.  No source was modified, no MCC return
mapping was changed, full pore-pressure feedback stayed off, and no GPU
simulation was run.

All cases are very-short dense-output CPU Release diagnostics with the same
mild MCC parameters used in M3k.

## Tested Variants

Experiment directory:

`examples/u-pw/04_Undrained_Triaxial/experiments/M3l_PlatenSpecimenSmoothing/`

| variant | purpose | change |
| --- | --- | --- |
| `baseline` | M3k-equivalent dense reference | none |
| `gap_2dp` | platen/specimen spacing diagnostic | generated platen center gap increased from 1dp to 2dp |
| `platen_overhang` | interface support diagnostic | platen radius increased from 0.03 m to 0.04 m |
| `edge_selector_buffer` | edge/cap lateral-selector diagnostic | cap/edge exclusion increased from 0.015 m to 0.025 m |

All cases completed:

```text
code=0
excluded=0
DtMin adjustments=0
```

The raw solver outputs were postprocessed into extracted CSV and figures, then
removed from the committed package.

## Return Status Comparison

| variant | first failure time [s] | first neg. count | first `-3` | first `-1` | max `-3` | max `-1` | final neg. |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 0.001005 | 96 | 4 | 92 | 16 | 157 | 40 |
| gap_2dp | 0.000804 | 4 | 0 | 4 | 0 | 258 | 89 |
| platen_overhang | 0.001005 | 12 | 8 | 4 | 8 | 20 | 8 |
| edge_selector_buffer | 0.000905 | 8 | 0 | 8 | 13 | 174 | 69 |

Interpretation:

- `gap_2dp` eliminates `ReturnStatus=-3`, but it weakens top-platen support and
  substantially worsens `ReturnStatus=-1` near-tension behavior.
- `platen_overhang` is the best overall diagnostic: first negative count drops
  from 96 to 12, max `-1` drops from 157 to 20, and final negative count drops
  from 40 to 8.  However, `-3` is not eliminated.
- `edge_selector_buffer` is not useful in this form: failure starts earlier,
  final negative count increases, and final `-3` appears.

No variant passes a clean validation gate because every variant still has saved
frames with negative MCC return status.

## Support / Neighbor Proxy

Aggregate failed-particle support metrics:

| variant | failed records | failed `-3` | failed `-1` | specimen-neighbor mean | support/core mean |
| --- | ---: | ---: | ---: | ---: | ---: |
| baseline | 1784 | 46 | 1738 | 96.25 | 0.828 |
| gap_2dp | 3037 | 0 | 3037 | 102.22 | 0.834 |
| platen_overhang | 229 | 37 | 192 | 111.38 | 0.966 |
| edge_selector_buffer | 2208 | 58 | 2150 | 96.35 | 0.809 |

`platen_overhang` clearly improves the aggregate support environment of failed
particles and dramatically reduces the number of failed records.  This is the
strongest support for the boundary/interface hypothesis.

At first onset, `platen_overhang` still has edge `-3` failures, but their local
return burden is lower than baseline:

| first `-3` metric | baseline | platen_overhang |
| --- | ---: | ---: |
| `-3` count | 4 | 8 |
| specimen-neighbor proxy | 56 | 64 |
| velocity-gradient proxy | 0.112 | 0.093 |
| `p'` [Pa] | 73.97 | 62.65 |
| `q` [Pa] | 93.76 | 79.81 |
| yield residual | 3888 | 1196 |

The overhang variant does not remove the edge failure mode, but it weakens the
local kinematic and return-mapping severity.

## Local Strain / Velocity-Gradient Behavior

The first-onset hard `-3` failures remain edge-localized.  Relative to baseline,
the overhang variant reduces:

- local velocity-gradient proxy: `0.112 -> 0.093`;
- local shear-rate proxy: `0.156 -> 0.131`;
- local `q`: `93.76 Pa -> 79.81 Pa`;
- local yield residual: `3888 -> 1196`.

The gap variant removes `-3` but does so by under-supporting the platen/specimen
interaction.  It produces earlier and more persistent near-tension `-1`
failures.

The edge-selector-buffer variant reduces first-frame `-3`, but it worsens the
overall failure history and is therefore not a good production direction.

## Global Reaction / p'-q / Pore Pressure

Global response remains bounded in all cases:

| variant | final p' [Pa] | final q [Pa] | pairwise reaction [N] | `Fz_proxy` [N] | final mean PorePress [Pa] |
| --- | ---: | ---: | ---: | ---: | ---: |
| baseline | 48.34 | 49.27 | 0.249 | 0.213 | -13006 |
| gap_2dp | 35.16 | 33.75 | 0.116 | 0.133 | -12485 |
| platen_overhang | 55.88 | 52.42 | 0.283 | 0.243 | -4612 |
| edge_selector_buffer | 39.96 | 50.73 | 0.231 | 0.194 | -19077 |

The overhang variant preserves a reasonable global p'-q path and pairwise
reaction while making pore pressure less negative.  The gap variant weakens the
pairwise reaction substantially, which is consistent with reduced platen
coupling rather than a robust boundary fix.

## Which Variant Is Most Effective?

Best overall: `platen_overhang`.

Reason:

- it strongly reduces total failed records;
- it dramatically reduces `ReturnStatus=-1`;
- it halves max `ReturnStatus=-3`;
- it improves aggregate failed-particle support;
- it reduces first-onset `-3` velocity-gradient and yield-residual severity;
- it keeps reaction, p'-q, and pore pressure bounded.

But it is not clean:

```text
first `-3`: 8
max `-3`: 8
final negative count: 8
```

`gap_2dp` is not recommended despite eliminating `-3`, because it shifts the
problem into broad near-tension `-1` behavior and weakens platen reaction.

`edge_selector_buffer` is also not recommended in this form.

## Boundary-Induced Failure Interpretation

M3l supports the M3k boundary-induced failure interpretation.

The strongest evidence is that a purely geometric/interface change
(`platen_overhang`) changes the return-failure population by almost an order of
magnitude without changing MCC parameters, return mapping, PR pressure update,
or FlexibleConfiningStress physics.

The remaining hard failures are still edge-localized, so the next improvement
should target the actual edge/platen/specimen geometry, not another MCC return
mapping patch.

## Next Step

Recommended next step: M3m refined boundary geometry route.

Priority:

1. refine platen/specimen interface using overhang or a smoother contact buffer;
2. combine with real edge/corner smoothing, not merely lateral selector
   exclusion;
3. if still not clean, move to a smooth/fan-like cylinder layout;
4. do not call the current route clean MCC validation.

Full pore-pressure feedback and GPU remain deferred.
