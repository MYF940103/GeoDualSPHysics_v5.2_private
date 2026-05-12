# C4-D Hydraulic No-Elevation Report

## Objective

C4-D decouples hydraulic-conductivity scaling from hydrostatic/elevation source
terms so the future strict Cryer path can run with zero mechanical gravity and
zero hydrostatic source while retaining positive `g_h` for `k/(rho_w g_h)`.

## Implementation Summary

- Added `HydraulicElevationSource` under execution parameters.
- Default is `1`, preserving all existing self-weight/Terzaghi behavior.
- CPU `ComputeHydroPorePressRatePR()` now uses:

```text
source on : Kw/n * (-DivVel + k/(rho_w*g_h)*LapPorePress + k*LapZ)
source off: Kw/n * (-DivVel + k/(rho_w*g_h)*LapPorePress)
```

- `GetHydrostaticPorePressure()` returns zero when `HydraulicElevationSource=0`.
  This makes `ExcessPorePress == PorePress` for gravity-free Cryer.
- CPU Shepard excess mode, feedback excess mode, top/bottom corrections,
  ghost diagnostics, and curved drained mode use the same hydrostatic helper.
- GPU with `HydraulicElevationSource=0` hard-errors during XML loading.

No changes were made to `FlexibleConfiningStress`, `SoilConstitutiveModel`,
`PorePressureBoundaryOperator` modes `0/1/2`, or the PR governing equation
apart from the optional source-term switch.

## Build

- CPU Debug: passed.
- CPU Release: passed.
- GPU Release: passed; the no-elevation feature itself remains CPU-only.

## Short CPU Smokes

Location:

`examples/u-pw/03_Cryer_Problem/strict_reproduction_plan/hydraulic_no_elevation_C4D/`

| case | purpose | code | excluded | frames | key result |
|---|---|---:|---:|---:|---|
| `source_on_regression` | legacy source-on regression | 0 | 0 | 5 | old path still runs |
| `no_elevation_diffusion` | gravity-free pressure diffusion | 0 | 0 | 5 | center excess decreases from `1000 Pa` to `995.65 Pa`; used `LapZ` contribution is zero |
| `no_elevation_compression` | compression plus curved drainage | 0 | 0 | 6 | center excess rises under compression, then drains/oscillates in the short window; `Kplastic=0` |

Diagnostics:

- Raw `LapZ` remains available as a diagnostic (`maxAbs` about `67.07` in the
  sphere smokes), but `LapZ_rate_contribution_maxAbs_est=0` in the retained
  C4-D metrics for all no-elevation cases.
- The compression smoke reached `p0_eff=50 Pa`, max velocity about
  `1.10e-3 m/s`, and kept `Kplastic=0`.
- No particle exclusion or NaN/Inf was observed.

## Interpretation

The no-elevation representation is now sufficient for a coarse CPU strict-sphere
Cryer smoke: pore-pressure diffusion remains active with positive hydraulic
scaling, the elevation source is inactive, the curved drained boundary can use
`p_w=0`, and the linear-elastic skeleton remains plastic-free.

This is still not strict Cryer reproduction. Remaining limitations are:

- no analytical center-pressure comparison has been run;
- `PorePressureBoundaryOperator=3` is a first-order curved Dirichlet ghost, not
  MLS/boundary quadrature;
- `FlexibleConfiningStress` and curved drainage have only been tested in short
  CPU smokes;
- GPU support remains deferred.

## Recommendation

Proceed to C5: a coarse CPU strict-sphere smoke combining:

- `SoilConstitutiveModel=0`;
- `FlexibleConfiningStress=1`;
- `PorePressureBoundaryOperator=3`;
- `PorePressureCurvedDrained=1`;
- `HydraulicElevationSource=0`.

Do not start GPU or strict Figure 7 comparison until the coarse CPU path has
stable center-pressure extraction.
