# Smoke Status: Undrained Triaxial Reduced PR Case

Date: 2026-05-11

## Case

- XML: `CaseUndrainedTriaxial_PR_Smoke_Def.xml`
- Launcher: `xCaseUndrainedTriaxial_PR_Smoke_win64_CPU_debug.bat`
- Solver path tested: CPU Release
- TimeMax: `0.001 s`
- TimeOut: `0.001 s`

## Execution

| Check | Result |
| --- | --- |
| GenCase | code=0 |
| DualSPHysics | code=0 |
| Excluded particles | 0 |
| Steps | 1049 |
| Runtime | 22.10 s |
| Particle rows in CSV | 1040 |
| Top AccInput layer | 10 particles, `mkfluid=1` |
| NaN/Inf scan | not detected |

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
| Mean pore pressure | `4719.96 Pa` |
| Mean excess pore pressure | `3.61 Pa` |
| Mean `p'` proxy | `9.05e-3 Pa` |
| Mean `q` proxy | `8.36e-3 Pa` |
| Axial strain proxy | `0.0` over this tiny smoke window |

## Interpretation

The reduced smoke is runnable and stable for the CPU pre-GPU case gate. It does
not validate the strict undrained triaxial benchmark because prescribed
confinement, controlled axial strain/stress, and a calibrated triaxial material
model are still missing.

`analyze_triaxial_smoke.py` now writes `triaxial_smoke_summary.csv` with
framewise `p'`, `q`, pore pressure, excess pore pressure, axial-strain proxy,
and velocity metrics. Generated output was removed after recording these
metrics.
