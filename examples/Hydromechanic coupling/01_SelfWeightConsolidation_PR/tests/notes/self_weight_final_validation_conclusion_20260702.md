# Self-weight consolidation final validation conclusion

Date: 2026-07-02

## Accepted validation setup

The accepted setup for `01_SelfWeightConsolidation_PR` is the two-stage Scenario 2 workflow:

1. Stage 1 undrained self-weight initialization:
   - `HydraulicConductivity = 0`
   - `HydroMechInitMode = 1` (`FreeSurface`)
   - `HydroMechDrainage = 1`
   - `PoreShepardRegularization = 1`
   - `PoreShepardInterval = 40`
   - `SoilDampingCoef = 0.02`
   - fixed `dt = 1e-6`
   - restart state: `Part_0060`, corresponding to 0.30 s

2. Scenario 2 drained consolidation:
   - restart from Stage 1 `Part_0060`
   - inherit `Sigma`, `PorePress`, and `PorePress0`
   - `HydraulicConductivity = 1e-3`
   - `HydroMechInitMode = 0`
   - `HydroMechDrainage = 1`
   - `PoreShepardRegularization = 0`
   - `SoilDampingCoef = 0.02`
   - fixed `dt = 1e-6`
   - output interval: `TimeOut = 0.0182185714 s`, equivalent to `Delta Tv = 0.005`
   - final time: `TimeMax = 3.85 s`, approximately `Tv = 1`

## Preserved test data

The retained validation outputs are:

- Stage 1 output:
  `tests/outputs/CaseSWStage1_TwoStage_Damp002_DrainShep40_t040_GPU_out`
- Scenario 2 output:
  `tests/outputs/CaseSWScenario2_TwoStage_Damp002_DTv0005_from_p0060_GPU_out`
- Stage 1 figures:
  `tests/figures/CaseSWStage1_TwoStage_Damp002_DrainShep40_t040_GPU`
- Scenario 2 figures:
  `tests/figures/CaseSWScenario2_TwoStage_Damp002_DTv0005_from_p0060_GPU`
- Stage 1 config:
  `tests/configs/CaseSWStage1_TwoStage_Damp002_DrainShep40_t040_Def.xml`
- Scenario 2 config:
  `tests/configs/CaseSWScenario2_TwoStage_Damp002_DTv0005_Def.xml`

Other Mode 3 replay, fixed-dt diagnostic, damping sweep, GPU reproducibility rerun, and mixed-damping outputs were removed from `tests` after their conclusions were recorded.

## Main result

The accepted `0.02/0.02` two-stage run completed with:

- `DTs adjusted to DtMin = 0`
- `Excluded particles = 0`
- `Steps of simulation = 3850000`
- `PART files = 212`
- restart data confirmed in runtime log:
  - `Sigma inherited`
  - `PorePress and PorePress0 inherited`

Representative Scenario 2 target comparisons:

| Tv | Bottom SPH (kPa) | Theory (kPa) | RMS profile error (Pa) |
| --- | ---: | ---: | ---: |
| 0.000 | 10.4017 | 10.6964 | 98.573 |
| 0.005 | 9.86395 | 9.88899 | 70.089 |
| 0.050 | 8.05135 | 8.03550 | 30.736 |
| 0.100 | 6.94800 | 6.91237 | 32.510 |
| 0.250 | 4.76348 | 4.70479 | 43.603 |
| 0.400 | 3.32519 | 3.24695 | 55.464 |
| 0.500 | 2.62346 | 2.53689 | 61.424 |
| 0.700 | 1.69277 | 1.54876 | 85.764 |
| 1.000 | 0.84620 | 0.73877 | 73.623 |

This setup removes the large startup overshoot from the direct `HydroMechInitMode=3` initialization and avoids the late-time plateau observed before the fixed-time-step semantics were corrected.

## Damping checks

The following alternatives were tested and rejected as final defaults:

- `Stage1=0.01, Stage2=0.01`: slightly improves the very late-time RMS by only a few Pa, but Stage 1 is less stable and early/mid-time profiles are worse.
- `Stage1=0.02, Stage2=0.01`: keeps the accepted initial state but worsens `Tv=0.005-0.25`; late-time improvement is only about 1-3 Pa.

Therefore the final recommended damping combination is:

- Stage 1: `SoilDampingCoef = 0.02`
- Stage 2: `SoilDampingCoef = 0.02`

## Release file update

The root release XML/BAT files should reflect the accepted setup:

- `CaseSelfWeightConsolidation_Stage1_Def.xml`
- `CaseSelfWeightConsolidation_Scenario2_Def.xml`
- `xCaseSelfWeightConsolidation_Stage1_win64_CPU.bat`
- `xCaseSelfWeightConsolidation_Scenario2_win64_CPU.bat`
- `xCaseSelfWeightConsolidation_win64_CPU.bat`

The BAT files should export pure boundary VTKs with `-onlytype:-all,bound`.

After cleanup, `tests/outputs`, `tests/figures`, and `tests/configs` retain only the accepted `0.02/0.02` Stage 1 and Scenario 2 validation set. A temporary GenCase parse check of the root Stage 1 and Scenario 2 XML files passed after the release-file update.
