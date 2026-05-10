# Smoke Status: Undrained Triaxial Reduced PR Case

Date: 2026-05-10

## Case

- XML: `CaseUndrainedTriaxial_PR_Smoke_Def.xml`
- Launcher: `xCaseUndrainedTriaxial_PR_Smoke_win64_CPU_debug.bat`
- Solver path tested: CPU Debug
- TimeMax: `0.001 s`
- TimeOut: `0.001 s`

## Execution

| Check | Result |
| --- | --- |
| GenCase | code=0 |
| DualSPHysics | code=0 |
| Excluded particles | 0 |
| Steps | 1049 |
| Runtime | 103.77 s |
| Material particles | 1000 |
| Top AccInput layer | 10 particles, `mkfluid=1` |

## Field Output

`PartCsv_0001.csv` included the required u-pw fields:

- `PorePress`
- `ExcessPorePress`
- `PorePressRate`
- `DivVel`
- `LapPorePress`
- `LapZ`
- `DivVelCorr`
- `LapPorePressCorr`
- `LapZCorr`
- `PorePressureAccel`
- `PorePressureAccelDiff`
- velocity, density, `Sigma_kk`, `Sigma_ij`, and `Kplastic`

## Short-Window Metrics

| Metric | Value |
| --- | --- |
| Max velocity | `1.86e-5 m/s` |
| Mean velocity | `2.47e-6 m/s` |
| PorePress min/max/mean | `64.53 / 9761.04 / 4908.76 Pa` |
| ExcessPorePress min/max/mean | `0.0903 / 15.48 / 3.76 Pa` |
| PorePressRate max | `3.74e4 Pa/s` |
| DivVel min/max/mean | `-3.15e-4 / -4.01e-8 / -1.63e-5 1/s` |
| PorePressureAccelDiff.z min/max/mean | `-2.21e-2 / 1.67e-6 / -7.24e-3 m/s2` |

## Interpretation

The reduced smoke is runnable and stable for the CPU pre-GPU case gate. It does
not validate the strict undrained triaxial benchmark because prescribed
confinement, controlled axial strain/stress, and a calibrated triaxial material
model are still missing.

Generated output was removed after recording these metrics.
