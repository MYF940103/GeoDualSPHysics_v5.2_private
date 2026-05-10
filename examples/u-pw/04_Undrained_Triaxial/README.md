# 04 Undrained Triaxial

TODO scaffold for undrained triaxial tests using the u-pw PR formulation.

This is not a runnable validated reproduction yet. It is a case-readiness
placeholder used to track the loading, boundary, constitutive, and postprocessing
features required before a meaningful smoke test.

## Current Status

- Status: TODO scaffold only.
- `CaseUndrainedTriaxial_PR_TODO_Def.xml` is a placeholder.
- No GenCase or DualSPHysics run is required in the current pre-GPU pass.
- Current Drucker-Prager soil can support qualitative experiments only after
  loading/confinement controls are defined; strict paper matching may require
  Modified Cam Clay or another calibrated constitutive model.

## Missing Features

- Axial strain or axial stress control.
- Confinement / lateral stress boundary.
- Undrained boundary setup and pore-pressure output strategy.
- Stress-path postprocessing: `p'`, `q`, pore pressure, axial strain, and
  volumetric strain.
- Material-model decision: calibrated DP approximation versus MCC.

## Minimum Future Smoke Standard

A future first smoke should be tiny and short:

- `code=0`;
- `excluded=0`;
- no NaN;
- very small axial strain or stress increment;
- correct qualitative pore-pressure sign;
- stress-path CSV generated for manual inspection.
