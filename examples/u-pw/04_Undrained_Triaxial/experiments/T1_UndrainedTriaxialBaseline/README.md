# T1 Undrained Triaxial Baseline

This directory contains the T1 reduced undrained triaxial-style CPU baseline.
It is a short smoke, not a full paper reproduction.

Key choices:

- `SoilConstitutiveModel=0` linear elastic skeleton;
- native DualSPHysics `accinput` on top `mkfluid=1` for reduced axial loading;
- no strict triaxial confining stress control;
- `PorePressureBoundaryOperator=0`;
- `HydraulicElevationSource=0` for gravity-free pressure diffusion;
- CPU Release only, because `HydraulicElevationSource=0` is GPU unsupported in
  this branch.

Run:

```bat
xCaseUndrainedTriaxial_PR_T1_Baseline_win64_CPU_release.bat
```

Postprocess:

```bat
py -3 scripts\analyze_t1_undrained_triaxial.py --data CaseUndrainedTriaxial_PR_T1_Baseline_out\data --outdir .
```
