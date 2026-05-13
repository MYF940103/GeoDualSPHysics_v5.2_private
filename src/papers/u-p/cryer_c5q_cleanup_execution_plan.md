# C5q Cleanup Execution Plan

Date: 2026-05-13

## Plan 1: Conservative Cleanup

Plan 1 makes no source deletions. It only updates documentation and parameter
references.

Actions:

- keep production defaults unchanged;
- keep `PorePressureBoundaryOperator=0` as the production default;
- keep `SoilConstitutiveModel`, `HydraulicElevationSource`, and
  `FlexibleConfiningStress` documented as stable or stable-experimental
  infrastructure;
- mark `CurvedDrainedBoundaryMode=5/6/7/8` and their parameters as archived
  failed Cryer research paths;
- mark mode `4` as experimental boundary-particle research, not validated;
- state that no C6 Figure 7B comparison should start without a new boundary
  formulation and a passing pressure-only spherical FV diffusion gate.

Advantages:

- no compile risk before T1;
- archived C5 XML cases and reports remain readable;
- future source cleanup can still happen on a focused branch;
- avoids mixing cleanup churn with the next benchmark setup.

Disadvantages:

- source still contains failed experimental branches;
- parser help remains broad unless later source warnings are added.

Build/test requirement:

- no build required if only documentation is changed.

## Plan 2: Source Cleanup

Plan 2 removes failed Cryer source paths.

Possible actions:

- remove `CurvedDrainedBoundaryMode=5/6/7/8` branches from
  `source/JSphCpu.cpp`;
- remove mode-5 MLS, mode-7 shell, mode-8 corrected-Laplacian, and limiter
  parser/storage fields;
- keep `CurvedDrainedBoundaryMode=0/1/2/3/4` if desired;
- update XML documentation and archived notes to state that old C5 XML files
  require the historical branch;
- run CPU Release build;
- run targeted PR regression smokes for non-Cryer examples;
- run GPU Release build if shared parser or GPU-visible configuration changed.

Advantages:

- smaller interface surface;
- less temptation to use failed modes in new cases;
- less maintenance burden later.

Risks:

- archived C5 XML cases would no longer run on the current branch;
- source deletion could accidentally affect common parsing/logging;
- doing this before T1 could delay the recommended next benchmark;
- GPU hard-error and parser paths would need careful retesting.

## Recommended Plan

Use Plan 1 now.

Plan 1 matches the C5p no-go decision: freeze strict Cryer, document the
failed interfaces clearly, and move to T1 without risky source churn. Plan 2
can be considered after T1, preferably as a separate cleanup branch with a
build and regression matrix.

## Optional Future Source Guard

A later small source change could print a warning when
`CurvedDrainedBoundaryMode=5/6/7/8` is enabled:

```text
This Cryer experimental boundary mode did not pass the pressure-only FV gate
and is not recommended for new cases.
```

C5q does not add this warning because the current task is audit-first and
documentation-only. Adding the warning should be paired with a CPU Release
build.
