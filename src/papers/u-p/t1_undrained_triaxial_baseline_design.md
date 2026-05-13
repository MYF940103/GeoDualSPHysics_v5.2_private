# T1 Undrained Triaxial Baseline Design

Date: 2026-05-13

## Positioning

T1 is a reduced undrained triaxial-style compression smoke. It is not a full
paper reproduction and it is not a strict theoretical stress-path comparison.

The goal is narrower: verify that the current u-pw PR framework can complete a
short triaxial-style loading workflow and produce finite pore-pressure, stress,
velocity, and plasticity diagnostics.

## Constitutive Choice

T1 uses:

```text
SoilConstitutiveModel=0
```

Rationale:

- the immediate goal is u-pw pore-pressure response plumbing, not DP yield
  calibration;
- linear elasticity should keep `Kplastic=0`, giving a clean health check;
- DP elastoplastic stress-path validation should be a separate T2 step;
- DP softening and MCC are out of scope.

## Hydraulic Choice

T1 uses:

```text
HydromechCoupling=1
PorePressureModel=1
PorePressureBoundaryOperator=0
HydraulicElevationSource=0
HydraulicGravity=(0,0,-9.81)
PorePressureInit=0
PorePressureFeedback=1
PorePressureFeedbackMode=1
PorePressureFeedbackOperator=1
PorePressureShepard=1
PorePressureShepardInterval=10
PorePressureShepardMode=1
PorePressureDtSafety=0.20
```

`HydraulicElevationSource=0` makes the smoke gravity-free: hydraulic gravity
provides scaling magnitude only, hydrostatic pressure is zero, and the `LapZ`
source is omitted from `PorePressRate`. This also means GPU is deferred for T1
because `HydraulicElevationSource=0` is CPU-only in the current branch.

## Loading and Confinement

T1 uses the existing native AccInput mechanism:

- `mkfluid=1` top material layer;
- `TriaxialAxialAcc_T1.csv`;
- final axial acceleration `-0.5 m/s2` over `0.001 s`.

This is a reduced axial loading smoke. It is not strict triaxial loading:

- no true lateral confining pressure is imposed;
- no controlled axial strain boundary is implemented;
- fixed/mDBC side and bottom support provide only reduced confinement;
- `FlexibleConfiningStress` is not used in T1.

## Baseline Directory

T1 is retained under:

```text
examples/u-pw/04_Undrained_Triaxial/experiments/T1_UndrainedTriaxialBaseline/
```

Key files:

- `CaseUndrainedTriaxial_PR_T1_Baseline_Def.xml`;
- `TriaxialAxialAcc_T1.csv`;
- `xCaseUndrainedTriaxial_PR_T1_Baseline_win64_CPU_release.bat`;
- `scripts/analyze_t1_undrained_triaxial.py`.

## Success Gate

T1 passes as a baseline smoke if:

- GenCase returns `code=0`;
- DualSPHysics CPU Release returns `code=0`;
- PartVTK returns `code=0`;
- excluded particles are zero;
- no NaN/Inf appears in the postprocessed fields;
- `PorePress`/`ExcessPorePress` are exported and respond to loading;
- `Kplastic=0`;
- stress-path proxies are exported for future T2 work.

T1 does not require matching a paper p-q curve.
