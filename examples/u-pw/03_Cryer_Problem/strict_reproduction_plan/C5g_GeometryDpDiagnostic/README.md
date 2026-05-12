# C5g Geometry / dp Diagnostic

This folder contains a modest one-level sphere-resolution diagnostic for the
CPU-only strict Cryer smoke path.

It does not claim Figure 7B reproduction. It tests whether the coarse C5f
filled sphere is a major cause of the high center pressure and persistent
surface residual.

## Cases

- `CaseCryer_PR_StrictSphere_C5g_CoarseCompressionNormalized_Def.xml`
- `CaseCryer_PR_StrictSphere_C5g_FinerCompressionNormalized_Def.xml`
- `CaseCryer_PR_StrictSphere_C5g_CoarseDiffusionNormalized_Def.xml`
- `CaseCryer_PR_StrictSphere_C5g_FinerDiffusionNormalized_Def.xml`

The coarse cases use `Dp=0.01 m`. The finer cases use `Dp=0.008 m` while
keeping radius, p0, ramp, material parameters, and boundary settings unchanged.

Common strict-smoke settings:

- `SoilConstitutiveModel=0`
- `PorePressureBoundaryOperator=3`
- `PorePressureCurvedDrained=1`
- `CurvedDrainedBoundaryMode=4`
- `CurvedDrainedBoundaryWeighting=1`
- `HydraulicElevationSource=0`
- CPU Release only

## Run

```bat
xCaseCryer_PR_StrictSphere_C5g_GeometryDpDiagnostic_win64_CPU_release.bat
```

The BAT runs GenCase, CPU Release, PartVTK, and the C5g analysis script for all
four cases.

Heavy raw output should be cleaned before commit. Retain XML/BAT, scripts,
CSV, figures, and this README.
