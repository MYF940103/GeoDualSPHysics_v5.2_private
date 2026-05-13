# M3f Transient MCC Return Failure Audit

## Objective

M3f audits the transient `MccReturnStatus` failures that remain after M3d3.
The target is a clean reduced MCC feedback-off platen triaxial candidate with
no `-3` line-search failures, no `-5` partial fallback, and no transient
negative return-status episodes.

The audit uses the M3f experiment directory:

`examples/u-pw/04_Undrained_Triaxial/experiments/M3f_MCCReturnStagingRefinement/`

No full pore-pressure feedback is enabled in these cases.

## Cases Audited

The M3f set contains seven CPU Release diagnostic cases:

| key | case | purpose |
| --- | --- | --- |
| `baseline` | `CaseM3f_MCCMildBaseline` | original-rate mild MCC, no substepping |
| `ramp_current_adaptive` | `CaseM3f_MCCMildRampCurrentAdaptive` | smoother platen ramp with existing adaptive retry |
| `improved_adaptive` | `CaseM3f_MCCMildImprovedAdaptive` | original-rate improved adaptive mode 2 |
| `ramp_improved_adaptive` | `CaseM3f_MCCMildRampImprovedAdaptive` | smoother ramp plus improved mode 2 |
| `half_speed_adaptive` | `CaseM3f_MCCMildHalfSpeedAdaptiveRef` | half-speed adaptive reference |
| `half_speed_ramp_adaptive` | `CaseM3f_MCCMildHalfSpeedRampAdaptive` | half-speed smoother ramp reference |
| `quarter_speed_adaptive` | `CaseM3f_MCCMildQuarterSpeedAdaptiveRef` | lower-speed diagnostic reference |

All cases finish `code=0`, `excluded=0`, and `DtMin=0`.

## Failure Timeline

The detailed particle-level table is:

`m3f_transient_failed_particles.csv`

The frame-level table is:

`m3f_return_failure_timeline.csv`

The earliest negative status appears at approximately `t=0.001005 s` in most
cases. Quarter-speed loading delays the first recorded failure to about
`t=0.002011 s`.

| case | failure time range (s) | failed-status records |
| --- | ---: | ---: |
| baseline | 0.001005 to 0.018096 | 465 |
| ramp current adaptive | 0.001005 to 0.020006 | 553 |
| improved adaptive | 0.001005 to 0.018095 | 1546 |
| ramp improved adaptive | 0.001005 to 0.020006 | 1706 |
| half-speed adaptive | 0.001005 to 0.032071 | 296 |
| half-speed ramp adaptive | 0.001005 to 0.033077 | 406 |
| quarter-speed adaptive | 0.002011 to 0.022018 | 70 |

The quarter-speed case reduces the number of failed-status particle records
most strongly, but it still has transient failures and therefore does not pass
the strict clean-candidate gate.

## Failure Regions

The failed particles are not distributed uniformly through the specimen. They
are concentrated near edge and bottom/platen-adjacent regions.

| case | edge | lateral boundary | bottom cap zone | interior | top cap zone |
| --- | ---: | ---: | ---: | ---: | ---: |
| baseline | 212 | 84 | 64 | 99 | 6 |
| ramp current adaptive | 228 | 44 | 113 | 160 | 8 |
| improved adaptive | 650 | 140 | 180 | 308 | 268 |
| ramp improved adaptive | 616 | 155 | 228 | 349 | 358 |
| half-speed adaptive | 204 | 28 | 25 | 36 | 3 |
| half-speed ramp adaptive | 268 | 44 | 25 | 56 | 13 |
| quarter-speed adaptive | 58 | 0 | 12 | 0 | 0 |

The original-rate baseline has the same character seen in M3d2: local return
failures around the bottom cap/interior transition and nearby edge rings.
Quarter-speed loading leaves only edge and bottom-cap-zone transient failures.

## Return-Status Summary

The final and maximum negative-status counts are summarized in
`m3f_case_summary.csv`.

| case | final `-3` | final `-5` | final `-1` | max `-3` | max `-1` | bad frames |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 8 | 0 | 0 | 9 | 157 | 22 |
| ramp current adaptive | 5 | 0 | 4 | 16 | 128 | 34 |
| improved adaptive | 28 | 0 | 19 | 74 | 92 | 35 |
| ramp improved adaptive | 21 | 0 | 20 | 58 | 128 | 39 |
| half-speed adaptive | 0 | 0 | 0 | 8 | 100 | 23 |
| half-speed ramp adaptive | 0 | 0 | 0 | 20 | 160 | 28 |
| quarter-speed adaptive | 0 | 0 | 0 | 16 | 33 | 7 |

No M3f case uses partial fallback in the clean-candidate set, so `-5=0` in all
M3f runs. This is good for diagnostic honesty, but no case eliminates all
transient negative statuses.

## Local State at Failure

The failed-particle table records particle id, position, region, return status,
MCC state, pore pressure, stress path proxies, and velocity diagnostics at the
failure frames. The important pattern is:

- failures are local and symmetric enough to follow the platen/edge geometry;
- most of the specimen converges normally at the same times;
- `code`, `excluded`, and `DtMin` remain clean;
- final reaction, p'-q, and pore-pressure curves remain bounded;
- many early failures are admissibility/tension-style `-1` statuses, while
  the persistent final baseline issue is line-search `-3`.

## Interpretation

The transient failures are local constitutive-return failures triggered by the
boundary/platen strain path rather than a global solver instability. The
evidence is:

- all cases remain numerically stable at the solver level;
- most particles converge normally in every frame;
- lower loading speed reduces the frequency and spatial spread of failures;
- higher max iterations and tighter return tolerance from M3d2 did not solve
  the final failed set;
- smoother ramp alone does not remove failures.

The failure region and timing point to local trial-stress admissibility and
strain-increment concentration near platen/edge regions. This is not a sign
convention regression and not a full-feedback effect, since feedback is off.

