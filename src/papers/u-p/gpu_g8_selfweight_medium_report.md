# GPU G8 Self-Weight Medium-Run Report

Date: 2026-05-11

## Scope

G8 runs short-to-medium GPU Release self-weight Scenario 2 checks. It does not
modify source code and does not run the full 3.6 s reproduction.

G8 excludes:

- Scenario 1 GPU restart workflow;
- GPU softening;
- GPU boundary ghost production operators;
- corrected-gradient production operators;
- parameter sensitivity;
- 3.6 s long reproduction.

## Case Directory

```text
examples/u-pw/02_SelfWeight_Consolidation/experiments/GPU_G8_SelfWeightMedium/
```

Retained files:

- `CaseSelfWeightConsolidation_PR_GPU_G8_T0p05_Def.xml`
- `CaseSelfWeightConsolidation_PR_GPU_G8_T0p2_Def.xml`
- `xCaseSelfWeightConsolidation_PR_GPU_G8_T0p05_win64_GPU_release.bat`
- `xCaseSelfWeightConsolidation_PR_GPU_G8_T0p2_win64_GPU_release.bat`
- `analyze_gpu_g8_selfweight.py`
- `gpu_g8_case_summary.csv`
- `gpu_g8_frame_metrics.csv`

Generated `_out` directories and console logs were removed after analysis.

## Settings

Both G8 runs use the G7 self-weight Scenario 2 setup:

- body gravity `(0,0,-9.81)`;
- hydraulic gravity `(0,0,-9.81)`;
- `HydromechCoupling=1`;
- `PorePressureModel=1`;
- `PorePressureInit=1`;
- `PorePressureFeedback=1`;
- `PorePressureFeedbackMode=1`;
- `PorePressureFeedbackOperator=1`;
- `PorePressureTopDrained=1`;
- `PorePressureTopDrainedStartTime=0.002`;
- `PorePressureBottomNoFlux=1`;
- `PorePressureShepard=1`;
- `PorePressureShepardInterval=10`;
- `PorePressureShepardMode=1`;
- `HydromechDamping=1`;
- `HydromechDampingXi=0.10`;
- `PorePressureDtSafety=0.20`;
- `SavePorePressure=1`.

## Run Results

| Run | TimeMax | TimeOut | code | excluded | steps | runtime |
|---|---:|---:|---:|---:|---:|---:|
| A | 0.05 s | 0.005 s | 0 | 0 | 52437 | 126.38 s |
| B | 0.2 s | 0.02 s | 0 | 0 | 209747 | 495.20 s |

## Trend Summary

### Run A: 0.05 s

- Peak saved-frame `ExcessPorePress` maxAbs: `27696.18 Pa`.
- Final `ExcessPorePress` maxAbs: `16675.28 Pa`.
- Final bottom excess mean: `16671.40 Pa`.
- Final velocity max/mean: `2.590e-3 / 2.154e-3 m/s`.
- Final mean settlement: `-1.396e-4 m`.
- Final `PorePress` max/mean: `26432.53 / 14396.77 Pa`.
- Final `PorePressRate` maxAbs: `1.223e8 Pa/s`.
- Final `DivVel` maxAbs: `1.020e-2 1/s`.
- Final hydraulic contribution maxAbs: `1.834e-1 1/s`.
- Final `PorePressureAccelDiff` maxAbs: `10.07 m/s2`.
- Final top drained excess maxAbs: `1.21e-5 Pa`.
- Final bottom no-flux proxy maxAbs: `1.34e-2 Pa`.

### Run B: 0.2 s

- Peak saved-frame `ExcessPorePress` maxAbs: `17963.10 Pa`.
- Final `ExcessPorePress` maxAbs: `14059.07 Pa`.
- Final bottom excess mean: `14057.12 Pa`.
- Final velocity max/mean: `2.355e-3 / 1.713e-3 m/s`.
- Final mean settlement: `-4.235e-4 m`.
- Final `PorePress` max/mean: `23818.42 / 13499.50 Pa`.
- Final `PorePressRate` maxAbs: `1.181e8 Pa/s`.
- Final `DivVel` maxAbs: `5.160e-3 1/s`.
- Final hydraulic contribution maxAbs: `1.772e-1 1/s`.
- Final `PorePressureAccelDiff` maxAbs: `9.73 m/s2`.
- Final top drained excess maxAbs: `1.10e-5 Pa`.
- Final bottom no-flux proxy maxAbs: `7.11e-3 Pa`.

## Stability Assessment

Both medium smokes finished with `code=0`, `excluded=0`, finite fields, and
stable hydraulic boundary diagnostics. The saved-frame excess-pressure envelope
declines after the early self-weight generation peak. Velocity also trends down
over the 0.2 s run, while settlement accumulates smoothly.

The 0.2 s run is not a full reproduction. It is a medium stability smoke showing
that the G1-G6 GPU coupled PR path remains stable beyond the short G7 parity
window.

## Next Step

The GPU path can be considered for a separately scoped 3.6 s release run, but
that should be an explicit new phase. It should still avoid parameter
sensitivity and should preserve the current source code unless a narrow bug is
found.
