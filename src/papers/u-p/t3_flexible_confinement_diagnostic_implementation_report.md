# T3 Flexible Confinement Diagnostic Implementation Report

## Objective

T3 implements CPU-only diagnostics and opt-in selectors for the existing
`FlexibleConfiningStress` pair term. The goal is to make Zhao-style flexible
triaxial confinement measurable before attempting strict paper reproduction,
MCC, initial hydrostatic stress, or GPU support.

Defaults are unchanged: `FlexibleConfiningStress=1` with no new selector flags
continues to apply the legacy confining stress term to every target material
particle selected by `ConfiningStressTargetMk`.

## Implemented Interfaces

New diagnostic controls:

- `FlexibleConfiningStressFiDiagnostic`: compute and log Zhao-style kernel
  completeness index `f_i = sum_j (m_j / rho_j) W_ij`.
- `ConfiningStressFiThreshold`: default `0.70`, matching the 3D threshold
  candidate discussed in the Zhao audit.
- `SaveConfiningStressDiagnostics`: print extended confinement diagnostics.

New cylinder geometry controls:

- `ConfiningStressGeometry=1`: enable cylinder classification.
- `ConfiningStressCylinderCenterX/Y/Z`.
- `ConfiningStressCylinderAxisX/Y/Z`.
- `ConfiningStressCylinderRadius`.
- `ConfiningStressCylinderHeight`.
- `ConfiningStressCapExclusionLength`.
- `ConfiningStressEdgeExclusionLength`.

New opt-in selectors:

- `ConfiningStressUseFiSelector=1`: confining term applies only to particles
  with `f_i <= ConfiningStressFiThreshold`.
- `ConfiningStressUseLateralSelector=1`: confining term applies only to
  particles classified as cylinder lateral surface candidates.
- If both selectors are on, the active target set is their intersection.

## Diagnostics

The CPU force loop now logs:

- legacy target count;
- active selected target count;
- `f_i` min, max, mean, and threshold-selected count;
- cylinder class counts: interior, lateral, top, bottom, edge, outside;
- lateral particles below the `f_i` threshold;
- cap/edge particles below the `f_i` threshold;
- net confining force vector;
- total absolute confining force;
- maximum confining acceleration;
- center-of-mass acceleration estimate;
- symmetry residual;
- lateral inward radial acceleration mean/max;
- cap axial acceleration leakage mean/max.

The T3 postprocessor extracts these logs into:

- `t3_confining_fi_stats.csv`;
- `t3_confining_particle_classification.csv`;
- `t3_confining_force_metrics.csv`;
- `t3_confining_fi_particle_values.csv`;
- `t3_case_summary.csv`;
- `t3_pore_pressure_metrics.csv`;
- `t3_kplastic_metrics.csv`.

## Source Scope

Only the CPU `FlexibleConfiningStress` path was changed. The PR pore-pressure
equation, constitutive model selection, `HydraulicElevationSource`, Cryer
boundary modes, and deprecated Cryer experimental modes remain untouched.

The implementation still uses the current raw kernel gradient in the existing
momentum pair loop. It does not implement Zhao's renormalized gradient, the
large-deformation `l0/ln` rescaling, initial hydrostatic stress assignment,
MCC, or GPU support.

## GPU Status

`FlexibleConfiningStress=1` remains CPU-only. GPU execution still hard-errors
when flexible confinement is enabled. This is intentional until the CPU
diagnostics and selectors are stable.

## Build

CPU Release was rebuilt successfully after the source changes:

```text
msbuild .\VS\DualSPHysics5ReCpu_vs2022.sln /m /t:Build /p:Configuration=ReleaseCPU /p:Platform=x64 /v:minimal
```

The first run exposed a stack-overflow caused by large per-thread diagnostic
arrays allocated on the interaction-loop stack. The arrays were replaced by a
heap-backed per-thread diagnostic struct; the numerical force logic was not
changed.

## Remaining Gaps vs Zhao

- Kernel gradient is not renormalized.
- `f_i` is diagnostic/selector infrastructure only, not a full Zhao boundary
  formulation proof.
- Cylinder selection is geometric and does not yet adapt to large deformation.
- No initial hydrostatic confining stress route exists.
- No staged isotropic-confinement equilibration exists.
- MCC remains deferred.
