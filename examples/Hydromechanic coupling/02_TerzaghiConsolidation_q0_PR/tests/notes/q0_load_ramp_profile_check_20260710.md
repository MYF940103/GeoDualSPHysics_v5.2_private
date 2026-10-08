# q0 load-ramp pore-pressure profile check, 2026-07-10

Short CPU Release checks were run for the root `k=1e-4`, `dp=0.01` Terzaghi q0 case to inspect the pore-pressure build-up during the `0.01 s` ramp-load stage.

## Cases

- With damping: `CaseTerzaghiConsolidation_q0_PR_load_k1em4_t010_damp_Def.xml`
- Without damping: `CaseTerzaghiConsolidation_q0_PR_load_k1em4_t010_nodamp_Def.xml`

Common settings:

- `HydraulicConductivity=1e-4 m/s`
- `Dp=0.01 m`
- `HydroMechTopLoadRampTime=0.01 s`
- `HydroMechDrainageStartTime=0.01 s`
- `DtFixed=1e-5 s`
- `TimeMax=0.1 s`
- `TimeOut=0.0025 s`

## Outputs

- Profile figure: `figures/load_ramp_k1em4_t010_profiles.png`
- Profile data: `figures/load_ramp_k1em4_t010_profiles_data.csv`
- Summary data: `figures/load_ramp_k1em4_t010_summary.csv`

## Main observation

The damping and no-damping pressure profiles are almost identical during the first `0.01 s` of ramp loading. Damping only slightly lowers the lower-column excess pore pressure at `t=0.005 s`; it does not remove the loading-stage profile nonuniformity.

The ramp-load build-up is not a perfectly uniform vertical profile. Near the top of the column the excess pore pressure overshoots the nominal ramp target:

| Time (s) | Ramp target (kPa) | With damping max (kPa) | No damping max (kPa) |
|---:|---:|---:|---:|
| 0.0025 | 2.5 | 3.246 | 3.247 |
| 0.0050 | 5.0 | 6.494 | 6.495 |
| 0.0075 | 7.5 | 9.614 | 9.611 |
| 0.0100 | 10.0 | 12.712 | 12.709 |

Conclusion: for this q0 `k=1e-4`, `dp=0.01` setup, the early ramp-load pore-pressure profile is governed mainly by the loading/boundary response rather than by the small Bui-Fukagawa damping term. The damping-on and damping-off cases are stable and mutually close in pore pressure during `0-0.01 s`, but both show a top-layer overshoot relative to the nominal ramp-load target.

## Time-step sensitivity follow-up

The ramp-load check was repeated with `DtFixed=5e-6 s` for both damping and no-damping cases:

- With damping: `CaseTerzaghiConsolidation_q0_PR_load_k1em4_t010_dt5em6_damp_Def.xml`
- Without damping: `CaseTerzaghiConsolidation_q0_PR_load_k1em4_t010_dt5em6_nodamp_Def.xml`
- Comparison figure: `figures/load_ramp_k1em4_t010_dt_sensitivity_profiles.png`
- Reduced-time-step overlay: `figures/load_ramp_k1em4_t010_dt5em6_profiles_overlay.png`
- Data: `figures/load_ramp_k1em4_t010_dt_sensitivity_summary.csv`, `figures/load_ramp_k1em4_t010_dt_sensitivity_profiles_data.csv`

Halving the fixed time step does not materially change the loading-stage pressure profile. For the damping case, the maximum excess pore pressure changes only from `12.712 kPa` to `12.709 kPa` at `t=0.01 s`; the top-layer overshoot remains about `2.71 kPa` above the nominal `10 kPa` ramp target. This indicates that the observed ramp-stage nonuniformity is not primarily caused by the original `DtFixed=1e-5 s`.

A further damping-only run with `DtFixed=1e-6 s` was also completed:

- XML/BAT: `CaseTerzaghiConsolidation_q0_PR_load_k1em4_t010_dt1em6_damp_Def.xml`, `xCaseTerzaghiConsolidation_q0_PR_load_k1em4_t010_dt1em6_damp_win64_CPU.bat`
- Output: `CaseTerzaghiConsolidation_q0_PR_load_k1em4_t010_dt1em6_damp_out`
- Post-ramp comparison: `figures/load_ramp_k1em4_t010_postramp_profiles.png`
- Post-ramp data: `figures/load_ramp_k1em4_t010_postramp_summary.csv`, `figures/load_ramp_k1em4_t010_postramp_profiles_data.csv`

Reducing the time step to `1e-6 s` still does not remove the `t=0.01 s` top overshoot or bottom deficit. At `t=0.01 s`, the damping run has bottom excess pore pressure `9.324 kPa` and top maximum `12.708 kPa`. Looking later without changing `RampTime=0.01 s` shows that the bottom response catches up and oscillates around the nominal undrained `10 kPa`: bottom excess pore pressure is `11.054 kPa` at `0.0125 s`, `12.396 kPa` at `0.02 s`, `10.369 kPa` at `0.05 s`, and `10.116 kPa` at `0.1 s`. Thus the mismatch at exactly ramp end is a transient dynamic adjustment after loading, not a fixed-time-step truncation error.

## Delayed-drainage undrained stabilization window

To separate ramp loading from early drainage, another CPU Release check kept `HydroMechTopLoadRampTime=0.01 s` but delayed `HydroMechDrainageStartTime` to `0.1 s`:

- XML/BAT: `CaseTerzaghiConsolidation_q0_PR_load_k1em4_t010_drain010_damp_Def.xml`, `xCaseTerzaghiConsolidation_q0_PR_load_k1em4_t010_drain010_damp_win64_CPU.bat`
- Output: `CaseTerzaghiConsolidation_q0_PR_load_k1em4_t010_drain010_damp_out`
- Figures: `figures/load_ramp_k1em4_t010_drain010_profiles.png`, `figures/load_ramp_k1em4_t010_drain010_profiles_overlay.png`
- Data: `figures/load_ramp_k1em4_t010_drain010_summary.csv`, `figures/load_ramp_k1em4_t010_drain010_profiles_data.csv`

With drainage delayed, the inner column converges toward the expected undrained `10 kPa` profile after the dynamic ramp-load transient:

| Time (s) | Inner mean (kPa) | Inner RMS error to 10 kPa | Inner max abs error (kPa) | Bottom p_excess (kPa) |
|---:|---:|---:|---:|---:|
| 0.010 | 9.497 | 0.528 | 0.667 | 9.332 |
| 0.020 | 11.034 | 1.094 | 1.456 | 11.461 |
| 0.050 | 9.877 | 0.135 | 0.183 | 9.816 |
| 0.075 | 10.070 | 0.075 | 0.217 | 10.087 |
| 0.100 | 9.996 | 0.048 | 0.256 | 9.973 |

Conclusion: for this case, a non-drained stabilization window of about `0.05-0.1 s` after the `0.01 s` ramp is needed to reproduce a near-vertical undrained pore-pressure profile like the reference figure. The `0.1 s` state is the best current candidate if a Stage 2 restart is desired; the uppermost free-surface/load layer remains locally biased, so inner-column metrics are more representative than the top layer alone.

## Increased damping coefficient check

The delayed-drainage check was repeated with `SoilDampingCoef=0.04` while keeping `HydroMechTopLoadRampTime=0.01 s`, `HydroMechDrainageStartTime=0.1 s`, and `DtFixed=1e-5 s`.

The long descriptive case name exceeded a GenCase output-path limit when writing `Boundary_Actual.vtk`, so the successful rerun uses a short case name:

- XML/BAT: `CaseTCq0_load_D010_d04_Def.xml`, `xCaseTCq0_load_D010_d04_win64_CPU.bat`
- Output: `CaseTCq0_load_D010_d04_out`
- Comparison figure: `figures/load_ramp_k1em4_t010_drain010_damping_sensitivity_profiles.png`
- Data: `figures/load_ramp_k1em4_t010_drain010_damping_sensitivity_summary.csv`, `figures/load_ramp_k1em4_t010_drain010_damping_sensitivity_profiles_data.csv`

Increasing damping from `0.02` to `0.04` reduces the post-ramp oscillation and reaches the near-vertical undrained profile earlier:

| Time (s) | Inner RMS, coef 0.02 (kPa) | Inner RMS, coef 0.04 (kPa) |
|---:|---:|---:|
| 0.020 | 1.094 | 0.873 |
| 0.030 | 1.001 | 0.659 |
| 0.040 | 0.601 | 0.333 |
| 0.050 | 0.135 | 0.054 |
| 0.075 | 0.075 | 0.040 |
| 0.100 | 0.048 | 0.046 |

Conclusion: `SoilDampingCoef=0.04` is better for the Stage 1 undrained ramp-load stabilization window. A restart around `t=0.05-0.075 s` may already be adequate with `0.04`, while `t=0.1 s` remains the most conservative stable state. The topmost layer still has a local load/free-surface bias and should not be the only acceptance metric.

## Damping coefficient sweep

The delayed-drainage ramp-load case was swept further with short case names to avoid the `Boundary_Actual.vtk` path-length failure:

- `CaseTCq0_load_D010_d06`
- `CaseTCq0_load_D010_d08`
- `CaseTCq0_load_D010_d10`
- `CaseTCq0_load_D010_d12`
- `CaseTCq0_load_D010_d20`
- `CaseTCq0_load_D010_d40`

Together with the earlier `0.02` and `0.04` runs, the sweep shows that increasing damping does not make the bottom pore pressure reach the nominal `10 kPa` exactly at the ramp end (`t=0.01 s`). The best ramp-end bottom value is only about `9.36 kPa` around `SoilDampingCoef=0.06-0.10`; larger damping then worsens the ramp-end bottom value.

| SoilDampingCoef | Bottom excess at 0.01 s (kPa) | Inner RMS to 10 kPa at 0.01 s (kPa) | Top-layer excess at 0.01 s (kPa) | First stable time by RMS<0.15 kPa and bottom error<0.1 kPa |
|---:|---:|---:|---:|---:|
| 0.02 | 9.332 | 0.519 | 12.712 | 0.075 s |
| 0.04 | 9.348 | 0.501 | 12.714 | 0.050 s |
| 0.06 | 9.357 | 0.490 | 12.716 | 0.050 s |
| 0.08 | 9.360 | 0.484 | 12.717 | 0.050 s |
| 0.10 | 9.357 | 0.483 | 12.718 | 0.040 s |
| 0.12 | 9.349 | 0.486 | 12.719 | 0.040 s |
| 0.20 | 9.279 | 0.528 | 12.718 | 0.030 s |
| 0.40 | 8.927 | 0.778 | 12.706 | 0.015 s |

Outputs:

- `figures/load_ramp_k1em4_t010_drain010_damp_sweep_metrics.png`
- `figures/load_ramp_k1em4_t010_drain010_damp_sweep_summary.csv`
- `figures/load_ramp_k1em4_t010_drain010_damp_sweep_profiles_data.csv`
- `figures/load_ramp_k1em4_t010_drain010_damp_sweep_profiles_t0p01.png`
- `figures/load_ramp_k1em4_t010_drain010_damp_sweep_profiles_t0p05.png`
- `figures/load_ramp_k1em4_t010_drain010_damp_sweep_profiles_t0p075.png`
- `figures/load_ramp_k1em4_t010_drain010_damp_sweep_profiles_t0p1.png`

Conclusion: damping can shorten the post-ramp dynamic stabilization time, but it cannot by itself reproduce a fully uniform `10 kPa` profile exactly at `t=0.01 s`. For a balanced Stage 1 setup, `SoilDampingCoef=0.08-0.10` is the most useful range: it slightly improves the ramp-end inner profile and reaches the stable undrained state earlier without the stronger ramp-end bottom deficit seen at `0.20-0.40`. If the restart is allowed after the ramp, `t=0.04-0.05 s` is already acceptable for `0.08-0.12`, while `t=0.1 s` remains conservative.
