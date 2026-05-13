# T1 Triaxial Case Audit

Date: 2026-05-13

## Scope

This audit inspected the existing `examples/u-pw/04_Undrained_Triaxial/`
scaffold before creating the T1 baseline. No source code was modified.

## Current Scaffold State

The directory already contained a reduced triaxial smoke scaffold:

- `CaseUndrainedTriaxial_PR_Smoke_Def.xml`;
- `xCaseUndrainedTriaxial_PR_Smoke_win64_CPU_debug.bat`;
- `TriaxialAxialAcc_m1.csv`;
- `analyze_triaxial_smoke.py`;
- `triaxial_smoke_summary.csv`;
- `README.md`, `notes.md`, and `smoke_status.md`.

It is not a full paper reproduction. It is a small 2D column-style u-pw PR
plumbing smoke.

## Runnable Status

The existing scaffold is runnable according to its recorded smoke status:

- GenCase `code=0`;
- DualSPHysics CPU Release `code=0`;
- `excluded=0`;
- pore-pressure and stress fields exported;
- no NaN/Inf detected in the recorded CSV audit.

The existing BAT is named CPU debug but the recorded status says the tested
solver path was CPU Release. T1 therefore creates a fresh CPU Release launcher
inside a dedicated experiment directory.

## Loading Route

The current scaffold uses native DualSPHysics `accinput` on the top material
layer:

- top material layer: `mkfluid=1`;
- existing acceleration file: `TriaxialAxialAcc_m1.csv`;
- existing final axial acceleration: `-0.047619 m/s2`;
- loading is intentionally tiny and only exercises the coupled-field plumbing.

There is no controlled axial strain or stress boundary condition.

## Confinement Route

The current scaffold has fixed/mDBC side and bottom boundaries. It does not
implement true flexible lateral triaxial confinement or prescribed confining
pressure. `FlexibleConfiningStress` is not used in the existing smoke.

## Soil Model

The existing smoke XML does not set `SoilConstitutiveModel`, so the parser
falls back to the Drucker-Prager path (`SoilConstitutiveModel=1`) because
legacy `Softening` is absent. This is useful for an early DP plumbing smoke but
is not ideal for the first T1 u-pw pore-pressure response baseline.

## Output Fields

The recorded `PartCsv` output included:

- `PorePress`;
- `ExcessPorePress`;
- `PorePressRate`;
- `DivVel`;
- `LapPorePress`;
- `LapZ`;
- corrected-gradient diagnostic fields;
- `PorePressureAccel`;
- `PorePressureAccelDiff`;
- stress tensor components;
- `Kplastic`.

The existing `analyze_triaxial_smoke.py` computes approximate `p'`, `q`,
pore pressure, velocity, and axial-strain proxy metrics.

## Missing for Baseline

For a cleaner T1 baseline, the scaffold needed:

- a dedicated experiment directory;
- explicit `SoilConstitutiveModel=0` for the first poroelastic response smoke;
- explicit `PorePressureBoundaryOperator=0`;
- gravity-free `HydraulicElevationSource=0` if CPU-only is accepted;
- a CPU Release BAT with GenCase, DualSPHysics, and PartVTK;
- a postprocessor that writes frame metrics, measurement-region metrics,
  pore-pressure metrics, stress-path proxy metrics, figures, and case summary.

## Audit Answers

1. The scaffold is a reduced triaxial-style u-pw PR smoke, not a strict
   reproduction.
2. It is runnable and previously passed a short CPU smoke.
3. Loading uses native `accinput` on a top material layer.
4. There is no true confining pressure; lateral confinement is reduced/fixed
   boundary support.
5. Axial compression exists as top-layer acceleration, not prescribed strain.
6. The existing smoke defaults to DP; T1 changes the first baseline to linear
   elastic.
7. Pore pressure, excess pressure, stress, velocity, and `Kplastic` are
   exported.
8. A dedicated linear-elastic CPU Release baseline and updated postprocessing
   were needed.
