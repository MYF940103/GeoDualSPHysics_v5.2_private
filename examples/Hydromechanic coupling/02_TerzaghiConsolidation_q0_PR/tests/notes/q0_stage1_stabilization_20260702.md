# q0 k=1e-2 Stage1 stabilization test

Date: 2026-07-02

## Purpose

Test a two-stage q0 Terzaghi workflow for the fast `k=1e-2` case:

- Stage1: apply the q0 load under undrained conditions and let the dynamic response settle.
- Stage2: restart from a stabilized Stage1 state and start the formal dissipation calculation.

This follows the same general strategy used in `01_SelfWeightConsolidation_PR`.

## Stage1 setup

Derived from `CaseTerzaghiConsolidation_q0_PR_full_k1em2_Def.xml`.

- `HydraulicConductivity=0`
- `HydroMechTopLoadMode=TopVertical`
- `HydroMechTopLoadRampTime=0`
- `HydroMechDrainage=1`
- `HydroMechDrainageStartTime=0`
- `PoreShepardRegularization=1`
- `PoreShepardInterval=40`
- `TimeOut=0.0005 s`

## Results

| case | TimeMax | DtFixed | final mean excess | bottom excess | inner RMS vs 10 kPa | max speed | particles |
|---|---:|---:|---:|---:|---:|---:|---:|
| `stage1_dt1em6` | 0.01 s | 1e-6 s | 15.2496 kPa | 19.3995 kPa | 6.6779 kPa | 0.0125566 m/s | 1000 |
| `stage1_dt1em7` | 0.01 s | 1e-7 s | 14.5220 kPa | 17.7928 kPa | 5.4970 kPa | 0.0188070 m/s | 1000 |
| `stage1_dt1em7_t006` | 0.06 s | 1e-7 s | 10.1207 kPa | 11.1616 kPa | 1.6156 kPa | 0.00317395 m/s | 1000 |
| `stage1_dt1em7_t010` | 0.10 s | 1e-7 s | 8.9367 kPa | 9.5640 kPa | 1.7702 kPa | 0.00133593 m/s | 1000 |
| `stage1_d04t010` | 0.10 s | 1e-7 s | 9.0110 kPa | 9.7676 kPa | 1.7605 kPa | 0.00145771 m/s | 1000 |
| `stage1_dt1em7_t015` | 0.15 s absolute, restart from 0.10 s | 1e-7 s | 9.0050 kPa | 9.9376 kPa | 1.9913 kPa | 0.00119192 m/s | 1000 |

All runs completed without particle exclusion.

## Interpretation

The `0.01 s` Stage1 duration is too short. Reducing `DtFixed` from `1e-6 s` to `1e-7 s` improves the pressure profile slightly, but the velocity peak remains large and the pressure field is still too high relative to the intended undrained `q0=10 kPa` state.

Extending Stage1 to `0.06 s` at `DtFixed=1e-7 s` gives a much better candidate restart state:

- Mean excess pore pressure is close to `10 kPa`.
- Inner-column RMS error drops to about `1.62 kPa`.
- Maximum velocity drops to about `3.17e-3 m/s`.
- Particle count remains 1000.

Extending further to `0.10 s` reduces the velocity peak to about `1.34e-3 m/s`, but the pressure field is still oscillating around the intended `10 kPa` undrained state. At the final `0.10 s` snapshot, the oscillation phase is on the low-pressure side: mean excess pressure is about `8.94 kPa`, bottom excess pressure is about `9.56 kPa`, and the inner RMS is slightly worse than the `0.06 s` endpoint. The better Stage2 restart may therefore be a low-velocity snapshot selected from the late-time window, not necessarily the final snapshot.

Increasing `SoilDampingCoef` from `0.02` to `0.4` for a `0.10 s` Stage1 run did not improve the restart state. The final pressure metrics are only marginally different from the `0.02` case, and the final maximum speed is slightly higher (`1.46e-3 m/s` vs `1.34e-3 m/s`). The high-damping run also moves monotonically toward a low-pressure profile after the early transient, so it is not a better way to obtain a low-velocity, near-`10 kPa` initial state.

Continuing the `0.02` case from `0.10 s` to an absolute `0.15 s` further reduces the final maximum speed to about `1.19e-3 m/s`, but the pressure profile continues to drift low: final mean excess pressure is about `9.00 kPa` and inner RMS rises to about `1.99 kPa`. In the `0.10-0.15 s` continuation window, the lowest-speed snapshots have mean excess pressure around `9.05-9.24 kPa`; no snapshot with mean excess pressure within `0.3 kPa` of the `10 kPa` target was found.

Implementation note: the `0.15 s` case uses `-partbegin:200:0` from `stage1_dt1em7_t010` and sets XML `TimeMax=0.05 s`, because restart runs count `PartTime` from zero after loading the inherited state. The postprocess script applies a `0.10 s` time offset so CSV and plots report the absolute Stage1 time.

Late-window candidate snapshots from `stage1_dt1em7_t010`:

- `Part_0138` (`t=0.069 s`): mean excess `9.9809 kPa`, bottom excess `11.0097 kPa`, inner RMS `1.6347 kPa`, max speed `9.6858e-4 m/s`.
- `Part_0124` (`t=0.062 s`): mean excess `10.0733 kPa`, bottom excess `11.1053 kPa`, inner RMS `1.6113 kPa`, max speed `1.0266e-3 m/s`.
- `Part_0151` (`t=0.0755 s`): mean excess `9.9880 kPa`, bottom excess `11.0668 kPa`, inner RMS `1.6965 kPa`, max speed `1.5454e-3 m/s`.

## Files

- Config: `tests/configs/CaseTerzaghiConsolidation_q0_PR_stage1_dt1em7_t006_Def.xml`
- Output: `tests/outputs/CaseTerzaghiConsolidation_q0_PR_stage1_dt1em7_t006_out`
- Summary: `tests/figures/CaseTerzaghiConsolidation_q0_PR_stage1_dt1em7_t006/CaseTerzaghiConsolidation_q0_PR_stage1_dt1em7_t006_summary.txt`
- Metrics: `tests/figures/CaseTerzaghiConsolidation_q0_PR_stage1_dt1em7_t006/CaseTerzaghiConsolidation_q0_PR_stage1_dt1em7_t006_stage1_metrics.csv`
- Final profile: `tests/figures/CaseTerzaghiConsolidation_q0_PR_stage1_dt1em7_t006/CaseTerzaghiConsolidation_q0_PR_stage1_dt1em7_t006_final_profile.png`
- History plot: `tests/figures/CaseTerzaghiConsolidation_q0_PR_stage1_dt1em7_t006/CaseTerzaghiConsolidation_q0_PR_stage1_dt1em7_t006_history.png`
- Extended 0.10 s config: `tests/configs/CaseTerzaghiConsolidation_q0_PR_stage1_dt1em7_t010_Def.xml`
- Extended 0.10 s output: `tests/outputs/CaseTerzaghiConsolidation_q0_PR_stage1_dt1em7_t010_out`
- Extended 0.10 s metrics: `tests/figures/CaseTerzaghiConsolidation_q0_PR_stage1_dt1em7_t010/CaseTerzaghiConsolidation_q0_PR_stage1_dt1em7_t010_stage1_metrics.csv`
- High-damping 0.10 s metrics: `tests/figures/CaseTerzaghiConsolidation_q0_PR_stage1_d04t010/CaseTerzaghiConsolidation_q0_PR_stage1_d04t010_stage1_metrics.csv`
- Restarted 0.15 s metrics: `tests/figures/CaseTerzaghiConsolidation_q0_PR_stage1_dt1em7_t015/CaseTerzaghiConsolidation_q0_PR_stage1_dt1em7_t015_stage1_metrics.csv`

## Next step

Use `Part_0120` from `stage1_dt1em7_t006` as the first Stage2 restart candidate, then enable `HydraulicConductivity=1e-2` and measure dissipation time from the restart state. Also test `Part_0138` from `stage1_dt1em7_t010`; it currently has the best balance of low velocity and mean excess pressure close to `10 kPa`. Avoid using the final `Part_0200` from `stage1_dt1em7_t010`, the high-damping final state, or the `0.15 s` final state as the default restart because their pressure fields are on the low side of the oscillation.
