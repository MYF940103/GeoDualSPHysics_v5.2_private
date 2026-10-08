# q0 k1e-4 resolution L2 slope-guide fix, 2026-07-14

The L2 convergence figure in
`tests/figures/resolution_k1em4_dp003_dp0005_dt2em6/resolution_k1em4_dp003_l2_error.png`
previously drew the first- and second-order reference lines from an arbitrary
point based on the maximum plotted error. Since the current dataset includes
known bad/outlier points (`dp = 0.03` and the `dp = 0.005` result at `Tv = 1`),
that made the reference lines look like misleading separation boundaries.

The plotting helper `tests/support/resolution_k1em4_convergence.py` was first
changed to anchor the slope guides at `dp = 0.02`, then corrected again after
review: if these lines are treated as order boundaries, the first-order line
should pass through `(dp/H, error) = (0.01, 0.01)` because `H = 1 m` in this
case.

The final plot now shows only `Tv = 0.05` and uses absolute order thresholds:

- dashed line: `error = dp/H`
- solid line: `error = (dp/H)^2`

The corrected plot was regenerated from the existing
`resolution_k1em4_dp003_targets.csv` data without rerunning the solver or
re-reading VTK particle files.
