# Self-weight Scenario 2 two-stage validation and damping check

Date: 2026-07-02

## Purpose

Validate the two-stage Scenario 2 workflow after restoring fixed-time-step semantics:

1. Stage 1: undrained self-weight initialization, drainage enabled at the top free surface, pore-pressure Shepard regularization enabled with interval 40, `SoilDampingCoef=0.02`.
2. Stage 2: restart from the stable Stage 1 state, inherit pore pressure and stress state, run drained Scenario 2 with output interval `DTv=0.005`.
3. Re-run Stage 2 on GPU to check reproducibility.
4. Run a smaller damping case (`SoilDampingCoef=0.01`) to check whether accuracy improves.

No source-code changes were made during this test set.

## Configurations

Main damping 0.02:

- Stage 1 config: `tests/configs/CaseSWStage1_TwoStage_Damp002_DrainShep40_t040_Def.xml`
- Stage 2 config: `tests/configs/CaseSWScenario2_TwoStage_Damp002_DTv0005_Def.xml`
- Stage 1 output: `tests/outputs/CaseSWStage1_TwoStage_Damp002_DrainShep40_t040_GPU_out`
- Stage 2 output: `tests/outputs/CaseSWScenario2_TwoStage_Damp002_DTv0005_from_p0060_GPU_out`
- GPU reproducibility run output: `tests/outputs/SWSc2_TS_p0060_gpuR2_out`

Smaller damping 0.01:

- Stage 1 config: `tests/configs/CaseSWStage1_TwoStage_Damp001_DrainShep40_t040_Def.xml`
- Stage 2 config: `tests/configs/CaseSWScenario2_TwoStage_Damp001_DTv0005_Def.xml`
- Stage 1 output: `tests/outputs/SWStage1_TS_damp001_t040_gpu_out`
- Stage 2 output: `tests/outputs/SWSc2_TS_d001_p0074_gpu_out`

## Stage 1 restart selection

For `SoilDampingCoef=0.02`, Stage 1 completed to 0.4 s with zero excluded particles. The final bottom pore pressure was 20.0437 kPa compared with the undrained theory value 20.4157 kPa. The selected restart state is:

- `Part_0060`
- Time = 0.300 s
- RMS profile error = 0.07944 kPa
- Bottom pore pressure = 20.1136 kPa
- Maximum speed = 1.462e-05 m/s

Although a purely score-based ranking slightly favored `Part_0056`, `Part_0060` was selected because it had lower residual speed, a better bottom value, and matched the previously observed stable window.

For `SoilDampingCoef=0.01`, Stage 1 was less damped and retained larger residual velocities. The selected restart state is:

- `Part_0074`
- Time = 0.370 s
- RMS profile error = 0.19953 kPa
- Bottom pore pressure = 20.2618 kPa
- Maximum speed = 2.495e-05 m/s

This selection prioritizes low residual speed and a bottom value close to theory.

## Stage 2 damping 0.02 result

The two-stage GPU run using `SoilDampingCoef=0.02` completed successfully:

- Fixed time step: 1.0e-6 s
- Stage 2 steps: 3,850,000
- Excluded particles: 0
- Restart state: Stage 1 `Part_0060`
- Restart data confirmed: stress, pore pressure, and `PorePress0` inherited

Important target comparisons:

| Tv | Bottom SPH (kPa) | Theory (kPa) | RMS profile error (Pa) |
| --- | ---: | ---: | ---: |
| 0.000 | 10.4017 | 10.6964 | 98.573 |
| 0.005 | 9.86395 | 9.88899 | 70.089 |
| 0.050 | 8.05135 | 8.03550 | 30.736 |
| 0.100 | 6.94800 | 6.91237 | 32.511 |
| 0.250 | 4.76348 | 4.70479 | 43.603 |
| 0.400 | 3.32519 | 3.24695 | 55.464 |
| 0.500 | 2.62346 | 2.53689 | 61.424 |
| 0.700 | 1.69277 | 1.54876 | 85.764 |
| 1.000 | 0.84620 | 0.73877 | 73.623 |

Conclusion: the two-stage workflow removes the large initial overshoot seen in direct `HydroMechInitMode=3` runs and avoids the late plateau observed before the fixed-time-step correction. The remaining late-time bottom pressure is slightly high, about 0.107 kPa at `Tv=1`.

## GPU reproducibility

The second GPU run used the same damping 0.02 Stage 1 restart and the same Stage 2 config.

- Output: `tests/outputs/SWSc2_TS_p0060_gpuR2_out`
- Excluded particles: 0
- Maximum bottom-pressure difference from the first GPU run: 0.001616 kPa, about 1.616 Pa, near `Tv=0.885`.

Conclusion: the GPU result is effectively reproducible for this case.

## Smaller damping check

The `SoilDampingCoef=0.01` two-stage GPU run completed successfully from `Part_0074`.

Important target comparisons:

| Tv | Damp 0.02 RMS (Pa) | Damp 0.01 RMS (Pa) | Damp 0.01 - Damp 0.02 (Pa) |
| --- | ---: | ---: | ---: |
| 0.000 | 98.573 | 221.642 | +123.069 |
| 0.005 | 70.089 | 72.238 | +2.149 |
| 0.050 | 30.736 | 43.904 | +13.168 |
| 0.100 | 32.511 | 41.941 | +9.430 |
| 0.250 | 43.603 | 45.558 | +1.955 |
| 0.400 | 55.464 | 53.923 | -1.542 |
| 0.500 | 61.424 | 58.824 | -2.600 |
| 0.700 | 85.764 | 83.234 | -2.529 |
| 1.000 | 73.623 | 71.045 | -2.578 |

Conclusion: damping 0.01 gives only a very small late-time RMS improvement, about 1.5 to 2.6 Pa, but worsens Stage 1 stability and early/mid-time profile accuracy. It is not a better default than damping 0.02.

## Figures and CSV summaries

- Main damping 0.02 profiles: `tests/figures/CaseSWScenario2_TwoStage_Damp002_DTv0005_from_p0060_GPU/scenario2_pore_pressure_profiles.png`
- Main damping 0.02 bottom series: `tests/figures/CaseSWScenario2_TwoStage_Damp002_DTv0005_from_p0060_GPU/scenario2_bottom_dissipation.csv`
- GPU reproducibility comparison: `tests/figures/twostage_gpu_repro_compare/`
- Damping comparison: `tests/figures/twostage_damping_compare/`

## Current recommendation

Use the two-stage Scenario 2 setup with:

- Stage 1: `SoilDampingCoef=0.02`, top drainage enabled, pore-pressure Shepard interval 40, restart from about 0.30 s.
- Stage 2: inherit Stage 1 state, `SoilDampingCoef=0.02`, no pore-pressure Shepard filtering, `DTv=0.005`, fixed `dt=1e-6`.

The smaller damping test does not justify changing the baseline damping coefficient.
