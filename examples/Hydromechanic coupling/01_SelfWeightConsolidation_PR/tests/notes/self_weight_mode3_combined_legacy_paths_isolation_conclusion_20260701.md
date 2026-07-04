# Combined legacy CPU path isolation conclusion

Case: `CaseSWScenario2_Mode3_CombinedLegacyPaths_CPU`

Purpose: test whether the old CPU baseline can be reproduced by restoring both legacy CPU paths together:

- separate mDBC pore-pressure extrapolation via `InteractionPorePressureMdbcCorrection()`;
- standalone pore-pressure-rate evaluation via `InteractionPorePressureRate()`;
- all case parameters otherwise unchanged from the direct `HydroMechInitMode=3` Scenario 2 control.

Result:

- The run completed without excluded particles.
- The comparison against the old CPU baseline still reports `DIFFERENT`.
- Bottom-dissipation maximum absolute difference: about `0.3340 kPa`.
- Bottom-dissipation RMS difference: about `0.0931 kPa`.
- At `Tv=1.0`, current bottom excess pore pressure is about `1.0312 kPa`, while the old CPU baseline is about `0.7947 kPa`.
- The target-point values are essentially the same as the standalone pore-pressure-rate isolation, so combining the old mDBC scheduling with standalone pore-rate does not restore the old CPU curve.

Decision:

- Do not start the two-stage `HydroMechInitMode=3` workflow yet.
- The mismatch is not explained by mDBC pore-pressure scheduling, pore-pressure-rate loop merging, XML compatibility, or the free-surface drainage predicate.
- The next cause to inspect should be another source-side difference affecting the direct analytical self-weight path or subsequent effective-stress/pore-pressure coupling.

Artifacts kept:

- `tests/outputs/CaseSWScenario2_Mode3_CombinedLegacyPaths_CPU_out`
- `tests/figures/CaseSWScenario2_Mode3_CombinedLegacyPaths_CPU`
- `tests/figures/CaseSWScenario2_Mode3_CombinedLegacyPaths_CPU_vs_old_cpu`
- `tests/configs/CaseSWScenario2_Mode3_CombinedLegacyPaths_CPU_Def.xml`
- `tests/xCaseSWScenario2_Mode3_CombinedLegacyPaths_CPU_win64_CPU.bat`

Temporary source changes were reverted after the test, and CPU Debug/Release builds passed.
