# Cryer k=1e-5 peak-window dp convergence, 2026-06-22

## Scope

This run tested the one-stage drained Cryer configuration with:

- `HydroMechTopLoadMode=3` (`FlexibleConfinement`, global pair-wise mode);
- no load ramp: `HydroMechTopLoadRampTime=0`;
- drainage active from the start: `HydroMechDrainage=1`, `HydroMechDrainageStartTime=0`;
- `HydraulicConductivity=1e-5 m/s`;
- `SoilDampingCoef=0.02`;
- `PoreShepardRegularization=0`;
- `setfrdrawmode auto="true"`;
- fixed time step in the generated test XML: `DtFixed=5e-6 s`.

The physical time scale is:

- `T_v=1 -> 0.910928571429 s`;
- short peak-window runs used `T_v_max=0.1` and `Delta T_v=0.001`.

The `DtFixed=5e-6 s` setting was checked against the retained `dp=0.003`,
`DtFixed=1e-6 s`, `k=1e-5` run. The peak value and peak time were essentially
unchanged:

- old `DtFixed=1e-6`: peak `p/p0=1.20430` at `T_v=0.048`;
- current `DtFixed=5e-6`: peak `p/p0=1.20416` at `T_v=0.048`.

## Output locations

Run folders:

- `refinement/k1e5_convergence_20260622/dp003_tv010`
- `refinement/k1e5_convergence_20260622/dp0025_tv010`
- `refinement/k1e5_convergence_20260622/dp002_tv010`

Main figures and tables:

- `figures/cryer_k1e5_dp_convergence_20260622_peak_window.png`
- `figures/cryer_k1e5_dp_convergence_20260622_error_trend.png`
- `figures/cryer_k1e5_dp_convergence_20260622_peak_metrics.csv`
- `figures/cryer_k1e5_dp_convergence_20260622_peak_metrics.json`

Reusable runner:

- `support/run_k1e5_convergence_20260622.py`

## Results

| dp | Fluid particles | Runtime | Peak p/p0 | Peak Tv | Analytical peak p/p0 | RMSE, 0<Tv<=0.1 | Peak deficit at analytical peak Tv | Max speed |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.0030 | 22483 | 1465.5 s | 1.204159 | 0.048 | 1.249008 | 0.036963 | -0.045038 | 0.058033 |
| 0.0025 | 37173 | 3283.6 s | 1.214782 | 0.049 | 1.249008 | 0.029772 | -0.034996 | 0.039921 |
| 0.0020 | 71170 | 9769.8 s | 1.221718 | 0.049 | 1.249008 | 0.026528 | -0.028015 | 0.021253 |

## Interpretation

The convergence trend is physically encouraging:

- the peak pore pressure increases monotonically with resolution;
- the peak-window RMSE decreases monotonically;
- the maximum velocity decreases strongly with refinement;
- the numerical peak remains near `T_v=0.048-0.049`, close to the analytical
  peak location around `T_v=0.046`.

However, the `dp=0.002` peak is still about `0.0273 p0` below the analytical
peak, or about `2.2%` of `p0`. This is an improvement, but it is not yet a
fully converged match to the analytical Cryer peak.

## Full-run decision

The requested full `dp=0.002`, `T_v=1` run was not launched in this pass.

Reason:

- the short `dp=0.002`, `T_v=0.1` run took `9769.8 s`;
- a direct `T_v=1` run with the same time step would be roughly ten times
  longer, about `27 h`, before PartVTK/postprocessing;
- the peak-window result is improved but still underpredicts the analytical
  peak by about `2.2%`, so the condition "peak has converged close to theory"
  is not yet fully satisfied.

Recommended next step before any full `T_v=1` production run:

- run one additional short case at `dp=0.00175` or improve the center sampling
  strategy for `dp=0.002`;
- if the peak rises further toward `1.249 p0`, then launch the two-output-scale
  full run:
  - early run: `Delta T_v=1e-4`, `T_v_max=0.01`;
  - full run: `Delta T_v=1e-2`, `T_v_max=1`.
