# M3f MCC Return/Staging Refinement Report

## Objective

M3f attempts to clean the mild MCC feedback-off explicit-platen triaxial route
after M3e. The target is a reduced validation candidate with no `-3`, no `-5`,
and no transient negative return-status episodes in any saved frame.

No full pore-pressure feedback was enabled. No GPU simulation was run.

## Source Changes

M3f adds opt-in MCC substepping diagnostics and an improved adaptive substep
trigger for `SoilConstitutiveModel=3` only:

- `MccMinSubsteps`;
- `MccSubstepYieldDistanceThreshold`;
- `MccSubstepTriggerReason` output;
- `MccSubstepMode=2` now can choose substeps from minimum substeps, approximate
  strain-increment threshold, and normalized trial yield-distance threshold.

Default behavior is unchanged:

```text
MccSubstepping=0
MccMinSubsteps=1
MccSubstepYieldDistanceThreshold=0
MccFailureFallback=0
```

GPU behavior is unchanged: `SoilConstitutiveModel=3` remains GPU-hard-error.

## Cases

The M3f cases are stored in:

`examples/u-pw/04_Undrained_Triaxial/experiments/M3f_MCCReturnStagingRefinement/`

| key | description |
| --- | --- |
| `baseline` | original-rate mild MCC, no substepping |
| `ramp_current_adaptive` | smoother platen ramp plus existing adaptive retry |
| `improved_adaptive` | original-rate improved adaptive mode 2 |
| `ramp_improved_adaptive` | smoother ramp plus improved adaptive mode 2 |
| `half_speed_adaptive` | half-speed adaptive reference |
| `half_speed_ramp_adaptive` | half-speed smoother ramp adaptive |
| `quarter_speed_adaptive` | quarter-speed adaptive diagnostic |

All cases finish:

```text
code=0
excluded=0
DtMin=0
```

## Return Robustness Results

| case | final `-3` | final `-1` | final `-5` | max `-3` | max `-1` | bad frames | clean |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 8 | 0 | 0 | 9 | 157 | 22 | 0 |
| ramp current adaptive | 5 | 4 | 0 | 16 | 128 | 34 | 0 |
| improved adaptive | 28 | 19 | 0 | 74 | 92 | 35 | 0 |
| ramp improved adaptive | 21 | 20 | 0 | 58 | 128 | 39 | 0 |
| half-speed adaptive | 0 | 0 | 0 | 8 | 100 | 23 | 0 |
| half-speed ramp adaptive | 0 | 0 | 0 | 20 | 160 | 28 | 0 |
| quarter-speed adaptive | 0 | 0 | 0 | 16 | 33 | 7 | 0 |

No case satisfies the strict clean gate because every case has at least one
saved frame with a negative return status. The quarter-speed diagnostic is the
best of the set, but it still has transient `-3` episodes.

## Where Transient Failures Occur

Transient failures are concentrated around edge and platen-adjacent regions.
The baseline has failed-status records in edge, lateral-boundary, bottom
cap-zone, and nearby interior particles. Quarter-speed loading reduces the
failed set to edge and bottom-cap-zone particles only.

The failure location is local rather than global:

- most particles converge in the same frames;
- solver-level stability remains clean;
- pairwise reaction remains bounded;
- p'-q and pore-pressure curves remain readable.

## Failure Cause

The dominant cause is local trial-stress/admissibility difficulty caused by
platen/edge strain concentration. There are two observed status families:

- early `-1` admissibility/tension-cutoff states;
- later local `-3` line-search failures.

Higher iteration limits and tighter tolerances had already failed to clean the
case in M3d2. M3f confirms that the issue is not simply insufficient Newton
iterations.

## Smoother Loading

Smoother platen ramping does not solve the problem. It slightly reduces final
`-3` in the original-rate current-adaptive case, but introduces final `-1`
particles and more bad frames. At half speed, ramping increases transient
failures relative to half speed without ramping.

## Improved Adaptive Substepping

Improved adaptive substepping was implemented, including a trial yield-distance
trigger and trigger-reason output. It does not improve the tested mild MCC
case. With the M3f thresholds, original-rate mode 2 cases have more final
negative statuses and more transient failures than the baseline.

This suggests the next clean-validation work should improve the local return
mapping/admissibility projection itself rather than only splitting increments.

## State, Reaction, and Pore Pressure

Even the non-clean cases remain bounded:

- `pc`, void ratio, plastic volumetric strain, and equivalent plastic strain
  evolve continuously at the specimen scale;
- pairwise reaction is bounded;
- p'-q paths remain readable;
- pore pressure does not run away.

Representative final values:

| case | pc mean (Pa) | e mean | plastic vol strain mean | reaction avg (N) | p' (Pa) | q (Pa) | mean pore pressure (Pa) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 119.63 | 0.80049 | -2.75e-4 | 0.286 | 47.26 | 64.95 | -2.25e5 |
| half-speed adaptive | 119.53 | 0.80063 | -3.48e-4 | 0.255 | 46.25 | 62.16 | -2.82e5 |
| quarter-speed adaptive | 119.48 | 0.80070 | -3.85e-4 | 0.233 | 45.03 | 59.35 | -3.09e5 |

The negative pore pressure remains a feedback-off reduced-route limitation and
must not be read as strict undrained MCC validation.

## Build and Run Status

CPU Release build passed after the source changes. CPU Release M3f cases all
finish `code=0`, `excluded=0`, `DtMin=0`.

GPU Release build is required because shared parser/source files changed. GPU
simulation remains deferred and `SoilConstitutiveModel=3` remains unsupported
on GPU.

## Conclusion

M3f does not produce a clean reduced MCC validation candidate.

The main conclusions are:

- transient failures remain local to edge/platen-adjacent regions;
- smoother loading does not clean them;
- improved adaptive substepping is implemented but does not clean them with the
  tested thresholds;
- quarter-speed adaptive is the best diagnostic route but still has transient
  `-3`;
- no route uses hidden fallback as validation;
- state, reaction, p'-q, and pore pressure remain bounded but diagnostic only.

## Recommendation

Do not enter M3g as a clean MCC validation package. If a caveated reporting
package is acceptable, M3g can summarize M3f, but it should not claim clean
validation.

For clean validation, the next step should be a focused local-return stage:

1. improve admissible Newton projection / line-search;
2. preserve the no-fallback validation rule;
3. retest the same mild MCC platen route;
4. keep full feedback and GPU deferred.

