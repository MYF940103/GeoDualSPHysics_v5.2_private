# Cryer ramp-time refinement notes (2026-06-20)

## Purpose

Continue tuning `HydroMechTopLoadRampTime` for the 003 Cryer case with drainage opened from the start (`HydroMechDrainage=1`, `HydroMechDrainageStartTime=0`) and `FlexibleConfinement` loading. The target was to reduce the initial overshoot while avoiding an increase in particle velocity.

Common settings:

- Particle resolution: 003
- Loading mode: `FlexibleConfinement`
- Drainage: enabled from `t=0`
- `k=1e-4`
- `SoilDampingCoef=0.02`
- Analytical time alignment: `t_analytic = t - HydroMechTopLoadRampTime`

## Short-window ramp scan

The short-window metric uses the first approximately 0.005 s after the ramp ends.

| Case | Ramp time (s) | Peak center p/q0 | RMSE | Max speed (m/s) | Comment |
| --- | ---: | ---: | ---: | ---: | --- |
| r010 full short window | 0.0100 | 1.1261 | 0.0955 | 0.00717 | Higher peak overshoot and higher max speed. |
| r0110 short | 0.0110 | 1.1104 | 0.0884 | 0.00675 | Better than 0.010, but still larger peak and speed than 0.0115. |
| r0115 short | 0.0115 | 1.0971 | 0.0825 | 0.00597 | Best short-window compromise in this scan. |
| r0125 short | 0.0125 | 1.0765 | 0.0998 | 0.00568 | Peak and speed decrease, but early post-ramp pressure drops too fast. |
| r015 short | 0.0150 | 1.0311 | 0.1541 | 0.00549 | Ramp is too long; early response is overly damped/under-predicted. |

Conclusion: `HydroMechTopLoadRampTime=0.0115` is the best local compromise from this scan. It reduces the velocity relative to 0.010 s and avoids the excessive early under-prediction seen for 0.0125-0.015 s.

## Full-cycle validation with RampTime=0.0115 s

Case: `refinement/ramp_refine_20260620/r0115_drain0_full`

Key metrics:

- Peak center pore pressure: `1.0860 q0`
- Theory at peak time: `1.0645 q0`
- Peak absolute error at peak time: `0.0215 q0`
- Maximum absolute error over full aligned curve: `0.1539 q0` at `t=0.0175 s` (`Tv=0.0659`)
- Full-cycle RMSE: `0.0453`
- Full-cycle MAE: `0.0287`
- Maximum velocity: `0.00463 m/s`
- Final center pore pressure: `0.00291 q0`

Compared with the previous `RampTime=0.010 s` full run:

- Peak overshoot is strongly reduced: `1.1261 q0 -> 1.0860 q0`.
- Maximum velocity is reduced: `0.00717 m/s -> 0.00463 m/s`.
- Full-cycle RMSE is slightly worse: `0.0416 -> 0.0453`, mainly because the early post-ramp response around `Tv~0.066` remains under-predicted.

Overall conclusion: `RampTime=0.0115 s` is preferable if the current priority is to reduce initial overshoot and keep velocity from increasing. `RampTime=0.010 s` still gives a slightly lower full-cycle RMSE, but it produces a larger initial overshoot and larger max velocity.

## Generated figures and summaries

- `figures/cryer_r0115_drain0_full_center_pressure.png`
- `figures/cryer_r010_vs_r0115_full_center_pressure.png`
- `figures/cryer_ramp_refine_20260620_short_window.png`
- `figures/cryer_ramp_refine_20260620_metrics.json`

## Theory correction update

The original metrics in this note were computed with an incorrect implementation
of the Cryer analytical series. The implementation has since been corrected to
match the u-pw reference paper Equations (46)-(47):

- root equation: `(1 - eta*xi^2/2) tan(xi) = xi`;
- center pressure coefficient denominator:
  `eta*xi*cos(xi)/2 + (eta - 1)*sin(xi)`;
- paper-style plot axes: logarithmic `T_v` on the x-axis and normalized pore
  pressure `p^w/p0` on the y-axis.

Corrected output files:

- `figures/cryer_r0115_drain0_full_paper_axes_corrected_theory.png`
- `figures/cryer_r010_vs_r0115_full_paper_axes_corrected_theory.png`
- `figures/cryer_ramp_refine_20260620_short_window_paper_axes_corrected_theory.png`
- `figures/cryer_ramp_refine_20260620_metrics_corrected_theory.json`
- `refinement/ramp_refine_20260620/r0115_drain0_full/analysis/r0115_drain0_full_summary_corrected_theory.json`
- `refinement/r010_drain0_full_20260620/analysis/r010_drain0_full_summary_corrected_theory.json`

With the corrected analytical solution, the reference peak for `nu=0.3` is
about `1.24 p0`, so the current numerical results under-predict the
Mandel-Cryer peak. The previous conclusion that `RampTime=0.0115 s` closely
matches the peak should be treated as superseded. The `0.0115 s` case still
reduces the maximum velocity compared with `0.010 s`, but it is not yet close to
the corrected analytical peak.

## Data cleanup

Short-window cases were used only for parameter selection and their heavy `out` folders can be removed after preserving this note and the analysis summaries. The full validation output for `r0115_drain0_full` should be retained.
