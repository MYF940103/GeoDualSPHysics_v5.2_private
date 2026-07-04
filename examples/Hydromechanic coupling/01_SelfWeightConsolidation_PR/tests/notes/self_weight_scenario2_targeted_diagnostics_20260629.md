# Self-weight Scenario 2 targeted diagnostics, 2026-06-29

## Context

Scenario 2 restarted from the improved Stage 1 state gives a better early undrained profile than the old analytical-init workflow, but the late-time bottom excess pore pressure plateaus above the 1D consolidation theory. A full run with `SoilDampingCoef=0.02` did not remove this late-time discrepancy.

The purpose of this diagnostic was to determine whether the error is mainly caused by insufficient local damping after `Tv ~= 0.9`, or by cancellation between the pore-pressure rate terms.

## Diagnostic 1: local high damping from `Tv ~= 0.9` to `Tv ~= 1.0`

Case:

- Config: `tests/configs/CaseSWScenario2_restart_p0180_D_DTv0005_damp002_toTv1_Def.xml`
- BAT: `tests/xCaseSWScenario2_restart_p0180_D_DTv0005_damp002_toTv1_win64_GPU.bat`
- Restart source: `tests/outputs/CaseSWScenario2_restart_p0060_D_DTv0005_out/data`, `Part_0180`
- Damping: `SoilDampingCoef=0.02`
- Output: `tests/figures/CaseSWScenario2_restart_p0180_D_DTv0005_damp002_toTv1/scenario2_target_summary.csv`

Key bottom excess pore pressure:

| Tv | SPH bottom excess (kPa) | Theory (kPa) |
| --- | ---: | ---: |
| 0.900 | 1.091327 | 0.945513 |
| 0.905 | 1.081187 | 0.933920 |
| 0.950 | 1.078257 | 0.835774 |
| 1.000 | 1.075572 | 0.738771 |

Conclusion: increasing damping only over the late window does not restore the theoretical late dissipation. The bottom pore pressure remains almost flat from `Tv=0.905` to `Tv=1.0`.

## Diagnostic 2: interval-averaged pore-rate components

Temporary GPU diagnostics were added only for this run to accumulate the component contributions in `HydroMechLoadAce`; they were removed immediately after the test and GPU Release was rebuilt successfully.

Case:

- Config: `tests/configs/CaseSWScenario2_restart_p0180_D_rateavg_toTv1_Def.xml`
- BAT: `tests/xCaseSWScenario2_restart_p0180_D_rateavg_toTv1_win64_GPU.bat`
- Restart source: same `Part_0180`
- Damping: baseline value, `SoilDampingCoef=4e-5`
- Output CSV: `tests/figures/CaseSWScenario2_restart_p0180_D_rateavg_toTv1/pore_rate_components_interval_average.csv`
- Output figure: `tests/figures/CaseSWScenario2_restart_p0180_D_rateavg_toTv1/pore_rate_components_interval_average.png`

Representative bottom-layer interval averages:

| Interval Tv | Compression (kPa/s) | Darcy lapw (kPa/s) | Gravity head (kPa/s) | Component total (kPa/s) | Actual bottom dEPWP/dt (kPa/s) |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0.900 -> 0.905 | +499.391 | -538.234 | +37.695 | -1.148 | -0.0895 |
| 0.995 -> 1.000 | +499.003 | -529.529 | +38.507 | +7.980 | -0.0147 |

The component total and actual `dEPWP/dt` are not expected to match exactly in this diagnostic because the symplectic force evaluations are accumulated over internal calls and are not a single equal-weight end-of-step rate. The robust qualitative result is the component balance:

- Darcy pressure diffusion is present and large.
- It is nearly cancelled by the compression term plus the gravity-head seepage term.
- The plateau is therefore not a simple "diffusion coefficient too small" problem.

## Revised interpretation

The diagnostic proves that the late discrepancy is not removed by increasing global damping and is not caused by a missing pressure-diffusion term. It does **not** prove that the main cause is the Stage 1 inherited state.

The profile evolution and bottom-dissipation curve show good early agreement with theory, then several mid/late deviations where the result first moves away from theory, partly recovers near `Tv ~= 0.4`, and later deviates again. This behavior is more consistent with intermittent numerical oscillations or coupled mechanical-hydraulic disturbances during Scenario 2 than with a static initial-state error inherited from Stage 1.

## Recommended next tests

1. Locate the onset times of the mid/late oscillations using bottom pressure, velocity, `divv`, and stress histories.
2. Compare bottom-layer `divv`, vertical velocity gradient, settlement, and strain history between:
   - old analytical-init Scenario 2 output, and
   - restart-from-Stage-1 Scenario 2 output.
3. Run a controlled "frozen skeleton" or near-pure-diffusion restart from the improved Stage 1 pore-pressure profile to confirm that the hydraulic part alone dissipates at the theoretical rate.
4. If the hydraulic-only behavior is correct, focus on the mechanism that injects mid/late mechanical oscillations during Scenario 2, rather than treating Stage 1 inheritance as the primary explanation.

## Cleanup status

- Temporary source diagnostics were removed from `source/JSphGpu_ker.cu` and `source/JSphGpu.cpp`.
- GPU Release was rebuilt successfully after cleanup.
- Test-support postprocessing script kept for repeatable diagnostics:
  `tests/support/postprocess_porerate_components_avg_diag.py`.
