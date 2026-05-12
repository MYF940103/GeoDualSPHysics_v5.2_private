# C5h Higher-Resolution Sphere Diagnostic

This directory contains a CPU-only higher-resolution sphere diagnostic for the
strict Cryer route. It does not modify source code, does not run GPU, and does
not claim Figure 7B quantitative reproduction.

The setup repeats the C5g normalized mode-4 boundary-particle drained case with
one additional sphere resolution:

- C5g coarse context: `dp=0.010`
- C5g finer context: `dp=0.008`
- C5h higher-resolution run: `dp=0.0065`

Physical settings are unchanged from the C5g normalized baseline:

- `SoilConstitutiveModel=0`
- `FlexibleConfiningStress=1`, `ConfiningStressP0=50 Pa` for compression
- `HydraulicElevationSource=0`
- `PorePressureBoundaryOperator=3`
- `PorePressureCurvedDrained=1`
- `CurvedDrainedBoundaryMode=4`
- `CurvedDrainedBoundaryWeighting=1`
- CPU Release only

Run manually from this directory:

```bat
xCaseCryer_PR_StrictSphere_C5h_HigherResolutionSphere_win64_CPU_release.bat
```

The BAT runs:

1. GenCase
2. DualSPHysics CPU Release
3. PartVTK
4. `scripts/analyze_c5h_higher_resolution_sphere.py`

The analysis script reads the C5h higher-resolution outputs and merges them
with retained C5g CSVs for coarse/finer comparison. Heavy solver output
directories are intentionally not retained after the committed diagnostic.
