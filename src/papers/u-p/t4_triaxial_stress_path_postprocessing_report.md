# T4 Triaxial Stress-Path Postprocessing Report

## Objective

T4 refines the measurement-region and stress-path postprocessing around the
T3 selected flexible-confinement triaxial smoke. It is still a reduced CPU
workflow. It is not a full triaxial paper reproduction, not a DP/MCC validation,
and not a GPU parity exercise.

## Case Setup

Retained package:

`examples/u-pw/04_Undrained_Triaxial/experiments/T4_StressPathPostprocessing/`

The T4 case is based on the T3 axial-compression plus selected flexible
confinement smoke:

- `SoilConstitutiveModel=0`;
- `HydraulicElevationSource=0`;
- `PorePressureBoundaryOperator=0`;
- `FlexibleConfiningStress=1`;
- `ConfiningStressUseFiSelector=1`;
- `ConfiningStressUseLateralSelector=1`;
- `FlexibleConfiningStressFiDiagnostic=1`;
- cylinder classification and confinement diagnostics enabled;
- top AccInput axial compression retained;
- CPU Release only.

An exploratory `TimeMax=0.004 s` window was too long for this reduced setup and
produced exclusions. The retained T4 smoke is deliberately shorter:

- `TimeMax=0.0015 s`;
- `TimeOut=0.000125 s`;
- final output time approximately `0.001507 s`.

## Run Health

| Item | Result |
| --- | ---: |
| GenCase | `code=0` |
| DualSPHysics CPU Release | `code=0` |
| PartVTK | `code=0` |
| Excluded particles | `0` |
| Steps | `14` |
| PART/CSV frames | `10` |
| Final max velocity | `38.16 m/s` |
| Final `Kplastic` max | `0` |

No GPU run was performed. No source was modified, so no build was required for
T4.

## Output and Postprocessing

New postprocessor:

`scripts/analyze_t4_triaxial_stress_path.py`

Generated CSV files:

- `t4_frame_metrics.csv`
- `t4_case_summary.csv`
- `t4_measurement_region_sensitivity.csv`
- `t4_stress_path_metrics.csv`
- `t4_pore_pressure_strain_metrics.csv`
- `t4_confinement_diagnostics.csv`
- `t4_fi_particle_metrics.csv`

Generated figures are retained as SVG and PNG under `figures/`.

## Measurement Regions

T4 evaluates five regions:

| Region | Final particles | Final mean `PorePress` Pa | Final `p'` proxy Pa | Final `q` proxy Pa |
| --- | ---: | ---: | ---: | ---: |
| `center_core_small` | 3 | `-2.623e6` | `-6.491e3` | `1.452e4` |
| `center_core_medium` | 25 | `-2.276e6` | `-5.273e3` | `1.058e4` |
| `center_core_large` | 63 | `-2.198e6` | `-5.299e3` | `6.992e3` |
| `full_excluding_caps_edges` | 259 | `-2.569e6` | `-4.045e3` | `4.179e3` |
| `zhao_measurement_cylinder` | 45 | `-2.484e6` | `-6.024e3` | `1.056e4` |

The small center core is too sparse for robust stress-path statistics. The
medium/large cores and Zhao-style cylinder are more useful, but the pore
pressure field is still highly dynamic and region-sensitive.

## Stress-Path Status

The `p'-q` path is a proxy, not a strict value.

The postprocessor computes a compression-positive mean-stress proxy from the
written `Sigma` tensor:

`p_eff_proxy = -(sigma_xx + sigma_yy + sigma_zz)/3`

and a standard deviatoric stress proxy:

`q_proxy = sqrt(1.5 * s_ij s_ij)`.

This is appropriate for diagnostic comparison between regions, but not yet for
paper-level stress-path validation. The output does not explicitly label
`Sigma` as total or effective stress and does not write original positions or
material `mk`, so a stricter postprocessor will need source output
enhancements.

## Pore Pressure and Strain

The T4 short run completes without exclusions, but the pore-pressure evolution
is not yet physically smooth enough for strict validation.

Framewise mean pore pressure evolves from zero to small positive values, then
changes sign and becomes strongly negative late in the retained window:

| Time s | Full-specimen mean `PorePress` Pa |
| ---: | ---: |
| `0.000704` | `6.71e2` |
| `0.001005` | `5.63e3` |
| `0.001305` | `6.62e4` |
| `0.001400` | `-9.70e4` |
| `0.001507` | `-3.82e6` |

The final top-layer axial-strain proxy is `0.03326`, while the height-based
strain proxy is `-0.00110`. Their mismatch reinforces that the present loading
is still a short dynamic smoke, not a controlled triaxial strain path.

Shepard regularization occurred during the run and reduced a very large
pressure range, so the late pore-pressure curve should be treated as an
instability diagnostic rather than a stable undrained response.

## Confinement Diagnostics

The selected flexible-confinement diagnostics remain good over the logged
window:

| Metric | Result |
| --- | ---: |
| Legacy target count | `407` |
| Active selected targets | `112` |
| `f_i` min / mean / max | `0.407175 / 0.745128 / 1.00132` |
| `f_i <= 0.70` count | `208` |
| lateral / top / bottom / edge / interior | `196 / 18 / 18 / 112 / 63` |
| lateral `f_i` selected count | `112` |
| lateral inward acceleration mean | `1.87224 m/s2` |
| lateral inward acceleration max | `1.9072 m/s2` |
| cap axial acceleration leakage | `0` |
| COM acceleration diagnostic | order `1e-8` to `1e-7 m/s2` |
| symmetry residual | order `1e-8` |

The selector continues to eliminate active cap leakage and gives a coherent
inward radial tendency. The main remaining issue is not selector targeting; it
is the dynamic coupled response under raw-gradient confinement and AccInput
loading.

## Answers Required by T4

1. T4 setup: reduced CPU selected-confinement triaxial smoke with linear elastic
   skeleton, AccInput axial loading, `f_i` and lateral selectors enabled.
2. T4 `code=0`, `excluded=0`: yes, for the retained `TimeMax=0.0015 s` case.
3. `Kplastic=0`: yes, final and framewise max remain zero.
4. Measurement regions: five regions were implemented, from small center core
   to full specimen excluding caps/edges. The small core is too sparse; the
   medium/large core and Zhao-style cylinder are the most useful current
   diagnostics.
5. `p'-q` status: proxy only, not strict.
6. Pore pressure versus axial strain: numerically produced, but not stable
   enough for validation. Late sign reversal and large pressure-rate excursions
   remain.
7. Cap leakage: controlled; active cap axial leakage remains zero in the
   selected confinement diagnostics.
8. Lateral confinement: coherent and balanced in the diagnostic window.
9. Output fields: enough for proxy stress-path diagnostics, not enough for
   strict stress-path validation.
10. Recommended next step: T4b Zhao renormalized-gradient confinement and
    loading/stability refinement before T5 DP triaxial baseline. T6 MCC remains
    deferred.

