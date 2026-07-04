# Self-weight Scenario2 full damping=0.02 run

Date: 2026-06-29

## Purpose

This full run checked whether increasing `SoilDampingCoef` from the current
baseline `4e-5` to `0.02` can remove the late-time bottom excess pore-pressure
plateau observed in Scenario2.

The run inherits the accepted Stage1 baseline:

- Stage1 output: `tests/outputs/CaseSWStage1_d02_D_SH40_FS_out/data`
- Restart part: `Part_0060`
- Scenario2 run: `tests/outputs/CaseSWScenario2_restart_p0060_D_DTv0005_damp002_out`
- Scenario2 figures: `tests/figures/CaseSWScenario2_restart_p0060_D_DTv0005_damp002`

The only intended change relative to the current Scenario2 baseline was:

- `SoilDampingCoef=0.02`

`Run.out` confirmed:

- `SoilDampingCoef=0.02`
- `Cs0=35.80574408560461`
- `CteB=384615.4`
- `PorePress`, `PorePress0`, and `Sigma` inherited from the Stage1 restart
- excluded particles: `0`

## Bottom excess pore-pressure comparison

Comparison files were saved in:

- `tests/figures/scenario2_damping_compare/scenario2_damping_compare_targets.csv`
- `tests/figures/scenario2_damping_compare/scenario2_damping_compare_bottom_curve.csv`
- `tests/figures/scenario2_damping_compare/scenario2_damping_compare_bottom_curve.png`

Key values in kPa:

| Tv | Theory | baseline `4e-5` | damping `0.02` | damping - baseline |
|---:|---:|---:|---:|---:|
| 0.005 | 9.8890 | 9.9582 | 9.8637 | -0.0945 |
| 0.050 | 8.0355 | 8.1029 | 8.0528 | -0.0501 |
| 0.100 | 6.9124 | 6.9921 | 6.9549 | -0.0372 |
| 0.250 | 4.7048 | 4.8193 | 4.8050 | -0.0143 |
| 0.400 | 3.2469 | 3.3983 | 3.3967 | -0.0017 |
| 0.500 | 2.5369 | 2.6385 | 2.6423 | +0.0038 |
| 0.700 | 1.5488 | 1.7398 | 1.7428 | +0.0031 |
| 1.000 | 0.7388 | 1.0818 | 1.0805 | -0.0013 |

## Conclusion

Full-history `SoilDampingCoef=0.02` does not fix the late-time dissipation
plateau. It improves the early profile and target errors up to about
`Tv=0.25`, but from `Tv=0.4` onward it is effectively indistinguishable from
the baseline. At `Tv=1.0`, the improvement in bottom excess pore pressure is
only about `0.0013 kPa`, while the remaining error is about `0.342 kPa`.

This means the short high-damping restart from `Part_0180` was a local
continuation effect, not a robust full-history fix. The late-time plateau should
not be solved by simply increasing global soil damping from the beginning of
Scenario2.

## Recommended next direction

The evidence now points to a time-history-dependent coupled oscillation rather
than insufficient constant damping. The next useful diagnostics are:

1. Local damping activation only after the onset window, e.g. restart from
   `Tv=0.7-0.85` with `SoilDampingCoef=0.02`, to confirm whether damping can
   still remove the plateau when applied after the earlier history has formed.
2. Time-averaged pore-rate decomposition over full output intervals, not only
   instantaneous end-of-interval values.
3. Check whether the residual volumetric strain/velocity field accumulated
   during `Tv=0.25-0.7` is responsible for the later cancellation of hydraulic
   diffusion.
