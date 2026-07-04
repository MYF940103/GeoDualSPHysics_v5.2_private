# Self-weight Scenario 2 pore-rate component window diagnostics

Date: 2026-06-29

Purpose: diagnose the mid/late Scenario 2 excess pore-pressure oscillation without rerunning the full case. A temporary GPU diagnostic mapped pore-pressure rate components to `HydroMechLoadAce`:

- `HydroMechLoadAce.x`: compression term, `K_w/n * (-divv)`, kPa/s
- `HydroMechLoadAce.y`: Darcy pressure-gradient Laplacian term, kPa/s
- `HydroMechLoadAce.z`: gravity-head term, kPa/s

Diagnostic windows:

- `Tv=0.300-0.340`: `outputs/CaseSWScenario2_restart_p0060_D_ratecomp_Tv030_034_out`
- `Tv=0.500-0.540`: `outputs/CaseSWScenario2_restart_p0100_D_ratecomp_Tv050_054_out`

Evidence files:

- `figures/CaseSWScenario2_restart_p0060_D_ratecomp_Tv030_034/rate_component_window_timeseries.csv`
- `figures/CaseSWScenario2_restart_p0060_D_ratecomp_Tv030_034/rate_component_window_diagnostics.png`
- `figures/CaseSWScenario2_restart_p0100_D_ratecomp_Tv050_054/rate_component_window_timeseries.csv`
- `figures/CaseSWScenario2_restart_p0100_D_ratecomp_Tv050_054/rate_component_window_diagnostics.png`
- `figures/self_weight_scenario2_rate_component_window_compare/rate_component_event_summary.csv`

## Findings

The error-slope sign changes are localized and repeatable:

- `Tv030_034`: `d(error)/dTv` crosses from negative to positive between `Tv=0.320` and `0.321`.
- `Tv050_054`: `d(error)/dTv` crosses from negative to positive between `Tv=0.521` and `0.522`.

Around `Tv=0.3205`:

- Pre-window mean (`Tv=0.309-0.317`): compression `+802.7 kPa/s`, Darcy lapw `-815.2 kPa/s`, gravity head `+9.49 kPa/s`, component total `-3.07 kPa/s`, actual bottom `dEPWP/dt=-3.11 kPa/s`, `d(error)/dTv=-1.39`.
- Post-window mean (`Tv=0.324-0.332`): compression `+624.8 kPa/s`, Darcy lapw `-637.4 kPa/s`, gravity head `+9.91 kPa/s`, component total `-2.74 kPa/s`, actual bottom `dEPWP/dt=-2.31 kPa/s`, `d(error)/dTv=+1.18`.

Around `Tv=0.5215`:

- Pre-window mean (`Tv=0.510-0.518`): compression `+486.7 kPa/s`, Darcy lapw `-501.3 kPa/s`, gravity head `+12.09 kPa/s`, component total `-2.46 kPa/s`, actual bottom `dEPWP/dt=-2.06 kPa/s`, `d(error)/dTv=-1.47`.
- Post-window mean (`Tv=0.525-0.533`): compression `+255.0 kPa/s`, Darcy lapw `-269.3 kPa/s`, gravity head `+13.22 kPa/s`, component total `-1.16 kPa/s`, actual bottom `dEPWP/dt=-1.28 kPa/s`, `d(error)/dTv=+1.18`.

Interpretation:

- The late mismatch is not a uniform slow-diffusion problem. It appears as localized rate-state changes that make bottom EPWP dissipation suddenly slower.
- The gravity-head term is smooth and small compared with the other two terms, so it is not the source of the jump.
- The two dominant terms, compression and Darcy lapw, both drop sharply in magnitude at the same transition. They remain nearly cancelling, so a modest relative imbalance changes the net pore-pressure rate enough to flip the residual slope.
- The bottom `vz` and simple bottom/lower `dvz/dz` proxies change smoothly and do not show a matching sign flip. The direct compression pore-rate term does jump, so the disturbance is likely inside the SPH neighbor-loop evaluation of `divv`/corrected gradients and the pressure Laplacian, not simply in the bottom-column velocity proxy.

Suggested next checks:

1. Output or sample the corrected-gradient ingredients used by the pore-rate loop near the bottom particle: correction matrix quality, neighbor count, and effective support composition.
2. Compare the same windows with mDBC pore-pressure corrector disabled/enabled only if the support-composition diagnostics implicate boundary neighbors.
3. The two diagnostic windows did not use pore-pressure Shepard regularization (`PoreShepardRegularization=0`, runtime `Disabled`), so the observed jumps cannot be attributed to Shepard filtering.
4. If needed, run a CPU/GPU one-window comparison with identical high-frequency output to exclude GPU-only arithmetic/order effects.

Cleanup status:

- Removed the temporary `HYDROMECH_PORERATE_COMPONENT_DIAG` source changes from `source/JSphGpu_ker.cu`.
- Rebuilt GPU Release after cleanup. The restored executable is `bin/windows/DualSPHysics5.2_GEO_win64.exe`, timestamp `2026-06-29 15:02:54`.
- Build log: `tests/run_gpu_release_cleanup_build.log`.
