# SelfWeight Mode3 mDBC pore-pressure scheduling isolation

Date: 2026-06-30 to 2026-07-01

Case: `CaseSWScenario2_Mode3_MdbcPwLegacy_GPU`

Temporary source change tested:

- Restored `InteractionPorePressureMdbcCorrection()` inside `ApplyPorePressureBoundaries()`.
- Disabled pore-pressure array updates inside `MdbcBoundCorrection()` by passing `NULL,NULL`.
- Kept the merged pore-pressure-rate pair-loop unchanged.

Run settings:

- GPU Release executable: `DualSPHysics5.2_GEO_win64.exe`
- `HydroMechInitMode=3` (`AnalyticalSelfWeight1D`)
- `PoreShepardRegularization=0`
- `DtFixed=1e-6`
- `TimeMax=3.85`
- `TimeOut=0.0182185714` (`Delta Tv=0.005`)
- `SlipMode=1`
- `SoilDampingCoef=4e-5`

Result:

- Initial analytical effective stress was correctly initialized after the buoyant self-weight fix: `sigma_zz min=-43.1867 Pa`, `max=-0.217019 Pa`.
- The legacy-scheduling isolation did **not** reproduce the old CPU baseline.
- It was much worse than the current path: bottom excess pore pressure stayed nearly locked at about `10.55 kPa` through `Tv=1`.
- Comparison against old CPU baseline:
  - Bottom dissipation max absolute difference: `9.85507 kPa`
  - Bottom dissipation RMS difference: `7.70279 kPa`
  - Target-point max absolute bottom difference: `9.75458 kPa`
  - Target-point max absolute profile RMS difference: `5555.83 Pa`

Files:

- Output: `tests/outputs/CaseSWScenario2_Mode3_MdbcPwLegacy_GPU_out`
- Profile figure: `tests/figures/CaseSWScenario2_Mode3_MdbcPwLegacy_GPU/scenario2_pore_pressure_profiles.png`
- Old CPU comparison figure: `tests/figures/CaseSWScenario2_Mode3_MdbcPwLegacy_GPU_vs_old_cpu/mode3_gpu_vs_old_cpu_bottom_compare.png`
- Comparison CSVs: `tests/figures/CaseSWScenario2_Mode3_MdbcPwLegacy_GPU_vs_old_cpu/`

Conclusion:

- The mDBC pore-pressure scheduling change alone is **not** the reason current results differ from the old CPU baseline.
- The temporary code change was reverted after the test; current source returns to the newer path where pore pressure is passed through `MdbcBoundCorrection()`.
- Do **not** start the two-stage Stage1/Stage2 workflow based on this isolation run, because the prerequisite "Mode3 direct initial state matches old CPU baseline" was not met.
- The next suspect is the other major path change: pore-pressure-rate computation was merged into the main pair-loop. A controlled test should keep the current mDBC pore-pressure update path and temporarily restore the standalone `InteractionPorePressureRate()` call after `Interaction_Forces_ct()`.
