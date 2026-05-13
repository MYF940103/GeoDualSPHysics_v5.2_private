# C5q Cleanup Recommendation

Date: 2026-05-13

## Category A: Keep Stable

These interfaces should remain available and documented as useful beyond
strict Cryer.

| Interface | Reason |
|---|---|
| `SoilConstitutiveModel` | General constitutive selector for linear elastic, DP, and DP-softening behavior. Useful for T1 triaxial, 1D, and future slope work. CPU and GPU paths exist. |
| `HydraulicElevationSource` | Provides a clean CPU no-elevation pressure-diffusion convention. Cryer used it, but the concept is broader than Cryer. |
| `HydraulicGravityX/Y/Z` | General hydromechanical scaling and hydrostatic/elevation reference vector. |
| `FlexibleConfiningStress` plus `ConfiningStress*` | CPU loading candidate for confinement/triaxial-style baselines. It is not a validated Cryer final route, but it is reusable. |

These should not be removed before T1.

## Category B: Keep Experimental

These interfaces have conceptual value, are already isolated from defaults, or
support active/non-Cryer experiments.

| Interface | Reason | Guardrail |
|---|---|---|
| `PorePressureBoundaryOperator=1` | Boundary-consistent top/bottom PR operator; GPU-supported experimental path. | Keep non-default. |
| `PorePressureBoundaryOperator=2` | CPU-only hydraulic mDBC-style boundary-particle experiment from H1. | Keep non-default, CPU-only. |
| `PorePressureBoundaryOperator=3` base entry | Provides a contained curved-drained research entry point. | Keep non-default and clearly mark strict Cryer failed. |
| `PorePressureCurvedDrained` and common curved geometry/value parameters | Needed to keep archived Cryer XML readable and to leave a future research hook. | Keep experimental. |
| `CurvedDrainedBoundaryMode=0/1` | Simple ghost baselines for future audits. | Not validated for strict Cryer. |
| `CurvedDrainedBoundaryMode=4` | Boundary-particle prescribed drained state has the closest conceptual link to literature-style boundary particles. | Keep experimental; not validated, not default. |
| `CurvedDrainedBoundaryWeighting=0/1` | Raw and normalized weighting are useful diagnostics for mode `4`. | Do not advertise as validated. |

## Category C: Deprecate / Archive

These routes failed the C5 pressure-only FV gate and should not be used for new
cases without a new design review.

| Interface | Reason |
|---|---|
| `CurvedDrainedBoundaryMode=2` | Direct material clamp; diagnostic only, not a boundary value problem. |
| `CurvedDrainedBoundaryMode=3` | Material-side quadrature showed limited improvement and did not solve residuals. |
| `CurvedDrainedBoundaryMode=5` | MLS normal-gradient flux correction failed FV pressure-only gate. |
| `CurvedDrainedBoundaryMode=6` | Radial-shell boundary flux matched some global flux metrics but failed surface shell and had flux reversal. |
| `CurvedDrainedBoundaryMode=7` | Conservative shell bookkeeping worked, but dynamic diffusion gate still failed. |
| `CurvedDrainedBoundaryMode=8` | Static manufactured consistency improved, but dynamic diffusion over-drained and reversed flux. |
| `CurvedDrainedBoundaryWeighting=3` | Diagnostic capped weighting, not production. |
| `CurvedDrainedMLS*` | Mode-5-specific and no longer recommended. |
| `CurvedDrainedShell*` | Mode-7-specific and no longer recommended. |
| `CurvedDrainedCorrectedLap*` | Mode-8-specific and no longer recommended for dynamic Cryer diffusion. |
| `CurvedDrainedCorrectedLaplacianLimiter`, `CurvedDrainedLimiter*` | C5o showed limiter tuning does not pass the pressure-only FV gate. |

Deprecation here means "archived experimental failed path", not immediate
source deletion.

## Category D: Delete Now

No source interface is recommended for immediate deletion in C5q.

Reasons:

- archived C5 XML files and reports still reference the interfaces;
- deleting source before T1 would increase regression risk;
- no build or smoke run is planned in this documentation-only audit;
- failed research routes are better marked as deprecated first, then removed on
  a separate cleanup branch if desired.

## Recommendation

Adopt conservative documentation deprecation now. Do not delete mode `5-8`
source branches or parser parameters until after T1 baseline work, and only on
a dedicated source-cleanup branch with CPU Release build and targeted
regression smokes.
