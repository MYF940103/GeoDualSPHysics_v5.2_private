# Frozen pressure-row offline review — author only

New script: `tests/support/c08_h18_pressure_row_review_r1.py`. It is not executed by authoring, building or running the pressure-row component. Root must review it separately before the single authorized offline invocation:

`D:/anaconda3/python.exe -X utf8 -B tests/support/c08_h18_pressure_row_review_r1.py --execution-authorized`

It consumes only the completed `c08_h18_pressure_row_r1` component check, its bound owned call/build/completion receipts, and the five new component CSVs. It does not open original BI4/native/PRE, active GPU programs, physical source or traces; it launches no process, force, decoder or solver and performs no hash scan. The existing component's successful original-source/primary-state/ledger checks remain transitive prerequisites, not newly claimed native checks. The component check did not originally bind the five output CSV stats; this review records their actual pre/post-read stats and checks their complete schema and numerical contents without inventing an earlier binding.

Only fresh `tests/figures/c08_h18_pressure_row_review_r1/` and `tests/logs/c08_h18_pressure_row_review_r1.check.json` can be written. Existing complete or partial review outputs cause refusal. Failure preserves all partial derived outputs and records its first error; there is no overwrite, force rerun, decode, automatic next action or new physical candidate.

## Independent offline checks

- Exact 5000 soil IDs2060–7059, actual Part300 clock/completed2600000, all35,000 ID/basis and15,000 ID/width combinations,28 region/basis summaries and six normalized toy-CN rows. Regions are mutually exclusive: FS takes precedence over wall adjacency.
- Original5000 final-float literal bits and float-write budget; original rate, N−S*pi, manufactured and shadow budgets and completion counters. No physical tolerance is introduced. CSVs do not contain all absolute neighbour sums needed to reconstruct the original late-RHS operation-count budget, so that budget is retained through the bound source/component and re-enforced against the saved error; it is not falsely described as fully re-derived here.
- Current positive `M=gamma*n/Kw`, S fluid/wall partition, negative A counts, original hS/M, exact full6805 manufactured constant null, original analytic donor coverage, pressure-row/direct identities and summary reconstruction.
- Manufactured affine product-rule references retain original numerical gradJ. The saved CSV lacks full gradJ components, so the affine variable-k target is not independently reconstructed as continuum truth. Quadratic local targets, constants, analytic gradients, row/direct closure and all summaries are independently checked. Raw-FS Taylor omissions and boundary errors remain descriptive.
- For h5us/0.5us/0.05us, exact original explicit increments, BE and lagged-N midpoint denominators/flags, defined values, residual budgets and full-row rescalings. Undefined denominators retain blank values and explicit flags; finite negative denominators are never clipped. Final-pressure rescaling can hide tiny increments through addition cancellation; increment identities are checked separately.
- Six constant two-node matrix rows independently reconstruct real manufactured predictor-neighbour CN, rational delta and the declared third-order Taylor defect. They are not native midpoint states or a proof of full coupled time order.

## Figures and matching data

The three PNGs retain all receivers and all extremes:

1. `stiffness.png`: hS/M empirical distributions, full spatial field, negative-coefficient locations and region sign fractions. Source data: `row_metrics.csv`, `cohort_summary.csv`, `stiffness_ecdf.csv`.
2. `shadows.png`: native-width algebraic factors, width dependence of RMS(delta/h), spatial increment changes and original arithmetic-budget ratios. Source data: `shadow_per_ID.csv`, `shadow_summary.csv`, `arithmetic_checks.csv` plus row coordinates.
3. `manufactured.png`: all-basis regional row/reference errors, affine-gradient errors, affine spatial errors and normalized toy-CN Taylor defects. Source data: `manufactured_metrics.csv`, `coupled_CN_checks.csv` and the explicit affine response/reference/difference columns in `row_metrics.csv`. No data are smoothed, fitted, clipped, dropped or reinterpreted as a physical pressure trajectory.

Each graph prominently labels the scope. Native algebra uses frozen B, N(p_n), current wall pressures and acceleration: **not a genuine midpoint field, global implicit solution or physical repair**. M retains finite Kw. Nonnegative S or sparse negative A alone cannot prove stability, monotonicity, a suitable production scheme, absence of clumping or physical collapse acceptance. Smaller shadow widths are arithmetic observations, not new half-step runs. Toy normalized h is not C08 physical time. Force/CSV times are component observations, not a controlled CPU/GPU benchmark. Root must visually inspect the three produced PNGs; the check deliberately leaves `visual_QA_pending=true`.
