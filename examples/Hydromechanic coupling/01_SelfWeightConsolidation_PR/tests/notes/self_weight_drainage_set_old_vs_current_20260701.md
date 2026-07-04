# Self-weight drainage-set old versus current check

Date: 2026-07-01

## Purpose

Check whether the current drained free-surface predicate changes the particles constrained to `PorePress=0` compared with the old upward-normal predicate from the `a407fbd` CPU baseline.

## Method

Used the full `CaseSWScenario2_Mode3_StandaloneRate_CPU` VTK output and exported `FSType` and `FSNormal` for target parts.

Compared:

- Current predicate for this non-strip case: drain `FSType` free-surface/isolated particles.
- Old predicate: drain only free-surface/isolated particles whose normal points upward (`nz/|n| > 0.35`, with gravity in `-z`).

## Result

At all target time factors (`Tv=0`, `0.005`, `0.05`, `0.1`, `0.25`, `0.4`, `0.5`, `0.7`, `1.0`):

- Current drained count: `10`.
- Old upward-normal drained count: `10`.
- Current-extra drained count: `0`.
- `FSType` counts: `0:990; 2:10`.

## Decision

The free-surface drainage predicate change does not explain the current mismatch with the old CPU baseline for this 1D self-weight consolidation case.

Summary CSV kept:

- `tests/figures/CaseSWScenario2_Mode3_StandaloneRate_CPU_vs_old_cpu/drained_set_current_vs_old_normal.csv`

Raw temporary PartVTK CSV exports were deleted.
