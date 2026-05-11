# GPU S1 BodyGravityStopTime short smoke

## Objective

This smoke test checks the Scenario 1 single-run route where mechanical body gravity is stopped at `t=0.002 s` while `HydraulicGravity=(0,0,-9.81)` remains active. The test is intentionally short (`TimeMax=0.005 s`) and uses the legacy production hydraulic boundary mode `PorePressureBoundaryOperator=0`.

## Setup

- Base case: `CaseSelfWeightConsolidation_PR_Scenario2_Def.xml`
- Route: `BodyGravityStopTime` single run, no restart
- `BodyGravityStopTime=0.002`
- `PorePressureTopDrained=1`, `PorePressureTopDrainedStartTime=0.002`
- `PorePressureBottomNoFlux=1`
- `HydromechDampingXi=0.05`
- `PorePressureFeedbackMode=1`, `PorePressureFeedbackOperator=1`
- `PorePressureShepard=1`, interval `10`, mode `1`
- `PorePressureDtSafety=0.20`
- `SavePorePressure=1`

## Retained Output Times

- CPU: 0, 0.001, 0.002001, 0.003001, 0.004, 0.005
- GPU: 0, 0.001, 0.002001, 0.003001, 0.004, 0.005

## Run Status

| run | launcher code | DualSPHysics code | excluded | steps | runtime_s | body-gravity stop log | hydraulic-gravity log |
|---|---:|---:|---:|---:|---:|---|---|
| CPU | 0 | 0 | 0 | 5244 | 119.554955 | True | True |
| GPU | 0 | 0 | 0 | 5244 | 12.323503 | False | False |

## Final Short-Smoke Metrics

| metric | CPU | GPU |
|---|---:|---:|
| max velocity [m/s] | 0.0237297 | 0.00343584 |
| mean settlement dz [m] | -9.77993e-06 | -4.09392e-05 |
| PorePress mean [Pa] | 8516.32 | 22384.8 |
| ExcessPorePress maxAbs [Pa] | 5033.58 | 30183.2 |
| bottom excess mean [Pa] | 2594.68 | 30174.2 |
| top layer excess maxAbs [Pa] | 0 | 9.21459e-06 |
| bottom no-flux proxy [Pa] | 0.92289 | 0.285256 |
| PorePressRate maxAbs [Pa/s] | 8.16277e+07 | 3.16914e+08 |
| PorePressureAccelDiff maxAbs [m/s2] | 10.4957 | 24.6147 |

## CPU/GPU Parity

Final nearest-frame differences:

- `PorePress` maxAbs: 27619.7 Pa
- `ExcessPorePress` maxAbs: 27619.6 Pa
- `PorePressRate` maxAbs: 2.75632e+08 Pa/s
- `|Vel|` maxAbs: 0.0217596 m/s

The CPU/GPU fields are essentially identical through the output immediately at the switch (`t≈0.002001 s`), then diverge rapidly after the switch. This is the expected signature if CPU stops mechanical body gravity and GPU continues applying constant body gravity.

## Switch Behavior

The CPU run reported the `Mechanical body gravity stopped` diagnostic and kept hydraulic gravity active. The GPU run did not report the same stop diagnostic. A source-side audit made before this smoke also found that GPU integration kernels still receive the constant `Gravity` vector directly, while the CPU path calls `GetMechanicalGravity(TimeStep)`. Because this S1 route depends on disabling mechanical body gravity while retaining hydraulic gravity, GPU medium/long Scenario 1 should not proceed from this exact build unless GPU-side mechanical gravity switching is implemented and re-smoked.

The short CPU run remained stable around `t=0.002 s`, with `excluded=0`, continuous pore-pressure output, active top-drained projection after the switch, and a finite bottom no-flux proxy. The GPU run also completed with `excluded=0`, but its physics after `t=0.002 s` cannot be certified as Scenario 1 BodyGravityStopTime behavior without the GPU stop event.

## Recommendation

GPU single-run BodyGravityStopTime is not validated in this build because the GPU log did not report the mechanical-gravity stop event; medium Scenario 1 should wait for a narrow GPU BodyGravityStopTime implementation or use the restart route.

The restart route remains deferred as planned. The next concrete task should be a minimal GPU `BodyGravityStopTime` support patch, followed by rerunning this S1-1 short smoke. No Scenario 1 medium/long run is recommended before that.

## Artifacts

- XML/BAT and analysis script: `examples/u-pw/02_SelfWeight_Consolidation/experiments/GPU_S1_BodyGravityStopShort/`
- Metrics:
  - `s1_bodygravity_stop_frame_metrics_cpu.csv`
  - `s1_bodygravity_stop_frame_metrics_gpu.csv`
  - `s1_bodygravity_stop_parity_metrics.csv`
  - `s1_bodygravity_stop_case_summary.csv`
- Figures: `figures/*.svg`, `figures/*.png`
