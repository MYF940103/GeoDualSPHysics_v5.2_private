# Server full Cryer result: center r <= 1dp

Date: 2026-06-22

## Source result

- Case output: `CaseCryerProblem_PR_out`
- Particle files: `CaseCryerProblem_PR_out/particles/PartFluid_0000.vtk` to `PartFluid_1000.vtk`
- `Run.csv`: GPU run, `PhysicalTime = 0.910931 s`, `PartFiles = 1001`
- Resolution: `Dp = 0.0025 m`
- Permeability used by the current formal case: `k = 1e-5`
- Soil damping in this completed server run: `SoilDampingCoef = 0.02`

## Post-processing

- Center pore pressure sampling radius: `r <= 1dp = 0.0025 m`
- Plotted time range: `T_v = 0.001` to `1.0`
- Normalized pressure: `p^w(0,t) / p0`
- Plot style: log-scale `T_v` axis and normalized center pore pressure axis, matching the u-pw Cryer reference figure convention.

## Generated files

- `figures/cryer_server_full_dp0025_k1e5_center_r1dp.csv`
- `figures/cryer_server_full_dp0025_k1e5_center_r1dp_paper_axes.png`
- `figures/cryer_server_full_dp0025_k1e5_center_r1dp_paper_axes.pdf`
- `figures/cryer_server_full_dp0025_k1e5_center_r1dp_peak_zoom.png`
- `figures/cryer_server_full_dp0025_k1e5_center_r1dp_paper_metrics.json`

## Metrics

- Points used: `1000`
- RMSE over `T_v = 0.001..1.0`: `0.02276091`
- MAE over `T_v = 0.001..1.0`: `0.01790222`
- Numerical peak: `p/p0 = 1.2159517` at `T_v = 0.049`
- Analytical peak: `p/p0 = 1.2490075` at `T_v = 0.046`
- Numerical value at analytical peak time: `p/p0 = 1.2148734`
- Peak deficit at analytical peak time: `-0.0341341`, about `2.7%` of `p0`
- Final value at `T_v = 1`: numerical `0.00428741`, analytical `0.00178351`
- Center sample particle count range inside `r <= 1dp`: `1` to `18`

## Conclusion

The completed formal run reproduces the main Mandel-Cryer response shape and the peak timing well. The numerical peak remains slightly lower than the analytical curve, and late-time dissipation is slightly slower, but the overall normalized center pore-pressure history is close over `T_v = 0.001..1.0`.

The strict `r <= 1dp` center sampling requested here can include a small and time-dependent number of particles, so minor local sampling noise is expected. The current completed server run used `SoilDampingCoef = 0.02`; a future full formal run with the later damping candidate may be useful if the early-time oscillation still needs to be reduced.
