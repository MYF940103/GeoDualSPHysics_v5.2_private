# GPU G7 Self-Weight Short Parity Report

Date: 2026-05-11

## Scope

G7 validates the already implemented GPU coupled PR path against the CPU
reference for a short self-weight Scenario 2 smoke.

No source files were modified in G7. This phase does not add GPU softening,
boundary ghost production operators, corrected-gradient production operators,
Scenario 1 restart workflow, or long-time reproduction runs.

## Case

Directory:

```text
examples/u-pw/02_SelfWeight_Consolidation/experiments/GPU_G7_SelfWeightParity/
```

Files:

- `CaseSelfWeightConsolidation_PR_GPU_G7_Scenario2Short_Def.xml`
- `xCaseSelfWeightConsolidation_PR_GPU_G7_Scenario2Short_win64_CPU_release.bat`
- `xCaseSelfWeightConsolidation_PR_GPU_G7_Scenario2Short_win64_GPU_release.bat`
- `analyze_gpu_g7_selfweight.py`
- `gpu_g7_selfweight_summary.csv`

The XML is a short-window Scenario 2 parity smoke:

- `TimeMax=0.003 s`
- `TimeOut=0.001 s`
- body gravity `(0,0,-9.81)`
- hydraulic gravity `(0,0,-9.81)`
- `PorePressureInit=1`
- `PorePressureFeedback=1`
- `PorePressureFeedbackMode=1`
- `PorePressureFeedbackOperator=1`
- `PorePressureTopDrained=1`
- `PorePressureTopDrainedStartTime=0.002`
- `PorePressureBottomNoFlux=1`
- `PorePressureShepard=1`
- `PorePressureShepardInterval=10`
- `PorePressureShepardMode=1`
- `HydromechDamping=1`
- `HydromechDampingXi=0.10`
- `PorePressureDtSafety=0.20`
- `SavePorePressure=1`

## Run Results

| Run | code | excluded | steps | runtime |
|---|---:|---:|---:|---:|
| CPU Release | 0 | 0 | 3147 | 70.67 s |
| GPU Release | 0 | 0 | 3147 | 7.38 s |

Both runs wrote the expected pore-pressure fields:

- `PorePress`
- `ExcessPorePress`
- `PorePressRate`
- `DivVel`
- `LapPorePress`
- `LapZ`
- `PorePressureAccelDiff`

## Final-Frame CPU/GPU Comparison

GPU minus CPU maxAbs / mean differences:

| Field | maxAbs difference | mean difference |
|---|---:|---:|
| `PorePress` | `2.60e-3 Pa` | `1.27e-3 Pa` |
| `ExcessPorePress` | `2.60e-3 Pa` | `1.27e-3 Pa` |
| `PorePressRate` | `8.77e4 Pa/s` | `-6.34e2 Pa/s` |
| `PorePressureAccelDiff` magnitude | `1.47e-2 m/s2` | `5.81e-3 m/s2` |
| velocity magnitude | `4.0e-9 m/s` | `-1.13e-9 m/s` |

Field scales at the final frame:

- CPU `PorePress` max: `34929.237 Pa`
- GPU `PorePress` max: `34929.240 Pa`
- CPU `ExcessPorePress` maxAbs: `25193.098 Pa`
- GPU `ExcessPorePress` maxAbs: `25193.099 Pa`
- CPU `PorePressRate` maxAbs: `2.719e8 Pa/s`
- GPU `PorePressRate` maxAbs: `2.720e8 Pa/s`
- CPU `PorePressureAccelDiff` max magnitude: `14.847 m/s2`
- GPU `PorePressureAccelDiff` max magnitude: `14.854 m/s2`

## Boundary Checks

Top drained layer excess:

- CPU maxAbs: `0 Pa`
- GPU maxAbs: `8.50e-5 Pa`

Bottom no-flux proxy:

- CPU maxAbs: `4.72e-1 Pa`
- GPU maxAbs: `4.71e-1 Pa`

Mean vertical displacement:

- CPU: `-2.8057e-5 m`
- GPU: `-2.8057e-5 m`

## Cleanup

Generated CPU/GPU `_out` folders and console logs were removed after extracting
the summary CSV. The retained files are only the XML/BAT templates, analysis
script, and `gpu_g7_selfweight_summary.csv`.

## Conclusion

The GPU coupled short path is stable and comparable to CPU for the self-weight
Scenario 2 smoke:

- CPU and GPU both finished with `code=0`;
- excluded particles remained zero;
- key hydromechanical fields were written;
- final pressure, acceleration, velocity, settlement, and hydraulic boundary
diagnostics are close at the short-window scale.

G7 passes as a short self-weight/Terzaghi-style GPU parity milestone.

This does not validate long-time Scenario 2 reproduction. G8, if requested,
must remain separately scoped and should start with cautious long-run planning
or a still-short extension before any production-duration GPU run.
