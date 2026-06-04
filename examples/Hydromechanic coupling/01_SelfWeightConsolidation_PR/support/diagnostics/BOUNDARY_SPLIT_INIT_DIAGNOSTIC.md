# Boundary split initialization diagnostic

Date: 2026-06-04

Code change under test: analytical 1D initialization now splits boundary pore
pressure as:

```text
PorePress0_boundary = hydrostatic pressure at actual boundary position
PorePress_boundary  = PorePress0_boundary + excess pore pressure at mDBC ghost/interface position
```

This keeps the hydrostatic part consistent with the PR seepage `lapz` coordinate,
while keeping the undrained excess-pore-pressure condition tied to the mDBC ghost
projection.

## Run

Output folder:

```text
support/diagnostics/diag4_scenario2_boundarysplit_fixeddt_t04
```

Command settings:

- Scenario 2 analytical initialization.
- Gravity on.
- `DtFixed = 1e-6`.
- `tmax = 0.4 s`.
- `tout = 0.02 s`.

The solver used exactly 400000 steps for 0.4 s.

## Bottom excess pore pressure

Values are bottom-layer averages in Pa.

| case | time (s) | bottom excess | theory | RMS error |
|---|---:|---:|---:|---:|
| before boundary split fix | 0.10 | 7424.7 | 8738.1 | 369.6 |
| before boundary split fix | 0.20 | 6012.3 | 7906.0 | 638.4 |
| before boundary split fix | 0.40 | 4023.4 | 6729.3 | 1091.6 |
| after boundary split fix | 0.10 | 8795.7 | 8738.1 | 48.8 |
| after boundary split fix | 0.20 | 7959.8 | 7906.0 | 44.5 |
| after boundary split fix | 0.40 | 6778.3 | 6729.3 | 39.4 |

The corrected analytical-initialization run now follows the Terzaghi solution in
the early drainage interval. The remaining error at 0.4 s is about 49 Pa at the
bottom layer.

## Boundary state check

Initial state after the fix:

| group | z range | mean PorePress | mean PorePress0 | mean excess |
|---|---:|---:|---:|---:|
| bottom boundary | -0.035 to -0.015 | 20534.2 | 10055.3 | 10478.9 |
| bottom fluid layer | 0.005 to 0.015 | 20352.0 | 9711.9 | 10640.1 |

State at 0.4 s:

| group | z range | mean PorePress | mean PorePress0 | mean excess |
|---|---:|---:|---:|---:|
| bottom boundary | -0.035 to -0.015 | 16827.6 | 10055.3 | 6772.3 |
| bottom fluid layer | 0.004974 to 0.014966 | 16489.5 | 9711.9 | 6777.6 |

The bottom boundary now has a higher hydrostatic baseline than the bottom soil
layer, as expected from its deeper actual position, while excess pore pressure is
consistent with the ghost-projected impermeable boundary condition.
