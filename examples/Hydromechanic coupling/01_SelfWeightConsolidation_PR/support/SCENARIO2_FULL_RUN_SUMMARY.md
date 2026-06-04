# Scenario 2 Full-Length Run Summary

Case: `CaseSelfWeightConsolidation_Scenario2_Def.xml`

Run mode:

- CPU release solver
- `HydroMechInitMode=AnalyticalSelfWeight1D`
- `Gravity=(0, 0, -9.81)`
- `TimeMax=3.85 s`
- `TimeOut=0.02 s`
- `dt=1e-6 s`

Generated outputs:

- Solver output: `CaseSelfWeightConsolidation_Scenario2_out`
- Fluid VTK files: `CaseSelfWeightConsolidation_Scenario2_out/particles/PartFluid_0000.vtk` to `PartFluid_0192.vtk`
- Figure: `figures/self_weight_consolidation_profiles.png`
- Summary CSV: `figures/self_weight_consolidation_summary.csv`
- Target comparison CSV: `figures/self_weight_consolidation_targets.csv`
- Initial state CSV: `figures/self_weight_scenario2_initial_metrics.csv`
- Console log: `support/run_scenario2_full_stdout.log`

## Initial Analytical State

The initialized state matches the analytical 1D self-weight state:

| quantity | SPH | theory |
| --- | ---: | ---: |
| bottom excess pore pressure | 10.693858 kPa | 10.693858 kPa |
| bottom total pore pressure | 20.454809 kPa | 20.454808 kPa |
| bottom sigma_zz | -43.186741 Pa | -43.186735 Pa |

The initial state has `max_speed=0` and `max_kplastic=0`.

## Dissipation Result

The later Scenario 2 dissipation does not yet match the analytical trend.
The bottom excess pore pressure is over-dissipated and becomes negative,
whereas the analytical solution remains positive and decays toward zero
excess pressure, i.e. toward the hydrostatic total pore-pressure profile.

| target Tv | actual Tv | bottom excess SPH [kPa] | bottom excess theory [kPa] |
| ---: | ---: | ---: | ---: |
| 0.005 | 0.005489 | 10.382290 | 9.848097 |
| 0.05 | 0.049400 | 6.264429 | 8.051814 |
| 0.1 | 0.098800 | 4.376648 | 6.935438 |
| 0.25 | 0.252490 | 0.543158 | 4.675804 |
| 0.4 | 0.400690 | -1.798122 | 3.241421 |
| 0.5 | 0.499490 | -2.969932 | 2.540084 |
| 0.7 | 0.702580 | -4.518044 | 1.538932 |
| 1.0 | 0.998981 | -5.896623 | 0.740632 |

At the final output (`t=3.84 s`, `Tv=1.05387`), the bottom excess pore
pressure is `-5.90094 kPa`, while the analytical value is `0.646822 kPa`.

## Current Interpretation

The analytical initialization is correct, so the mismatch is introduced during
the transient PR evolution or boundary coupling rather than at `t=0`.
The most likely next checks are:

- PR seepage/diffusion sign and scaling for the maintained-gravity Scenario 2.
- Whether the water-head source term and the total-pressure Laplacian form
  make the hydrostatic gradient a true discrete steady state.
- Whether the drained free-surface enforcement or mDBC excess-pressure boundary
  correction removes too much pore pressure during long-time dissipation.
