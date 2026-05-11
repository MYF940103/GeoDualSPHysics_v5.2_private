# GPU G9 Self-Weight Scenario 2 Long-Run Report

Date: 2026-05-11

## Scope

G9 runs the GPU Release self-weight Scenario 2 line to `TimeMax=3.6 s` using
the validated G1-G6 GPU coupled PR path. No source code was modified.

This phase does not include:

- parameter sensitivity;
- `xi=0.05`;
- Scenario 1 restart workflow on GPU;
- GPU softening;
- GPU boundary ghost production operators;
- corrected-gradient production operators;
- new GPU PR features.

## Case Directory

```text
examples/u-pw/02_SelfWeight_Consolidation/experiments/GPU_G9_SelfWeightLong/
```

Retained files:

- `CaseSelfWeightConsolidation_PR_Scenario2_GPU_T3p6_Xi010_Def.xml`
- `xCaseSelfWeightConsolidation_PR_Scenario2_GPU_T3p6_Xi010_win64_GPU_release.bat`
- `analyze_gpu_g9_selfweight.py`
- `plot_gpu_g9_si.py`
- `gpu_g9_frame_metrics.csv`
- `gpu_g9_case_summary.csv`
- `figures/gpu_g9_porepress_profiles.svg`
- `figures/gpu_g9_excess_profiles.svg`
- `figures/gpu_g9_bottom_porepress_time.svg`
- `figures/gpu_g9_excess_time.svg`

Generated `_out` folders, particle data, and console logs were removed after
analysis.

## Settings

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
- `SavePorePressure=1`;
- `TimeMax=3.6`;
- `TimeOut=0.1`.

## Run Summary

| Metric | GPU G9 |
|---|---:|
| code | 0 |
| excluded particles | 0 |
| steps | 3775438 |
| runtime | 10946.52 s |
| frames | 37 |
| final time | 3.6 s |

## Final State

| Quantity | Value |
|---|---:|
| final velocity max | `2.106e-4 m/s` |
| final velocity mean | `1.399e-4 m/s` |
| final mean z displacement | `-2.474e-3 m` |
| final `PorePress` max | `10922.62 Pa` |
| final hydrostatic max | `9762.26 Pa` |
| final `ExcessPorePress` max | `1160.52 Pa` |
| final `ExcessPorePress` mean | `725.99 Pa` |
| final bottom `ExcessPorePress` mean | `1160.35 Pa` |
| final top drained excess maxAbs | `9.83e-7 Pa` |
| final bottom no-flux proxy | `1.90e-4 Pa` |
| max `PorePressRate` over saved frames | `1.229e8 Pa/s` |
| max `DivVel` contribution over saved frames | `7.19e-3 1/s` |
| max hydraulic contribution over saved frames | `1.844e-1 1/s` |
| max `PorePressureAccelDiff` over saved frames | `9.924 m/s2` |

## Trend

The run shows the expected Scenario 2 gravity-on trend:

- excess pore pressure rises during the early undrained self-weight response;
- after top drainage activates, excess pressure decays;
- total pore pressure approaches the hydrostatic profile;
- velocity decays from the early peak to `2.1e-4 m/s` by `3.6 s`;
- settlement accumulates smoothly;
- top drained and bottom no-flux corrections remain stable.

Saved-frame excess-pressure envelope:

- peak maxAbs: `15595.77 Pa`;
- final maxAbs: `1160.52 Pa`.

## CPU SW3h Comparison

The committed CPU SW3h run used the same `xi=0.10` Scenario 2 line.

| Quantity | GPU G9 | CPU SW3h | GPU - CPU |
|---|---:|---:|---:|
| final `ExcessPorePress` max | `1160.52 Pa` | `1159.52 Pa` | `1.00 Pa` |
| final `ExcessPorePress` mean | `725.99 Pa` | `725.43 Pa` | `0.56 Pa` |
| final bottom excess mean | `1160.35 Pa` | `1159.35 Pa` | `1.00 Pa` |
| final `PorePress` max | `10922.62 Pa` | `10921.61 Pa` | `1.01 Pa` |

Runtime:

- GPU G9: `10946.52 s`;
- CPU SW3h: `68552.66 s`;
- speedup: `6.26x`.

## Figures

The following SVG figures were generated:

- `gpu_g9_porepress_profiles.svg`;
- `gpu_g9_excess_profiles.svg`;
- `gpu_g9_bottom_porepress_time.svg`;
- `gpu_g9_excess_time.svg`.

## Conclusion

G9 passes as the GPU Release long-run Scenario 2 trend check:

- `code=0`;
- `excluded=0`;
- no source changes;
- excess pressure decays strongly by `3.6 s`;
- total pressure trends toward hydrostatic;
- hydraulic boundary corrections remain stable;
- final GPU metrics agree closely with the previously committed CPU SW3h result.

Remaining work is outside G9 scope: Scenario 1 GPU restart workflow, parameter
sensitivity, GPU softening, production boundary ghost operators, and
corrected-gradient production operators.
