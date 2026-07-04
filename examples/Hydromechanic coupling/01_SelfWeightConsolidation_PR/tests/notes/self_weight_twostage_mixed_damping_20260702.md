# Self-weight Scenario 2 mixed damping check

Date: 2026-07-02

## Purpose

Test the mixed damping setup requested after the two-stage Scenario 2 validation:

- Stage 1: `SoilDampingCoef=0.02`, restart from the stable `Part_0060` state.
- Stage 2: `SoilDampingCoef=0.01`, otherwise identical to the validated two-stage Scenario 2 setup.

This isolates whether lowering damping only during the drained consolidation stage improves accuracy while preserving the more stable `0.02` initialization.

No source-code changes were made.

## Run

- Case name: `SWSc2_TS_s1d002_s2d001_gpu`
- Stage 1 source: `tests/outputs/CaseSWStage1_TwoStage_Damp002_DrainShep40_t040_GPU_out/data`
- Stage 1 restart part: `Part_0060`
- Stage 2 config: `tests/configs/CaseSWScenario2_TwoStage_Damp001_DTv0005_Def.xml`
- Stage 2 output: `tests/outputs/SWSc2_TS_s1d002_s2d001_gpu_out`
- Stage 2 figures: `tests/figures/SWSc2_TS_s1d002_s2d001_gpu`
- Three-case comparison: `tests/figures/twostage_stage1d002_stage2d001_compare`
- VTK export: `PartFluid_*.vtk` contains 1000 fluid particles; `PartBound_*.vtk` was exported with `-onlytype:-all,bound` and contains 40 boundary particles.

Execution completed successfully:

- `DTs adjusted to DtMin = 0`
- `Excluded particles = 0`
- `Steps of simulation = 3850000`
- `PART files = 212`
- Runtime = 13559.163 s

Runtime confirmed the intended restart path:

- `PartBegin=60`
- `PartBeginDir=outputs\CaseSWStage1_TwoStage_Damp002_DrainShep40_t040_GPU_out\data`
- `Restart soil data: Sigma inherited, Kplastic reset for restart stage.`
- `Restart hydromechanical data: PorePress and PorePress0 inherited.`
- `SoilDampingCoef=0.01` in Stage 2

## Target comparison

| Tv | RMS d002/d002 (Pa) | RMS d002/d001 (Pa) | RMS d001/d001 (Pa) | Bottom err d002/d002 (kPa) | Bottom err d002/d001 (kPa) | Bottom err d001/d001 (kPa) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.000 | 98.573 | 98.573 | 221.642 | -0.2947 | -0.2947 | -0.1465 |
| 0.005 | 70.089 | 96.453 | 72.238 | -0.0250 | 0.0215 | -0.0391 |
| 0.050 | 30.736 | 47.493 | 43.904 | 0.0159 | 0.0406 | 0.0323 |
| 0.100 | 32.510 | 45.493 | 41.941 | 0.0356 | 0.0539 | 0.0481 |
| 0.250 | 43.603 | 48.123 | 45.558 | 0.0587 | 0.0648 | 0.0613 |
| 0.400 | 55.464 | 55.721 | 53.923 | 0.0782 | 0.0787 | 0.0763 |
| 0.500 | 61.424 | 60.093 | 58.824 | 0.0866 | 0.0847 | 0.0832 |
| 0.700 | 85.764 | 83.197 | 83.234 | 0.1440 | 0.1406 | 0.1410 |
| 1.000 | 73.623 | 71.119 | 71.045 | 0.1074 | 0.1042 | 0.1041 |

## Conclusion

The mixed setup keeps the stable `0.02` Stage 1 initial state, so `Tv=0` matches the `0.02/0.02` baseline exactly. However, lowering damping only in Stage 2 worsens the early-to-mid consolidation profiles:

- At `Tv=0.005`, RMS increases from 70.089 Pa to 96.453 Pa.
- At `Tv=0.05`, RMS increases from 30.736 Pa to 47.493 Pa.
- At `Tv=0.10`, RMS increases from 32.510 Pa to 45.493 Pa.
- At `Tv=0.25`, RMS increases from 43.603 Pa to 48.123 Pa.

The late-time improvement is real but very small:

- At `Tv=0.5`, RMS improves by about 1.33 Pa.
- At `Tv=0.7`, RMS improves by about 2.57 Pa.
- At `Tv=1.0`, RMS improves by about 2.50 Pa.

Recommendation: keep the current baseline as `Stage 1 damping=0.02` and `Stage 2 damping=0.02`. The `Stage 2 damping=0.01` option only gives a tiny late-time benefit and degrades the more important early-to-mid profile agreement.
