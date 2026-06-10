# q0 Terzaghi Consolidation Verification Notes

Date: 2026-06-09

## Formal configurations kept

- `k=1e-2`: `CaseTerzaghiConsolidation_q0_PR_full_k1em2_Def.xml`
  - `tL = 0.0001 s`
  - `HydroMechFreeSurfaceDrainageStartTime = 0.0001 s`
  - `DtFixed = 1e-7 s`
- `k=1e-3`: `CaseTerzaghiConsolidation_q0_PR_full_k1em3_Def.xml`
  - `tL = 0.01 s`
  - `HydroMechFreeSurfaceDrainageStartTime = 0.01 s`
  - `DtFixed = 1e-6 s`
- `k=1e-4`: `CaseTerzaghiConsolidation_q0_PR_full_k1em4_Def.xml`
  - `tL = 0.01 s`
  - `HydroMechFreeSurfaceDrainageStartTime = 0.01 s`
  - `DtFixed = 1e-5 s`

## Latest full-validation metrics

| k | Final Tv | Final U num | Final U theory | U RMSE | Settlement mm | Max speed |
|---|---:|---:|---:|---:|---:|---:|
| 1e-2 | 0.9997 | 0.92067 | 0.93121 | 0.03665 | 3.572 | 1.867e-1 |
| 1e-3 | 1.0023 | 0.92785 | 0.93164 | 0.00492 | 3.613 | 2.046e-2 |
| 1e-4 | 0.9997 | 0.93090 | 0.93121 | 0.00191 | 3.695 | 2.489e-3 |

## Ramp sweep conclusions

- `k=1e-3`: The physical-time ramp sweep showed that `tL=0.01 s` is the best tested value. It removed the early `Tv≈0.005` transient mismatch and reduced the full-run `U_RMSE` to about `0.00492`.
- `k=1e-2`: Among the tested values (`0.001`, `0.003`, `0.005`, `0.01 s`), `tL=0.001 s` was the best short-run option, but the early `Tv≈0.005` error remained large. This case is not fixed by ramp duration alone; the next useful checks are damping/load-application strategy and possibly diffusion/time-step sensitivity.
- `k=1e-4`: The existing `tL=0.01 s` remains the best validated configuration and gives the most accurate full-run result.

## Ideal initial excess pressure check

- A temporary `k=1e-2` ideal-initial check was run, then removed to keep the code and case directory clean.
- The temporary run confirmed that the ideal initial field itself can be assigned correctly: at `Part_0000`, mean excess pressure was about `9.9 kPa`, bottom excess pressure was `10 kPa`, and the top free surface was drained.
- At the first output (`Tv~0.005`), the ideal-initial run still showed a strong transient drop (`U~0.640`, bottom excess `~2.78 kPa`), then recovered close to the dynamic-ramp run by `Tv~0.05`.
- Conclusion: the earliest `k=1e-2` mismatch is not caused by failure to initialize/generate q0 excess pore pressure alone. It is mainly triggered during the first coupled dynamic steps after the load/boundary state is applied.

## Drainage-delay sweep check

- Temporary short-run `k=1e-2` drainage-delay cases were generated with `tL=0.001 s`, `DtFixed=1e-7 s`, and `tD=0.001`, `0.005`, `0.02 s`.
- The invalid `DtFixed=1e-6 s` trial was discarded because it caused particle exclusion before a meaningful comparison.
- For delayed drainage, the pre-drainage field was healthy: `tD=0.005 s` gave mean/top/bottom excess pressure about `10.75/10.38/11.11 kPa`; `tD=0.02 s` gave about `10.07/10.19/10.01 kPa`, with very small residual velocity at `tD=0.02 s`.
- Once drainage was opened, the earliest response still over-dissipated strongly. At `Tv~0.005` measured from `tD`, numerical `U` was about `0.48` for `tD=0.001 s`, `0.60` for `tD=0.005 s`, and `0.59` for `tD=0.02 s`, while Terzaghi theory is about `0.084`.
- By `Tv~0.05` and `Tv~0.1`, the three drainage-delay runs converged back close to the same branch as the original dynamic case, with `U~0.27` and `U~0.37` respectively.
- Conclusion: delaying free-surface drainage confirms that the code can maintain a good near-10 kPa pre-drainage excess pressure field, but it does not fix the earliest `k=1e-2` mismatch. The dominant issue is the first few coupled dynamic steps after drainage activation, not the ramp field or PR diffusion alone.
- The temporary drainage-delay XML/BAT/output/figure/script files were removed after recording this conclusion.

## Time-step sensitivity check

- A short `k=1e-2` run was generated from the formal `full_k1em2` case with `DtFixed=5e-8 s`, `tL=tD=0.0001 s`, `TimeMax=0.0183185714285714 s` (`Tv~0.05`), and `TimeOut=0.00025 s`.
- Compared with the formal `DtFixed=1e-7 s` run:
  - At `Tv~0.005`, `U` improved only from about `0.5585` to `0.5024`; theory is about `0.08`.
  - Bottom excess pore pressure increased only from about `4.06 kPa` to `4.71 kPa`, still far from the expected near-10 kPa early profile.
  - Profile RMS reduced from about `5.12 kPa` to `4.54 kPa`, but the early mismatch remains large.
  - `max_speed` did not decrease (`0.187` to `0.201 m/s`), so the early dynamic transient was not suppressed by halving the time step.
  - At `Tv~0.02` and `Tv~0.05`, the `5e-8` and `1e-7` results are essentially identical.
- Conclusion: `DtFixed=1e-7 s` is already close to time-step convergence for this early-transient behavior. Smaller `dt` slightly smooths/improves the first sampled point but does not solve the `k=1e-2` over-dissipation mechanism.
- Generated comparison files:
  - `figures/dt_sensitivity_k1em2/dt5em8_vs_dt1em7_summary.csv`
  - `figures/dt_sensitivity_k1em2/dt5em8_vs_dt1em7_profiles.png`

## Pore Shepard regularization check

- A short `k=1e-2` run was generated from the formal `full_k1em2` case with `PoreShepardRegularization=1`, `PoreShepardInterval=30`, `DtFixed=1e-7 s`, `tL=tD=0.0001 s`, `TimeMax=0.0183185714285714 s`, and `TimeOut=0.00025 s`.
- The run completed normally with `Excluded particles = 0`.
- At `Tv~0.005`, Shepard regularization reduced `U` from the baseline nearest-output value of about `0.5585` to about `0.5088`, and profile RMS from about `5.12 kPa` to about `4.60 kPa`; however, theory is still only about `0.08`, so the early over-dissipation remains severe.
- At the same early output time, the `DtFixed=5e-8 s` no-Shepard run was slightly better (`U~0.5024`, RMS `~4.54 kPa`) than the `DtFixed=1e-7 s` Shepard run.
- At `Tv~0.02` and `Tv~0.05`, the Shepard result is essentially on the same branch as the no-Shepard runs, with a slightly larger RMS at `Tv~0.05`.
- Conclusion: pore-pressure Shepard regularization slightly smooths the first sampled early point, but it does not solve the `k=1e-2` early transient. It should not be treated as the fix for this verification mismatch.
- Generated comparison files:
  - `figures/pore_shepard_k1em2/pore_shepard_k1em2_summary.csv`
  - `figures/pore_shepard_k1em2/pore_shepard_k1em2_profiles.png`

## Artificial viscosity sweep check

- Short `k=1e-2` runs were generated from the formal `full_k1em2` case with `Visco=0.2`, `0.5`, and `1.0`, keeping `DtFixed=1e-7 s`, `tL=tD=0.0001 s`, `TimeMax=0.0183185714285714 s`, and the formal baseline `TimeOut=0.00182185714285714 s`.
- All three runs completed normally with `Excluded particles = 0`.
- Increasing artificial viscosity reduces velocity amplitudes: at `Tv~0.005`, `max_speed` decreased from about `0.187 m/s` at `alpha=0.1` to about `0.126 m/s` at `alpha=1.0`.
- The early excess-pressure error barely improved. At `Tv~0.005`, `U` changed only from about `0.5585` (`alpha=0.1`) to about `0.5509` (`alpha=1.0`), while Terzaghi theory is about `0.0776`. Bottom excess pore pressure rose only from about `4.06 kPa` to about `4.24 kPa`.
- At `Tv~0.02`, RMS improves mildly with larger viscosity (`0.588 kPa` to `0.556 kPa`), but at `Tv~0.05` it slightly worsens (`0.330 kPa` to `0.336 kPa`).
- Conclusion: artificial viscosity damps particle velocity but does not materially fix the `k=1e-2` early over-dissipation. The mismatch is not primarily a velocity-noise artifact that can be removed by increasing Monaghan artificial viscosity.
- Generated comparison files:
  - `figures/visco_sweep_k1em2/visco_sweep_k1em2_summary.csv`
  - `figures/visco_sweep_k1em2/visco_sweep_k1em2_profiles.png`

## Files kept after cleanup

- Formal XML/bat files for the three full cases.
- Formal output directories:
  - `CaseTerzaghiConsolidation_q0_PR_full_k1em2_out`
  - `CaseTerzaghiConsolidation_q0_PR_full_k1em3_out`
  - `CaseTerzaghiConsolidation_q0_PR_full_k1em4_out`
- Formal figures/CSV:
  - `figures/full_validation_q0_history.png`
  - `figures/full_validation_q0_profiles_k1em2.png`
  - `figures/full_validation_q0_profiles_k1em3.png`
  - `figures/full_validation_q0_profiles_k1em4.png`
  - `figures/full_validation_q0_summary.csv`
  - `figures/full_validation_q0_targets.csv`
