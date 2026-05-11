# GPU G9b Self-Weight Scenario 2 xi=0.05 Long-Run Comparison

Date: 2026-05-11

## Scope

G9b runs the self-weight Scenario 2 GPU Release line with
`HydromechDampingXi=0.05` to `TimeMax=3.6 s`. It is a paper-compatible damping
line for comparison against:

- the existing GPU G9 `xi=0.10` long run;
- the existing CPU SW3h `xi=0.10` long run;
- the hydrostatic/theoretical Scenario 2 end trend.

No source code was modified. This phase does not include Scenario 1, GPU
softening, boundary ghost production operators, corrected-gradient production
operators, or new GPU PR features.

## Case Directory

```text
examples/u-pw/02_SelfWeight_Consolidation/experiments/GPU_G9b_SelfWeightLong_Xi005/
```

Retained files:

- `CaseSelfWeightConsolidation_PR_Scenario2_GPU_T3p6_Xi005_Def.xml`
- `xCaseSelfWeightConsolidation_PR_Scenario2_GPU_T3p6_Xi005_win64_GPU_release.bat`
- `analyze_gpu_g9b_selfweight.py`
- `plot_gpu_g9b_comparison.py`
- `gpu_g9b_frame_metrics.csv`
- `gpu_g9b_case_summary.csv`
- SVG and PNG figures under `figures/`

Generated `_out` folders, particle data, BI4 files, VTK files, `Run.out`, and
console logs were removed after analysis.

## Run Setup

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
- `HydromechDampingXi=0.05`;
- `PorePressureDtSafety=0.20`;
- `SavePorePressure=1`;
- `TimeMax=3.6`;
- `TimeOut=0.1`;
- GPU Release only.

## Run Summary

| Metric | GPU G9b xi=0.05 |
|---|---:|
| code | 0 |
| excluded particles | 0 |
| steps | 3775438 |
| runtime | 12888.19 s |
| frames | 37 |
| final time | 3.6 s |

The run completed normally. No residual GPU process had to be killed.

## Final Metrics

| Quantity | Value |
|---|---:|
| final velocity max | `2.027e-4 m/s` |
| final velocity mean | `1.343e-4 m/s` |
| final mean z displacement | `-2.485e-3 m` |
| final `PorePress` max | `10872.27 Pa` |
| final `PorePress` mean | `5624.76 Pa` |
| final hydrostatic max | `9762.27 Pa` |
| final hydrostatic mean | `4929.38 Pa` |
| final `ExcessPorePress` max | `1110.17 Pa` |
| final `ExcessPorePress` mean | `695.39 Pa` |
| final bottom `ExcessPorePress` mean | `1110.00 Pa` |
| final top drained excess maxAbs | `9.46e-7 Pa` |
| final bottom no-flux proxy | `8.72e-3 Pa` |
| max `PorePressRate` over saved frames | `1.252e8 Pa/s` |
| max `DivVel` contribution over saved frames | `7.26e-3 1/s` |
| max hydraulic contribution over saved frames | `1.877e-1 1/s` |
| max `PorePressureAccelDiff` over saved frames | `10.139 m/s2` |

Saved-frame excess envelope:

- peak maxAbs: `15892.95 Pa`;
- final maxAbs: `1110.17 Pa`;
- final/peak ratio: `0.06985`.

## xi=0.05 vs xi=0.10

| Quantity | GPU xi=0.05 | GPU xi=0.10 | xi=0.05 - xi=0.10 |
|---|---:|---:|---:|
| runtime | `12888.19 s` | `10946.52 s` | `1941.67 s` |
| final `ExcessPorePress` max | `1110.17 Pa` | `1160.52 Pa` | `-50.35 Pa` |
| final `ExcessPorePress` mean | `695.39 Pa` | `725.99 Pa` | `-30.60 Pa` |
| final bottom excess mean | `1110.00 Pa` | `1160.35 Pa` | `-50.35 Pa` |
| final `PorePress` max | `10872.27 Pa` | `10922.62 Pa` | `-50.35 Pa` |
| final velocity max | `2.027e-4 m/s` | `2.106e-4 m/s` | `-7.91e-6 m/s` |

The `xi=0.05` line is stable and slightly more dissipated by `3.6 s` in the
saved metrics, but it ran about `17.7%` slower than the `xi=0.10` line on this
machine. Both lines maintain zero excluded particles and stable hydraulic
boundary behavior.

## GPU xi=0.05 vs CPU SW3h xi=0.10

The CPU reference available in the repository is the SW3h `xi=0.10` line, so
this is a cross-damping comparison rather than a strict same-parameter parity
check.

| Quantity | GPU xi=0.05 | CPU xi=0.10 | GPU xi=0.05 - CPU xi=0.10 |
|---|---:|---:|---:|
| runtime | `12888.19 s` | `68552.66 s` | `-55664.46 s` |
| final `ExcessPorePress` max | `1110.17 Pa` | `1159.52 Pa` | `-49.34 Pa` |
| final `ExcessPorePress` mean | `695.39 Pa` | `725.43 Pa` | `-30.04 Pa` |
| final bottom excess mean | `1110.00 Pa` | `1159.35 Pa` | `-49.35 Pa` |
| final `PorePress` max | `10872.27 Pa` | `10921.61 Pa` | `-49.34 Pa` |
| final velocity max | `2.027e-4 m/s` | `2.100e-4 m/s` | `-7.37e-6 m/s` |

Runtime speedup relative to the CPU SW3h line is `5.32x`.

## Supporting Information / Theoretical Comparison

The local repository does not contain machine-readable numerical data from the
Supporting Information Scenario 2 figure. Therefore the generated figures use
the hydrostatic pore-pressure profile as the theoretical end-state reference.

The G9b trend matches the qualitative Supporting Information Scenario 2
expectation:

- body gravity remains active;
- top drainage activates after the short undrained stage;
- excess pore pressure decays strongly;
- total pore pressure trends toward the hydrostatic profile;
- top drained excess remains effectively zero;
- the bottom no-flux proxy stays small.

## Figures

Generated SVG and PNG figures:

- `figures/gpu_g9b_porepress_profiles.svg`
- `figures/gpu_g9b_porepress_profiles.png`
- `figures/gpu_g9b_excess_profiles.svg`
- `figures/gpu_g9b_excess_profiles.png`
- `figures/gpu_g9b_bottom_porepress_time.svg`
- `figures/gpu_g9b_bottom_porepress_time.png`
- `figures/gpu_g9b_bottom_excess_time.svg`
- `figures/gpu_g9b_bottom_excess_time.png`
- `figures/gpu_g9b_excess_envelope_comparison.svg`
- `figures/gpu_g9b_excess_envelope_comparison.png`
- `figures/gpu_g9b_cpu_gpu_theory_comparison.svg`
- `figures/gpu_g9b_cpu_gpu_theory_comparison.png`

## Conclusion

G9b passes as the paper-compatible `xi=0.05` GPU Release Scenario 2 long-run
comparison:

- `code=0`;
- `excluded=0`;
- 37 frames written through `3.6 s`;
- excess pressure decays to about `7.0%` of the saved-frame peak;
- total pressure approaches hydrostatic;
- hydraulic boundary corrections remain stable;
- no source-code changes were made.

The `xi=0.05` line can be kept as the paper-compatible comparison line. The
previous `xi=0.10` line remains useful as a stability-diagnostic line.

Recommended next step: design the GPU Scenario 1 staged workflow separately.
That should not be treated as a new physics-kernel phase; it should first decide
whether to use a GPU PorePress restart path or a GPU-compatible body-gravity stop
route.
