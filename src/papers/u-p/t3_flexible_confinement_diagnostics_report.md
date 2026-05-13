# T3 Flexible Confinement Diagnostics Report

## Purpose

T3 is a CPU-only smoke and diagnostics stage for Zhao-style flexible lateral
confinement in the reduced undrained triaxial workflow. It is not a full
triaxial paper reproduction and does not use MCC.

The tested directory is:

`examples/u-pw/04_Undrained_Triaxial/experiments/T3_FlexibleConfinementDiagnostics/`

## Cases

Three short CPU Release cases were run:

| Case | Purpose | Selectors |
| --- | --- | --- |
| `CaseT3_ConfinementOnly_Legacy` | confinement-only legacy target behavior | off |
| `CaseT3_ConfinementOnly_Selected` | confinement-only Zhao-style lateral candidate | `f_i` + lateral |
| `CaseT3_AxialConfinement_Selected` | T1-style axial AccInput plus selected flexible confinement | `f_i` + lateral |

All cases use:

- `SoilConstitutiveModel=0`;
- `HydraulicElevationSource=0`;
- `PorePressureBoundaryOperator=0`;
- `FlexibleConfiningStress=1`;
- `ConfiningStressP0=50 Pa`;
- CPU Release only.

## Execution Result

| Case | DualSPHysics | Excluded | Steps | `Kplastic` max |
| --- | ---: | ---: | ---: | ---: |
| confinement-only legacy | `code=0` | `0` | `6` | `0` |
| confinement-only selected | `code=0` | `0` | `6` | `0` |
| axial + selected confinement | `code=0` | `0` | `6` | `0` |

No GPU case was run.

## Diagnostic Findings

The kernel-completeness diagnostic was stable over the short run:

| Metric | Value |
| --- | ---: |
| `f_i` min | `0.407175` |
| `f_i` mean | `0.745128` |
| `f_i` max | `1.00132` |
| computed `f_i` p05 / median / p95 | `0.45788 / 0.69129 / 0.99834` |
| `f_i <= 0.70` count | `208 / 407` |

The cylinder classification reported:

| Class | Count |
| --- | ---: |
| interior | `63` |
| lateral | `196` |
| top cap | `18` |
| bottom cap | `18` |
| edge ring | `112` |
| outside | `0` |

With selectors off, all `407` material particles receive the flexible
confinement term. With both selectors on, the active target count is `112`,
the intersection of the lateral class and `f_i <= 0.70`.

## Cap Leakage

The selector removes the measured cap axial leakage from the active confining
force:

| Case | Active targets | Mean lateral inward accel | Mean cap axial leakage |
| --- | ---: | ---: | ---: |
| legacy confinement-only | `407` | `1.49457 m/s2` | `0.93185 m/s2` |
| selected confinement-only | `112` | `1.87224 m/s2` | `0` |
| axial + selected confinement | `112` | `1.87224 m/s2` | `0` |

The net-force symmetry residual remains small, order `1e-8`, in all short
smokes. This indicates that the selected lateral shell is geometrically
balanced for the reduced cylinder.

## Pore Pressure and Axial Response

The selected confinement cases produce a strong pore-pressure response in this
very short, low-resolution free-cylinder smoke. The final center-region mean
excess pressure is about `8.61 kPa` for confinement-only selected and
`8.64 kPa` for axial plus selected confinement. The legacy confinement-only
case becomes oscillatory by the final frame, ending at about `-0.52 kPa` in
the center region.

This is useful as a plumbing and diagnostics smoke, not as validation. The
geometry is coarse, there are no platens or staged equilibration, and the
current confinement term still uses the raw kernel gradient rather than Zhao's
renormalized form.

## Figures and CSV

Generated CSV:

- `t3_confining_fi_stats.csv`
- `t3_confining_fi_particle_values.csv`
- `t3_confining_particle_classification.csv`
- `t3_confining_force_metrics.csv`
- `t3_case_summary.csv`
- `t3_pore_pressure_metrics.csv`
- `t3_kplastic_metrics.csv`

Generated figures are stored under `figures/` in both SVG and PNG formats.

## Answers to T3 Gate Questions

1. `f_i` diagnostic is implemented and logged.
2. Cylinder lateral/cap/edge/interior classification is implemented.
3. Optional `f_i` and lateral selectors are implemented.
4. Default behavior is unchanged when selectors are off.
5. The confinement-only legacy and selected smokes both passed with `code=0`,
   `excluded=0`.
6. The axial+confinement smoke passed with `code=0`, `excluded=0`.
7. The selected route reduces active cap axial leakage from about
   `0.93 m/s2` to `0`.
8. Lateral confinement response is mechanically coherent in the diagnostics:
   selected particles show inward radial acceleration and near-zero net force.
9. `Kplastic` remains `0` because the linear elastic skeleton was used.
10. GPU remains deferred.
11. MCC remains deferred.

## Recommended Next Step

Proceed to T4 as a measurement/confinement refinement step, not MCC:

- add a longer but still short CPU selected-confinement smoke with better
  measurement windows;
- improve stress-path postprocessing for `p'`, `q`, axial strain, and
  volumetric strain;
- evaluate whether Zhao-style renormalized gradient should be T4b before any
  full paper reproduction;
- keep initial hydrostatic stress as a later staged-confinement task.
