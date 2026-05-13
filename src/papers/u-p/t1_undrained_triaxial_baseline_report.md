# T1 Undrained Triaxial Baseline Report

Date: 2026-05-13

## Result

T1 created and ran a reduced CPU Release undrained triaxial-style baseline:

```text
examples/u-pw/04_Undrained_Triaxial/experiments/T1_UndrainedTriaxialBaseline/
```

This is not a full paper reproduction. It is a short workflow smoke for the
u-pw PR framework under reduced axial loading.

## Case Definition

Key choices:

- `SoilConstitutiveModel=0`;
- `HydromechCoupling=1`;
- `PorePressureModel=1`;
- `PorePressureBoundaryOperator=0`;
- `HydraulicElevationSource=0`;
- `HydraulicGravity=(0,0,-9.81)`;
- `PorePressureInit=0`;
- `PorePressureFeedback=1`;
- `PorePressureFeedbackMode=1`;
- `PorePressureFeedbackOperator=1`;
- `PorePressureShepard=1`;
- `PorePressureShepardInterval=10`;
- `PorePressureShepardMode=1`;
- `PorePressureDtSafety=0.20`.

No Cryer curved drained boundary modes and no deprecated Cryer modes `5-8`
were used.

## Loading and Confinement

T1 uses native DualSPHysics `accinput` on the top `mkfluid=1` material layer:

```text
0.001 s -> LinearAccZ = -0.5 m/s2
```

This is reduced axial compression. It is not strict triaxial stress or strain
control. Lateral confinement is only the existing fixed/mDBC boundary support;
`FlexibleConfiningStress` is not used.

## Execution

The CPU Release BAT ran:

```text
GenCase -> DualSPHysics CPU Release -> PartVTK
```

Results:

| Check | Result |
|---|---:|
| GenCase | `code=0` |
| DualSPHysics CPU Release | `code=0` |
| PartVTK | `code=0` |
| Excluded particles | `0` |
| Steps | `6` |
| PART frames | `4` |
| Runtime | `0.258549 s` |
| NaN/Inf field count in postprocessing | `0` |

GPU was not run because T1 uses `HydraulicElevationSource=0`, which is
CPU-only in this branch.

## Measurement Region

The postprocessor defines the diagnostic measurement region as an
upper-middle core below the AccInput layer:

```text
x: central 25%-75% of initial material width
z: 70%-90% of initial material height
```

This is deliberate for T1 because the smoke is very short and top-loaded; the
geometric center remains essentially unloaded over `0.001 s`.

## Postprocessed Metrics

Final metrics from `t1_case_summary.csv`:

| Metric | Value |
|---|---:|
| Final time | `0.001005 s` |
| Measurement-region particles | `80` |
| Top tracking particles | `30` |
| Final axial displacement | `-5.67e-08 m` |
| Final axial strain proxy | `5.50e-08` |
| Final region mean `ExcessPorePress` | `42.12 Pa` |
| Final region mean `PorePress` | `42.12 Pa` |
| Final region `PorePressRate` maxAbs | `2.31e6 Pa/s` |
| Final region mean `DivVel` | `-5.70e-04 1/s` |
| Final max velocity | `4.42e-04 m/s` |
| Final `Kplastic` max | `0` |
| Minimum pore pressure | `0 Pa` |

The pressure response is compression-positive in the loaded upper-middle
region and remains finite. Because `HydraulicElevationSource=0`, total and
excess pore pressure are identical in this case.

## Stress-Path Proxy

The script writes `t1_stress_path_metrics.csv` and the figure
`figures/t1_pq_path_proxy.*`. This is an approximate p-q diagnostic from saved
stress components, not a validated triaxial stress path.

Final proxy values:

| Metric | Value |
|---|---:|
| Region `p'` proxy | `0.105 Pa` |
| Region `q` proxy | `0.097 Pa` |
| All-material `p'` proxy | `0.111 Pa` |
| All-material `q` proxy | `0.103 Pa` |

These values are tiny because T1 is intentionally a very short small-strain
smoke.

## Figures and CSV

Retained CSV:

- `t1_frame_metrics.csv`;
- `t1_case_summary.csv`;
- `t1_measurement_region_metrics.csv`;
- `t1_pore_pressure_metrics.csv`;
- `t1_stress_path_metrics.csv`.

Retained figures:

- axial displacement and strain versus time;
- pore pressure and excess pressure versus time;
- velocity max versus time;
- `DivVel` / `PorePressRate` versus time;
- `Kplastic` max versus time;
- p-q proxy path.

## Interpretation

T1 passes the reduced CPU smoke gate:

- the baseline case is runnable;
- u-pw PR fields are written;
- the top-loaded upper-middle region develops finite positive pore pressure;
- `Kplastic=0`, as expected for `SoilConstitutiveModel=0`;
- no NaN/Inf was detected;
- no particles were excluded.

It does not validate the paper triaxial case. It lacks true lateral confining
pressure, controlled axial strain/stress loading, and validated p-q reduction.

## Next Step

T2 can start from this workflow. Recommended T2 scope:

1. validate and improve stress-path postprocessing (`p'`, `q`, axial strain,
   volumetric strain);
2. add a DP baseline as a separate case and track `Kplastic`;
3. refine loading/confinement, preferably before any paper-theory comparison;
4. keep full paper reproduction and MCC out of scope until the reduced
   stress-path workflow is trustworthy.
