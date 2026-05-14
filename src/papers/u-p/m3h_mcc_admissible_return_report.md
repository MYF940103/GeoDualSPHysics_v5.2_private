# M3h MCC Admissible Return Report

## Objective

M3h tests an opt-in admissible Newton / line-search refinement for the CPU MCC
return mapping.  The goal is to determine whether local platen/edge return
failures from M3f can be removed without fallback and without changing the MCC
physical model.

All M3h cases are:

- CPU-only;
- feedback-off;
- explicit-platen;
- selected lateral FlexibleConfiningStress;
- mild MCC;
- no GPU simulation;
- no Cryer;
- no PR pore-pressure update changes.

## Source Changes

M3h adds opt-in MCC-only controls:

- `MccAdmissibleLineSearch`;
- `MccLineSearchMaxBacktrack`;
- `MccLineSearchMinStep`;
- `MccLineSearchResidualReduction`;
- `MccEnforcePositivePlasticMultiplier`;
- `MccAdmissibleProjection`.

It also adds `SaveMccState` diagnostic fields:

- `MccLineSearchBacktrackCount`;
- `MccLineSearchRejectReason`;
- `MccLineSearchMinAlpha`.

Default behavior is unchanged.  With `MccAdmissibleLineSearch=0`, the old MCC
single-step/substepping behavior is retained.  Elastic, DP, DP+softening,
FlexibleConfiningStress, and PR pore-pressure update behavior are unchanged.

GPU behavior is unchanged: `SoilConstitutiveModel=3` remains a GPU hard error.

## Cases

The M3h cases are stored in:

`examples/u-pw/04_Undrained_Triaxial/experiments/M3h_MCCAdmissibleReturn/`

| key | description |
| --- | --- |
| `baseline` | original-rate mild MCC baseline, no admissible line search |
| `admissible_line` | original-rate admissible line search, no substepping |
| `adaptive_line` | original-rate adaptive substepping plus admissible line search |
| `half_speed_adaptive_line` | half-speed adaptive substepping plus admissible line search |
| `quarter_speed_line` | quarter-speed adaptive substepping plus admissible line search |

All cases finish:

```text
code=0
excluded=0
DtMin=0
```

## Return Status Results

| case | final `-3` | final `-5` | final `-1` | max `-3` | max `-5` | max `-1` | bad frames | clean |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 8 | 0 | 0 | 9 | 0 | 157 | 22 | 0 |
| admissible_line | 8 | 0 | 0 | 9 | 0 | 157 | 22 | 0 |
| adaptive_line | 10 | 0 | 8 | 16 | 0 | 92 | 35 | 0 |
| half_speed_adaptive_line | 0 | 0 | 0 | 8 | 0 | 100 | 23 | 0 |
| quarter_speed_line | 0 | 0 | 0 | 16 | 0 | 33 | 7 | 0 |

No M3h case is a clean candidate, because every case has at least one saved
frame with a negative return status.

## Original-Rate Result

Original-rate admissible line search does not improve the baseline:

```text
baseline final:        -3:8
admissible_line final: -3:8
```

The failure locations and final counts are essentially unchanged.  Increasing
the maximum line-search backtracking from 12 to 32 does not solve the local
return problem.

## Adaptive Substepping Plus Line Search

Adaptive substepping combined with admissible line search is not better at the
original rate:

```text
adaptive_line final: -3:10 | -1:8
```

It adds more transient bad frames than the baseline.  The maximum accumulated
backtrack count increases because multiple substeps can each invoke line
search.  This confirms that substepping plus admissible rejection still does
not clean the platen/edge local path.

## Slower Loading

Half-speed and quarter-speed cases both clear the final frame:

```text
half_speed_adaptive_line final: 0:407 split across elastic/plastic statuses
quarter_speed_line final:      0:407 split across elastic/plastic statuses
```

However, both still have transient saved-frame `-3` and `-1` episodes:

- half-speed: max `-3=8`, max `-1=100`, 23 bad frames;
- quarter-speed: max `-3=16`, max `-1=33`, 7 bad frames.

Quarter-speed is the best diagnostic route in this set because it has the
fewest bad frames, but it still fails the clean gate.

## Failed Return Cause

The M3h audit confirms the M3f diagnosis:

- failures are local, strongest near edge and platen-adjacent regions;
- early `-1` statuses correspond to inadmissible or near-tension saved `p'`;
- persistent `-3` statuses occur with positive `p'`, valid `pc`, and bounded
  state variables, so they are local Newton/line-search failures rather than a
  sign convention or global hardening failure;
- line-search reject reason `6` shows residual-reduction failure in the
  difficult local paths;
- reject reason `4` appears in `-3` records where plastic-multiplier
  admissibility is violated.

Trial p/q/f values were not persisted by M3f/M3h outputs.  The generated
`m3h_trial_state_diagnostics.csv` marks these columns as unavailable and
contains the available line-search aggregate diagnostics instead.

## State, Reaction, and Pore Pressure

State variables remain bounded and readable:

| case | pc mean (Pa) | e mean | plastic vol strain mean | reaction avg (N) | p' (Pa) | q (Pa) | mean pore pressure (Pa) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 119.63 | 0.80049 | -2.75e-4 | 0.286 | 47.26 | 64.95 | -2.25e5 |
| admissible_line | 119.63 | 0.80049 | -2.75e-4 | 0.286 | 47.26 | 64.95 | -2.25e5 |
| adaptive_line | 119.63 | 0.80049 | -2.72e-4 | 0.285 | 47.09 | 64.47 | -2.39e5 |
| half_speed_adaptive_line | 119.53 | 0.80063 | -3.48e-4 | 0.255 | 46.25 | 62.16 | -2.82e5 |
| quarter_speed_line | 119.48 | 0.80070 | -3.85e-4 | 0.233 | 45.03 | 59.35 | -3.09e5 |

Converged-particle yield residuals remain controlled:

```text
max converged residual ~= 1.19e-4 to 1.32e-4
```

Raw residual maxima remain high because they include failed particles.  Pairwise
reaction, p'-q paths, velocity, and pore pressure stay bounded, but the pore
pressure remains a feedback-off diagnostic and not strict undrained validation.

## Build and Run Status

M3h CPU Release cases complete successfully.  CPU Release build was run after
the source changes.  CPU Debug and GPU Release builds are required before final
commit because parser/shared source files changed.  No GPU simulation is run.

## Conclusion

M3h implements admissible line search and diagnostics, but it does not produce
a clean reduced MCC validation candidate.

The main findings are:

- default behavior is preserved;
- original-rate admissible line search does not improve the baseline;
- adaptive substepping plus admissible line search worsens the original-rate
  final status;
- half-speed and quarter-speed routes clear final `-3/-5`, but still contain
  transient saved-frame failures;
- no route uses fallback as validation;
- pc, void ratio, plastic strains, reaction, p'-q, and pore pressure remain
  bounded but caveated.

## Recommendation

Do not enter M3g as a clean MCC validation package.  If M3g is used, it should
be a caveated reporting package only.

For strict clean validation, the next step should either:

1. pause the platen MCC strict-validation route and design a smaller
   single-element/SPH local path with smoother strain localization; or
2. add deeper per-failure trial-state tracing and revisit the local return
   equations with a more robust closest-point/implicit scheme.

Full pore-pressure feedback and GPU MCC remain deferred.
