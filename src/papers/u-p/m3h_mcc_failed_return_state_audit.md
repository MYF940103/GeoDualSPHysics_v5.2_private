# M3h MCC Failed Return State Audit

## Objective

M3h revisits the local MCC return failures left by M3f.  The goal is to
separate solver-scale instability from local constitutive inadmissibility in
the explicit-platen, feedback-off MCC triaxial smoke.

The audit uses the M3h output in:

`examples/u-pw/04_Undrained_Triaxial/experiments/M3h_MCCAdmissibleReturn/`

and the generated CSV files:

- `m3h_failed_return_state.csv`
- `m3h_failed_return_region_summary.csv`
- `m3h_trial_state_diagnostics.csv`

## Available and Missing Diagnostics

M3h adds persistent per-particle line-search diagnostics:

- `MccLineSearchBacktrackCount`
- `MccLineSearchRejectReason`
- `MccLineSearchMinAlpha`

The prior M3f output did not persist the local trial stress invariants before
the Newton return.  M3h therefore reports the trial-state columns with
`trial_state_available=0` in `m3h_trial_state_diagnostics.csv`.  The audit uses
the saved post-return/failed-state `p'`, `q`, `pc`, plastic variables, local
velocity, `DivVel`, `PorePressRate`, and the new line-search aggregate fields.

## Case Set

| case | loading | return controls |
| --- | --- | --- |
| `baseline` | original rate | old single-step path |
| `admissible_line` | original rate | admissible line search, no substepping |
| `adaptive_line` | original rate | adaptive substepping plus admissible line search |
| `half_speed_adaptive_line` | half rate | adaptive substepping plus admissible line search |
| `quarter_speed_line` | quarter rate | adaptive substepping plus admissible line search |

All cases are CPU-only, feedback-off, and use the same mild MCC parameters and
explicit platen workflow.

## Solver-Level Status

All M3h cases finish with:

```text
code=0
excluded=0
DtMin=0
```

The return failures are therefore local MCC return failures, not global SPH
solver failures.

## Return Status Summary

| case | final `-3` | final `-5` | final `-1` | max `-3` | max `-5` | max `-1` | bad frames | clean |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline | 8 | 0 | 0 | 9 | 0 | 157 | 22 | 0 |
| admissible_line | 8 | 0 | 0 | 9 | 0 | 157 | 22 | 0 |
| adaptive_line | 10 | 0 | 8 | 16 | 0 | 92 | 35 | 0 |
| half_speed_adaptive_line | 0 | 0 | 0 | 8 | 0 | 100 | 23 | 0 |
| quarter_speed_line | 0 | 0 | 0 | 16 | 0 | 33 | 7 | 0 |

No case passes the strict clean gate because all cases retain at least one
saved frame with a negative return status.

## Failure Locations

Failed return records remain concentrated near platen and edge-adjacent
regions:

- `baseline` and `admissible_line` have `-3` records in interior, bottom cap
  zone, edge, lateral boundary, and top cap zone;
- `adaptive_line` spreads `-3` failures into interior, bottom cap, top cap,
  lateral, and edge records;
- `half_speed_adaptive_line` reduces the final frame to clean status but still
  has transient `-3` records, mostly edge and bottom-cap/top-cap adjacent;
- `quarter_speed_line` has the fewest bad frames, but still shows transient
  `-3` records in edge and bottom-cap zones.

This supports the M3f interpretation: the failure is local to platen/edge
strain paths, not a domain-wide MCC sign or hardening failure.

## State at Failed Returns

The failed-state ranges are physically bounded.  Representative values from
`m3h_failed_return_state.csv` are:

| group | p' range (Pa) | max q (Pa) | pc range (Pa) | plastic multiplier range | max backtrack | max reject reason |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline `-1` | -122.34 to -0.074 | 361.22 | 119.27 to 120.00 | 0 to 0 | 0 | 0 |
| baseline `-3` | 25.06 to 73.97 | 98.40 | 119.43 to 120.14 | 0 to 0 | 12 | 4 |
| admissible_line `-3` | 25.06 to 73.97 | 98.40 | 119.43 to 120.14 | 0 to 0 | 32 | 4 |
| adaptive_line `-1` | 2.35 to 20.23 | 53.73 | 118.50 to 120.00 | 3.15e-8 to 8.31e-7 | 45 | 6 |
| adaptive_line `-3` | 29.96 to 69.68 | 72.03 | 119.57 to 120.11 | 5.06e-8 to 5.96e-7 | 92 | 4 |
| half_speed `-3` | 29.70 to 51.93 | 71.35 | 119.72 to 120.00 | 4.10e-8 to 3.05e-7 | 70 | 4 |
| quarter_speed `-3` | 28.97 to 45.11 | 69.68 | 119.77 to 119.87 | 9.81e-8 to 1.49e-7 | 58 | 4 |

The early `-1` statuses in the baseline and admissible-line cases correspond
to negative or near-zero saved `p'`, so they are tension/admissibility
problems.  The later `-3` statuses have positive `p'` and valid `pc`, pointing
to line-search / Newton path failure rather than loss of sign convention or
negative `pc`.

## Line-Search Diagnostics

The new line-search fields show:

- baseline uses the old 12-backtrack path and still reaches reject reason `6`
  in some failed records;
- admissible_line increases allowed backtracks to 32 but reproduces the same
  final `-3:8` set;
- adaptive_line accumulates more backtracking through substeps and worsens the
  final state to `-3:10|-1:8`;
- half-speed and quarter-speed reduce the final failed set to zero, but still
  retain transient bad frames.

The smallest accepted alpha in line-search cases is about `2.33e-10`.  This
confirms that the local return path is being driven into very small admissible
steps near boundary/platen strain concentrations.

## Interpretation

The M3h failed-return evidence confirms:

1. The issue is local, concentrated near platen/edge regions.
2. The `-1` family is tied to inadmissible or near-tension saved `p'`.
3. The persistent `-3` family is a line-search / local return robustness issue
   with otherwise finite `pc`, void ratio, and plastic variables.
4. Increasing backtracking alone does not clean the original-rate route.
5. Slower loading reduces final failures but does not remove transient saved
   failures.

The current data do not yet support a clean MCC validation package.
