# Notes: Self-Weight Consolidation

## Current implementation status

The CPU PR prototype now has the pieces needed for short self-weight smoke tests:

- `PorePress` restart is implemented and should be used for Scenario 1 Stage B.
- `BodyGravityStopTime` is available as an alternative in-run route, but the formal Scenario 1 scaffold uses restart because it mirrors the Supporting Information staged workflow more explicitly.
- `HydraulicGravity` is independent of body gravity and remains active when Stage B sets body Gravity to zero.
- `PorePressureFeedbackMode=1` and `PorePressureFeedbackOperator=1` are the recommended coupled settings for self-weight/Terzaghi-style tests.
- `PorePressureShepardMode=1` and `HydromechDampingXi` are the recommended stabilization controls for smoke tests.

## Scenario 1 workflow

Stage A:

- body Gravity = `(0,0,-9.81)`;
- HydraulicGravity = `(0,0,-9.81)`;
- hydrostatic initialization with `PorePressureInit=1`;
- top drainage inactive during the undrained generation window;
- bottom no-flux active;
- `SavePorePressure=1` so Stage B can restore `PorePress` from PART output.

Stage B:

- restart from the Stage A final PART file;
- body Gravity = `(0,0,0)`;
- HydraulicGravity = `(0,0,-9.81)`;
- top drained active from the start of Stage B;
- bottom no-flux active;
- restart `PorePress` wins over XML initialization.

Expected short-window trend: the Stage A self-weight excess pressure is positive; Stage B begins dissipating excess pressure while avoiding a restart discontinuity.

## Scenario 2 workflow

Scenario 2 keeps body gravity on after the undrained stage. Top drainage activates after the prescribed undrained time, and total pore pressure should trend toward the hydrostatic profile.

## Diagnostic boundaries and operators

Boundary ghost diagnostics and corrected-gradient diagnostics are intentionally not used by the production PR operator:

- CPU-BG3 showed the simple ghost Laplacian did not improve bottom hydrostatic consistency.
- CPU-CG1 showed material-only corrected-gradient diagnostics did not outperform the current production operator in the tested smoke cases.

They remain diagnostics/research paths only. Production smoke tests should continue using the current material-only PR path plus layer top-drained/bottom-no-flux corrections.

## CPU/GPU policy

Do not use this directory for long CPU parameter sweeps. The CPU target is smoke readiness only:

- `code=0`;
- `excluded=0`;
- no NaN;
- key hydromech fields written;
- qualitative pore-pressure trend correct.

Long-time sensitivity and strict figure reproduction should wait for the GPU port.

## Latest Smoke Notes

- Scenario 1 Stage A completed with `code=0`, `excluded=0`.
- Scenario 1 Stage B completed with `code=0`, `excluded=0`.
- Stage B restart log confirmed restored soil stress state and restored
  `PorePress` for `1040/1040` particles using Idp mapping.
- Stage B log confirmed XML `PorePressureInit` was skipped after restoring
  restart pore pressure.
- Scenario 2 short smoke completed with `code=0`, `excluded=0`.
- All smoke outputs were removed after status collection.

Keep these runs as readiness checks only. Do not extend them into CPU
long-time tuning during the pre-GPU pass.
