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
- GPU after patch: 0, 0.001, 0.002001, 0.003001, 0.004, 0.005

## Run Status

| run | launcher code | DualSPHysics code | excluded | steps | runtime_s | body-gravity stop log | hydraulic-gravity log |
|---|---:|---:|---:|---:|---:|---|---|
| CPU | 0 | 0 | 0 | 5244 | 122.382866 | True | True |
| GPU after patch | 0 | 0 | 0 | 5244 | 12.454111 | True | True |

## Final Short-Smoke Metrics

| metric | CPU | GPU after patch |
|---|---:|---:|
| max velocity [m/s] | 0.0237297 | 0.0237297 |
| mean settlement dz [m] | -9.77993e-06 | -9.77993e-06 |
| PorePress mean [Pa] | 8516.32 | 8516.32 |
| ExcessPorePress maxAbs [Pa] | 5033.58 | 5033.57 |
| bottom excess mean [Pa] | 2594.68 | 2594.68 |
| top layer excess maxAbs [Pa] | 0 | 0.000110986 |
| bottom no-flux proxy [Pa] | 0.92289 | 0.922783 |
| PorePressRate maxAbs [Pa/s] | 8.16277e+07 | 8.15609e+07 |
| PorePressureAccelDiff maxAbs [m/s2] | 10.4957 | 10.491 |

## CPU/GPU Parity After Patch

Final nearest-frame differences:

- `PorePress` maxAbs: 0.00393928 Pa
- `ExcessPorePress` maxAbs: 0.00393927 Pa
- `PorePressRate` maxAbs: 641320 Pa/s
- `|Vel|` maxAbs: 6e-09 m/s

The CPU/GPU fields remain aligned through and after the gravity switch. The final pore-pressure and velocity differences are at numerical roundoff scale for the short smoke window. `PorePressRate` keeps a larger absolute max difference because it is a high-gradient diagnostic field, but the resulting pressure state and velocity remain matched.

## Switch Behavior

The CPU and GPU runs both reported the mechanical gravity stop diagnostic and kept hydraulic gravity active:

- CPU: `Mechanical body gravity stopped at TimeStep=0.00200051. Hydraulic gravity remains active.`
- GPU: `Mechanical body gravity stopped on GPU at TimeStep=0.00200051. Hydraulic gravity remains active.`

The short CPU and GPU runs remained stable around `t=0.002 s`, with `excluded=0`, continuous pore-pressure output, active top-drained projection after the switch, and a finite bottom no-flux proxy.

## S1-1b GPU BodyGravityStopTime Patch

The S1-1 before-patch smoke showed that GPU completed without error but did not stop mechanical body gravity. The GPU path has now been patched in `JSphGpu.cpp` so the host-side integration calls pass `GetMechanicalGravity(TimeStep)` to the Verlet and Symplectic GPU step kernels. Hydraulic gravity remains independent and is still used by the pore-pressure hydrostatic/elevation terms.

Before/after final metrics:

| metric | GPU before patch | GPU after patch | CPU reference |
|---|---:|---:|---:|
| body-gravity stop log | False | True | True |
| ExcessPorePress maxAbs [Pa] | 30183.2 | 5033.57 | 5033.58 |
| bottom excess mean [Pa] | 30174.2 | 2594.68 | 2594.68 |
| max velocity [m/s] | 0.00343584 | 0.0237297 | 0.0237297 |
| final PorePress CPU/GPU maxAbs diff [Pa] | 27619.7 | 0.003939 | 0 |
| final Excess CPU/GPU maxAbs diff [Pa] | 27619.6 | 0.003939 | 0 |
| final velocity CPU/GPU maxAbs diff [m/s] | 0.0217596 | 6e-09 | 0 |

The before-patch divergence after `t=0.002 s` was removed. The after-patch GPU result now follows the CPU BodyGravityStopTime route over the S1-1 short window.

## Recommendation

GPU single-run BodyGravityStopTime is now viable for a Scenario 1 medium run.

The restart route remains deferred as planned. The next concrete task should be Scenario 1 GPU medium smoke using the same `BodyGravityStopTime` single-run route, not a long run yet.

## Artifacts

- XML/BAT and analysis scripts: `examples/u-pw/02_SelfWeight_Consolidation/experiments/GPU_S1_BodyGravityStopShort/`
- Metrics:
  - `s1_bodygravity_stop_frame_metrics_cpu.csv`
  - `s1_bodygravity_stop_frame_metrics_gpu_before_patch.csv`
  - `s1_bodygravity_stop_frame_metrics_gpu_after_patch.csv`
  - `s1_bodygravity_stop_parity_metrics_before_patch.csv`
  - `s1_bodygravity_stop_parity_metrics_after_patch.csv`
  - `s1_bodygravity_stop_case_summary_before_patch.csv`
  - `s1_bodygravity_stop_case_summary_after_patch.csv`
- Figures: `figures/*.svg`, `figures/*.png`
