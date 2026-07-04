# Self-weight Scenario 2 baseline oscillation postprocess, 2026-06-29

## Purpose

Perform pure postprocessing on the retained baseline output:

- `tests/outputs/CaseSWScenario2_restart_p0060_D_DTv0005_out`

The goal is to locate the time-factor windows where the bottom excess pore pressure departs from theory, partly recovers, and departs again, then compare those windows with velocity, stress, and an approximate velocity-divergence indicator.

No C++/CUDA source code was modified for this postprocess.

## Generated files

- Script: `tests/support/diagnose_scenario2_baseline_oscillations.py`
- Figure folder: `tests/figures/CaseSWScenario2_restart_p0060_D_DTv0005_oscillation_diagnosis`
- Time series: `scenario2_baseline_oscillation_timeseries.csv`
- Detected windows: `scenario2_baseline_oscillation_windows.csv`
- Diagnostic figure: `scenario2_baseline_oscillation_diagnostics.png`
- VTK field list: `available_vtk_arrays.txt`

Available VTK arrays:

`ExcessPorePress`, `FSNormal`, `FSType`, `Idp`, `Kplastic`, `Mk`, `PorePress`, `PorePress0`, `Press`, `Rhop`, `Sigma_ij`, `Sigma_kk`, `Type`, `Vel`.

`divv` is not present in the retained VTK files. The postprocess therefore uses the bottom-layer / lower-column layer-averaged `dvz/dz` as a proxy for 1D velocity divergence. This is diagnostic only, not a replacement for a direct `divv` output.

## Main detected mid/late windows

Residual is defined as:

`bottom_error = bottom_excess_SPH - bottom_excess_Terzaghi`

Important slope sign-change windows after the early transient:

| Center part | Tv window | Center Tv | Slope change | bottom error (kPa) | bottom d(error)/dTv (kPa) | bottom vz (m/s) | bottom dvz/dz proxy (1/s) | bottom sigma_zz error (Pa) |
| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| PartFluid_0053 | 0.255-0.275 | 0.265 | + to - | 0.11555 | -0.15360 | -2.337e-05 | -1.254e-03 | -6100 |
| PartFluid_0065 | 0.315-0.335 | 0.325 | - to + | 0.06897 | +0.81444 | -1.496e-05 | -9.209e-04 | -6761 |
| PartFluid_0085 | 0.415-0.435 | 0.425 | + to - | 0.15570 | -0.06348 | -1.643e-05 | -8.798e-04 | -7516 |
| PartFluid_0105 | 0.515-0.535 | 0.525 | - to + | 0.07354 | +0.65149 | -2.799e-06 | -5.610e-04 | -8253 |
| PartFluid_0140 | 0.690-0.710 | 0.700 | + to - | 0.19100 | -0.09989 | -6.218e-06 | -3.744e-04 | -8964 |
| PartFluid_0171 | 0.845-0.865 | 0.855 | - to + | 0.09484 | +0.08885 | -5.443e-06 | -3.788e-04 | -9543 |

After `Tv ~= 0.855`, the bottom residual grows rapidly. The largest sustained late slope is around `Tv ~= 0.92-0.95`, where `d(error)/dTv` is about `2.0 kPa/Tv`.

## Interpretation

The postprocess supports the current working view that the late discrepancy is not a simple inherited initial-state offset:

- The early dissipation agrees well with theory.
- The bottom residual evolves non-monotonically: it grows, recovers, then grows again.
- Several residual slope reversals coincide with clear changes in the bottom `dvz/dz` proxy.
- The stress residual is mostly a slow monotonic drift and does not by itself explain the oscillatory residual shape.

The strongest suspect is therefore a coupled dynamic / kinematic disturbance during Scenario 2, visible through the velocity-gradient proxy. The retained baseline output does not include direct `divv`, so the next diagnostic should either output `divv` directly or add a temporary postprocess-only equivalent based on stored velocity components.

## Recommended next step

Prepare one short diagnostic rerun over the most informative windows, not a full parameter sweep:

1. Restart before `Tv ~= 0.30` and output at a finer interval around `Tv ~= 0.30-0.34`.
2. Restart before `Tv ~= 0.50` and output at a finer interval around `Tv ~= 0.50-0.54`.
3. Include direct `divv` or an equivalent hydromechanical compression-rate diagnostic in VTK output if available.
4. Keep physical parameters unchanged for the first rerun; the purpose is to identify the source of the disturbance, not tune it away.
