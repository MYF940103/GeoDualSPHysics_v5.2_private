# Self-weight Stage 1 baseline conclusion, 2026-06-27

## Baseline retained

The current best Stage 1 baseline is:

- Case: `CaseSWStage1_d02_D_SH40_FS`
- XML: `tests/configs/CaseSWStage1_d02_D_SH40_FS_Def.xml`
- Output: `tests/outputs/CaseSWStage1_d02_D_SH40_FS_out`
- Figures and summary: `tests/figures/CaseSWStage1_d02_D_SH40_FS`
- Key settings: `HydroMechInitMode=1`, `HydroMechDrainage=1`, `HydroMechDrainageStartTime=0`, `PoreShepardRegularization=1`, `PoreShepardInterval=40`, `SoilDampingCoef=0.02`, `HydraulicConductivity=0`, `TimeMax=0.40`, `TimeOut=0.005`.

Runtime checks from `Run.out`:

- `HydroMechInitMode="FreeSurface"`
- `HydroMechDrainage="Enabled"`
- `PoreShepardRegularization="Enabled"`
- `PoreShepardInterval: 40`
- `SoilDampingCoef=0.02`
- Initial pore pressure assigned to 1872 particles with `FreeSurface`, min `0`, max `10104.3` Pa.
- Final part: `Part_0080`, time `0.400000` s.
- Excluded particles: `0`.
- Finished execution with code `0`.

## Quantitative result

Final profile metrics at `t=0.40 s`:

- Bottom total pore pressure: `20.043532 kPa`
- Bottom theoretical total pore pressure: `20.4156825 kPa`
- Bottom error: `-0.3721505 kPa`
- RMS total pore pressure error: `0.0849309308 kPa`
- High-frequency pore pressure residual RMS: `0.0029066631 kPa`
- Maximum speed: `1.97670309e-05 m/s`
- Maximum plastic flag: `0`

Compared with the previous `HydroMechInitMode=0 + drainage=1 + Shepard40` group, the `FreeSurface` baseline reduced the bottom total pore-pressure error from about `-0.859 kPa` to `-0.372 kPa`, and reduced the final RMS error from about `0.140 kPa` to `0.085 kPa`.

## Interpretation

`HydroMechInitMode=1` is important here because it initializes the hydrostatic pore-pressure reference consistently for both fluid and nearby mDBC boundary particles. This fixes the earlier bottom-boundary underestimation caused by using a zero reference pore pressure with the mDBC pore-pressure interpolation path.

Opening drainage from the start keeps the free surface pinned to the intended drained condition and prevents the Shepard step from pulling the free-surface pore pressure upward. Shepard interval 40 is kept because it suppresses high-frequency pore-pressure oscillation without visibly distorting the stable final profile in this short Stage 1 test.

The formal Stage 1 configuration in the example root has been synchronized to this baseline. Non-baseline test outputs were removed after recording the conclusion to avoid confusing later checks.

## Restart time selection

For choosing the restart time for the next stage, `t=0.30 s` is preferred over `t=0.40 s`.

| time (s) | bottom total pore error (kPa) | profile RMS error (kPa) | HF residual RMS (kPa) | max speed (m/s) |
| --- | ---: | ---: | ---: | ---: |
| 0.25 | -0.280388 | 0.068906 | 0.003000 | 5.38376189e-05 |
| 0.30 | -0.302219 | 0.079473 | 0.002976 | 1.45961038e-05 |
| 0.35 | -0.336792 | 0.082657 | 0.002941 | 1.78782174e-05 |
| 0.40 | -0.372150 | 0.084931 | 0.002907 | 1.97670309e-05 |

The 0.30 s state is the best balance: the velocity residual is at a local minimum, while the pore-pressure profile is still closer to the undrained theoretical profile than at 0.40 s. The 0.40 s state slightly reduces the high-frequency residual, but the improvement is very small and is outweighed by the continued downward drift of the total pore pressure profile. The 0.25 s state has a smaller pressure error but still carries a much larger velocity residual, so it is less suitable as a restart state.

The profile change from 0.30 s to 0.40 s is small in absolute terms, with RMS change about `0.01625 kPa` and maximum layer change about `0.06993 kPa`; therefore the difference is not expected to dominate the later consolidation result. Still, for restart cleanliness, 0.30 s should be used as the Stage 1 handoff time unless later tests show a sensitivity to this choice.

The formal root Stage 1 XML and bat now stop at `0.30 s`, so the formal restart handoff is `Part_0060`.
