# Self-weight Scenario 2 Mode3 old-input replay conclusion (2026-06-30)

## Purpose

The old CPU baseline in `CaseSelfWeightConsolidation_Scenario2_out` was compared against the current CPU/GPU executables for Scenario 2 with `HydroMechInitMode=3` (`AnalyticalSelfWeight1D`).

The key question was whether the late-time difference was caused by GPU/CPU differences, test XML differences, or later code changes.

## Runs compared

1. Current GPU Mode3 test:
   - Output: `tests/outputs/CaseSWScenario2_Mode3_GPU_out`
   - Figures: `tests/figures/CaseSWScenario2_Mode3_GPU`

2. Current CPU Mode3 test generated from the current test XML:
   - Output: `tests/outputs/CaseSWScenario2_Mode3_CPU_out`
   - Figures: `tests/figures/CaseSWScenario2_Mode3_CPU`

3. Current CPU executable replay using the archived June 4 generated input:
   - Input: `CaseSelfWeightConsolidation_Scenario2_out/CaseSelfWeightConsolidation_Scenario2.xml` and `.bi4`
   - Output: `tests/outputs/CaseSWScenario2_Mode3_OldGeneratedXML_CPU_out`
   - Figures: `tests/figures/CaseSWScenario2_Mode3_OldGeneratedXML_CPU`

4. Old CPU baseline:
   - Output: `CaseSelfWeightConsolidation_Scenario2_out`
   - Figures: `figures/self_weight_consolidation_profiles.png`

## Quantitative comparison

Current CPU and current GPU match:

- Summary: `tests/figures/mode3_current_cpu_vs_gpu_compare/mode3_gpu_vs_cpu_summary.csv`
- Status: `MATCH`
- Maximum bottom-pressure difference: `0.002632 kPa`
- Maximum target bottom-pressure difference: `0.001387 kPa`

Current CPU differs from old CPU:

- Summary: `tests/figures/mode3_current_cpu_vs_old_cpu_compare/mode3_gpu_vs_cpu_summary.csv`
- Status: `DIFFERENT`
- Maximum bottom-pressure difference: `0.336422 kPa`
- Maximum target bottom-pressure difference: `0.238921 kPa`

Current CPU using the old generated XML/BI4 still differs from old CPU:

- Summary: `tests/figures/mode3_oldgenerated_current_cpu_vs_old_cpu_compare/mode3_gpu_vs_cpu_summary.csv`
- Status: `DIFFERENT`
- Maximum bottom-pressure difference: `0.336422 kPa`
- Maximum target bottom-pressure difference: `0.238921 kPa`
- At `Tv=1.0`, old CPU bottom excess pressure is about `0.794671 kPa`, while current CPU using the archived input is about `1.033592 kPa`.

## Runtime evidence

The archived old baseline run reported:

- `CteB=1165428`
- `Cs0=35.80574417114258`
- `Hydromechanics: initial pore pressure ... max=20552.9`
- `Hydromechanics: analytical 1D self-weight effective stress initialized (sigma_zz min=-43.1867, max=-0.217019)`
- No explicit `HydroMechDrainage` line was printed in the old `Run.out`.

The current CPU replay of the exact archived XML/BI4 reported:

- `XmlFile=".../CaseSelfWeightConsolidation_Scenario2_out/CaseSelfWeightConsolidation_Scenario2.xml"`
- `*** WARNING: Hydromechanics options are still defined inside <soils>; move them to <special><hydromechanics>.`
- `HydroMechDrainage="Enabled"`
- `CteB=384615.4`
- `Cs0=35.80574408560461`
- `Hydromechanics: initial pore pressure ... max=20513.6`
- `Hydromechanics: analytical 1D self-weight mode=gravity-on self-weight, reference gravity=9.81, hydrostatic baseline=retained.`
- `Hydromechanics: analytical 1D self-weight effective stress initialized (sigma_zz min=-82.4474, max=-0.414309)`

## Conclusion

The discrepancy is not caused by GPU arithmetic or by the current test XML/GenCase setup. Even when the current CPU executable reads the archived June 4 generated XML/BI4 input, it follows the current result instead of reproducing the old CPU baseline.

Therefore, the difference comes from later code-side behavior changes in the runtime interpretation/initialization path, especially:

1. The equation-of-state constant reported as `CteB` changed from `1165428` to `384615.4` while `Cs0` stayed about `35.8057`.
2. `AnalyticalSelfWeight1D` effective-stress initialization changed substantially: bottom `sigma_zz` went from about `-43.19 Pa` to about `-82.45 Pa`.
3. Legacy hydromechanics options under `<soils>` are now mapped with an explicit drainage default (`HydroMechDrainage="Enabled"`), whereas the old run did not print this option.

The next diagnostic should focus on the source paths that read hydromechanics options, compute/report `CteB`, and initialize `AnalyticalSelfWeight1D` pore pressure/effective stress. The old baseline can only be reproduced if those runtime behaviors are restored or deliberately compatibility-gated.
