# Experimental Interface Registry

Date: 2026-05-14

This registry is documentation-only. It records the u-pw experimental XML and
source interfaces that accumulated during the Cryer, triaxial, MCC, 1D
consolidation, boundary, and time-integration investigations. No source code,
simulation output, or build artifact was changed for this registry.

Status labels follow `experimental_interface_cleanup_policy.md`:

- `[PRODUCTION]`: stable enough for new cases when documented constraints are
  met.
- `[ACTIVE_EXPERIMENTAL]`: still under evaluation; not allowed as a default.
- `[DEPRECATED]`: retained only for old experiment reproducibility.
- `[DELETE_CANDIDATE]`: should be removed in a cleanup branch unless a user
  explicitly needs old-case replay.
- `[CPU_ONLY]`: implemented only on CPU.
- `[GPU_DEFERRED]`: GPU parity is future work.
- `[GPU_HARD_ERROR]`: XML loading must fail on GPU when enabled.

## Pore-Pressure Boundary Interfaces

| Interface | Purpose | Introduced / used in | Status | CPU support | GPU support | Validation status | Recommended usage | Cleanup action |
|---|---|---|---|---|---|---|---|---|
| `PorePressureBoundaryOperator=0` | Legacy material-only PR operator plus layer projections. | Original PR path, L3c/L4 reference. | `[PRODUCTION]` | Yes | Yes | Stable for L3c/L4 Level-1 diffusion gate. | Use for conservative regression and paper-compatible diffusion figures. | Keep. |
| `PorePressureBoundaryOperator=1` | Virtual top drained / bottom no-flux boundary contribution. | B1/B5, L5 feedback gate. | `[ACTIVE_EXPERIMENTAL]` | Yes | Yes | Stable in L5 feedback-on gate; not default. | Current recommended feedback-on 1D gate operator. | Promote only after TINT2 and broader wall checks. |
| `PorePressureBoundaryOperator=2` | Boundary-particle hydraulic state / generalized solid-wall no-flux prototype. | H1, BND1. | `[ACTIVE_EXPERIMENTAL] [CPU_ONLY] [GPU_HARD_ERROR]` | Yes | Hard error | BND1 feedback-off runs but worse than mode 1; feedback-on unstable. | Do not use for landslide or default until TINT/BND follow-up. | Reassess after TINT2; otherwise deprecate. |
| `PorePressureBoundaryOperator=3` | Curved drained boundary entry point. | Cryer C4-C through C5q. | `[DEPRECATED] [CPU_ONLY] [GPU_HARD_ERROR]` | Yes | Hard error | Multiple Cryer modes failed strict drained-boundary gates. | Reproduce old Cryer experiments only. | Archive; cleanup branch should remove failed submodes first. |
| `PorePressureCurvedDrained` | Enables curved drained boundary path under operator 3. | Cryer strict boundary work. | `[DEPRECATED] [CPU_ONLY]` | Yes | Hard error through operator 3 | Not strict validated. | Old Cryer replay only. | Archive with operator 3. |
| `CurvedDrainedBoundaryCenterX/Y/Z`, `CurvedDrainedBoundaryRadius`, `CurvedDrainedBoundaryTargetMk`, `CurvedDrainedBoundaryValue`, `CurvedDrainedBoundaryUseExcess`, `CurvedDrainedBoundaryThickness` | Geometry/value definition for curved drained tests. | Cryer C4-C to C5q. | `[DEPRECATED] [CPU_ONLY]` | Yes | Hard error through operator 3 | Needed only for old Cryer diagnostics. | Do not use in new cases. | Keep only until Cryer archive policy is decided. |
| `CurvedDrainedBoundaryMode=0/1` | First-order / strengthened spherical Dirichlet ghost. | Cryer C4/C5. | `[DEPRECATED]` | Yes | No | Simple baselines; not strict. | Old replay only. | Candidate for archive. |
| `CurvedDrainedBoundaryMode=2` | Diagnostic material clamp after pressure update. | Cryer C4/C5. | `[DELETE_CANDIDATE]` | Yes | No | Diagnostic-only; not a boundary operator. | Do not use. | Delete after old XML archive. |
| `CurvedDrainedBoundaryMode=3` | Multi-sample material-side boundary quadrature. | Cryer C5. | `[DEPRECATED]` | Yes | No | Did not solve surface residual. | Do not use in new cases. | Archive/delete candidate. |
| `CurvedDrainedBoundaryMode=4`, `CurvedDrainedBoundaryTargetMkBound`, `CurvedDrainedBoundaryUseBoundaryParticles`, `CurvedDrainedBoundarySelectionTolerance`, `CurvedDrainedBoundaryAdamiDiagnostic`, `CurvedDrainedBoundaryWeighting` | Boundary-particle prescribed drained state and diagnostics. | Cryer C5e/C5f. | `[DEPRECATED] [CPU_ONLY]` | Yes | No | Conceptually useful but not validated. | Old Cryer replay only unless restarted as a fresh boundary project. | Archive; do not promote. |
| `CurvedDrainedBoundaryMode=5/6/7/8`, `CurvedDrainedMLS*`, `CurvedDrainedShell*`, `CurvedDrainedCorrectedLap*`, `CurvedDrainedLimiter*` | MLS, radial-shell, conservative-shell, and corrected-Laplacian attempts. | Cryer C5j-C5o. | `[DELETE_CANDIDATE] [CPU_ONLY]` | Yes | No | Failed or inconclusive boundary gates. | Do not use. | Delete in cleanup branch after old results are archived. |

## Feedback Interfaces

| Interface | Purpose | Introduced / used in | Status | CPU support | GPU support | Validation status | Recommended usage | Cleanup action |
|---|---|---|---|---|---|---|---|---|
| `PorePressureFeedback` | Enables pore-pressure acceleration feedback. | Core u-pw coupling path. | `[ACTIVE_EXPERIMENTAL]` | Yes | Yes for operator 1 route | L5 1D gate stable; not strict Terzaghi reproduction. | Use only with documented mode/operator and diagnostics. | Keep active; promote only after more coupled gates. |
| `PorePressureFeedbackMode=1` | Use excess pressure rather than total pressure for feedback. | Self-weight, triaxial, L5. | `[ACTIVE_EXPERIMENTAL]` | Yes | Yes | Current recommended feedback convention. | Prefer for self-weight/L5-style tests. | Candidate promote after landslide reduced baseline. |
| `PorePressureFeedbackOperator=0` | Legacy symmetric stress-style feedback. | Early u-pw path. | `[DEPRECATED]` | Yes | Partial/legacy | Known constant-pressure/boundary artifacts. | Do not use for new validation. | Archive; consider delete after operator 1 is promoted. |
| `PorePressureFeedbackOperator=1` | Difference-gradient feedback. | B5, self-weight, L5. | `[ACTIVE_EXPERIMENTAL]` | Yes | Yes | Stable in L5 CPU/GPU target-amplitude gate. | Current recommended feedback-on route. | Keep active; candidate production after TINT2 and landslide reduced gate. |
| `PorePressureFeedbackOperator=2`, `PorePressureFeedbackLSQ*` | CPU LSQ pressure-gradient feedback. | Triaxial feedback diagnostics. | `[DEPRECATED] [CPU_ONLY] [GPU_HARD_ERROR]` | Yes | Hard error | Not selected as recommended route. | Avoid new cases. | Archive/delete candidate. |
| `PorePressureFeedbackOperator=3` | CPU paper-style stress-pair pressure momentum prototype. | Triaxial feedback diagnostics. | `[DEPRECATED] [CPU_ONLY] [GPU_HARD_ERROR]` | Yes | Hard error | Did not become stable validation route. | Avoid new cases. | Archive/delete candidate. |
| `PorePressureFeedbackStartTime`, `PorePressureFeedbackRampEndTime`, `PorePressureFeedbackScale` | Staged feedback ramp/scale. | T5 triaxial feedback audits. | `[DEPRECATED]` | Yes | Limited/mostly CPU path | Helpful diagnostics; not recommended to tune validation. | Old triaxial replay only. | Archive unless needed for one explicit staged test. |
| `PorePressureFeedbackRelaxation`, `PorePressureFeedbackMaxAccel`, `PorePressureFeedbackMaxAccelRatio`, `PorePressureFeedbackLimiterMode` | Feedback limiter/relaxation experiments. | T5 triaxial stabilization attempts. | `[DELETE_CANDIDATE]` | Yes | Mostly unsupported/deferred | Did not produce strict validation route. | Do not use to mask instability. | Delete after old XML archive. |
| `SavePorePressureFeedbackDiagnostics`, `PorePressureFeedbackDiagInterval` | Feedback diagnostic logging. | T5, L5. | `[ACTIVE_EXPERIMENTAL]` | Yes | Partial | Useful for gates. | Prefer diagnostics over new XML modes. | Keep while feedback is active experimental. |
| `PorePressureFeedbackUseClassFilter`, `PorePressureFeedbackExcludeCaps`, `PorePressureFeedbackExcludeEdges`, `PorePressureFeedbackExcludeConfinementTargets`, `PorePressureFeedbackInteriorOnly` | Triaxial geometry/class feedback filters. | T5 triaxial diagnostics. | `[DELETE_CANDIDATE] [CPU_ONLY]` | Yes | No | Did not lead to clean route. | Do not use in new cases. | Delete/archive with old triaxial feedback experiments. |

## Confinement and Triaxial Interfaces

| Interface | Purpose | Introduced / used in | Status | CPU support | GPU support | Validation status | Recommended usage | Cleanup action |
|---|---|---|---|---|---|---|---|---|
| `FlexibleConfiningStress`, `ConfiningStressP0`, `ConfiningStressRampStart`, `ConfiningStressRampEnd`, `ConfiningStressTargetMk`, `ConfiningStressMode` | Reduced flexible confinement for Cryer/triaxial diagnostics. | C4, T4/T5, MCC platen route. | `[ACTIVE_EXPERIMENTAL] [CPU_ONLY] [GPU_HARD_ERROR]` | Yes | Hard error | Useful reduced route; not strict actuator/traction reproduction. | Allowed only in documented reduced cases. | Keep active until replaced by a production boundary route. |
| `ConfiningStressGradientMode` | Corrected-gradient confinement pair term. | T4b/T4s diagnostics. | `[DEPRECATED] [CPU_ONLY]` | Yes | Hard error | Not central to current route. | Avoid new cases unless reproducing T4. | Archive. |
| `FlexibleConfiningStressFiDiagnostic`, `ConfiningStressFiThreshold`, `SaveConfiningStressDiagnostics`, `ConfiningStressGeometry`, `ConfiningStressCylinder*`, `ConfiningStressCapExclusionLength`, `ConfiningStressEdgeExclusionLength` | Geometry/support diagnostics and target classification. | T4/T5/MCC boundary audits. | `[ACTIVE_EXPERIMENTAL] [CPU_ONLY]` | Yes | Mostly deferred | Useful for reduced triaxial reporting. | Diagnostics only. | Keep until triaxial package is archived. |
| `ConfiningStressUseFiSelector`, `ConfiningStressUseLateralSelector`, `ConfiningStressLateralSelectorStartTime` | Selector/staging for lateral confinement targets. | T4n/T5. | `[DEPRECATED] [CPU_ONLY]` | Yes | Hard error for staged non-default | Reduced route only. | Avoid new validation. | Archive. |
| `CapConfiningStress*`, `SaveCapConfiningStressDiagnostics` | Cap-normal acceleration support diagnostic. | T4o/T4p. | `[DELETE_CANDIDATE] [CPU_ONLY]` | Yes | Hard error | Explicit acceleration patch failed as production route. | Do not use. | Delete after old reports are archived. |
| `SavePlatenReactionDiagnostics`, `PlatenTopMkBound`, `PlatenBottomMkBound`, `PlatenReactionMode`, `PlatenReactionArea`, `PlatenReactionInterval` | Pairwise platen reaction diagnostic. | T4t/T5/MCC feedback-off workflow. | `[ACTIVE_EXPERIMENTAL] [CPU_ONLY]` | Yes | No | Useful diagnostic, but not true actuator reaction. | Allowed for reduced platen reports with caveat. | Keep until actuator reaction is implemented. |

## Modified Cam Clay Interfaces

| Interface | Purpose | Introduced / used in | Status | CPU support | GPU support | Validation status | Recommended usage | Cleanup action |
|---|---|---|---|---|---|---|---|---|
| `SoilConstitutiveModel=3` | CPU Modified Cam Clay branch. | M3b/M3c. | `[ACTIVE_EXPERIMENTAL] [CPU_ONLY] [GPU_HARD_ERROR]` | Yes | Hard error | High-pc elastic-like and mild-yield reduced smokes pass; clean validation deferred. | Internal diagnostics / reduced DP-MCC comparison only. | Keep active; do not make paper-validation claim. |
| `MccLambda`, `MccKappa`, `MccM`, `MccInitialVoidRatio`, `MccInitialSpecificVolume`, `MccInitialPreconsolidationPressure`, `MccOCR`, `MccReferencePressure`, `MccTensionCutoff`, `MccReturnTolerance`, `MccReturnMaxIter`, `MccStressUpdateEnabled` | Core MCC material parameters and parser controls. | M3b/M3c. | `[ACTIVE_EXPERIMENTAL] [CPU_ONLY]` | Yes | Hard error through model 3 | Material-point parity passed; SPH reduced route caveated. | Use only in MCC CPU reduced experiments. | Keep until MCC route is retired or promoted. |
| `SaveMccState` | Outputs MCC state and return diagnostics. | M3b onward. | `[ACTIVE_EXPERIMENTAL] [CPU_ONLY]` | Yes | No | Required for MCC audits. | Enable for all MCC reduced cases. | Keep while MCC active. |
| `MccSubstepping`, `MccMaxSubsteps`, `MccSubstepMode`, `MccSubstepStrainThreshold`, `MccSubstepYieldDistanceThreshold`, `MccMinSubsteps` | MCC local substepping robustness experiments. | M3d3/M3f. | `[DEPRECATED] [CPU_ONLY]` | Yes | No | Did not clean original-rate platen route. | Avoid as new validation route. | Archive/delete candidate after MCC reports freeze. |
| `MccAdmissibilityGuard`, `MccFailureFallback` | Guard/fallback for MCC return failures. | M3d3. | `[DEPRECATED] [CPU_ONLY]` | Yes | No | Fallback is safety only, not validation. | Do not use fallback for clean validation. | Candidate delete unless needed for crash safety. |
| `MccAdmissibleLineSearch`, `MccLineSearchMaxBacktrack`, `MccLineSearchMinStep`, `MccLineSearchResidualReduction`, `MccEnforcePositivePlasticMultiplier`, `MccAdmissibleProjection` | Admissible Newton / line-search controls. | M3h. | `[DEPRECATED] [CPU_ONLY]` | Yes | No | Did not solve boundary-induced return failures. | Avoid new mode tuning. | Archive/delete candidate after MCC package freeze. |

## 1D Consolidation and Loading Interfaces

| Interface | Purpose | Introduced / used in | Status | CPU support | GPU support | Validation status | Recommended usage | Cleanup action |
|---|---|---|---|---|---|---|---|---|
| `PorePressureInit=0/1` | Zero/hydrostatic pore-pressure initialization. | Core PR path. | `[PRODUCTION]` | Yes | Yes | Used broadly. | Keep. | Keep. |
| `PorePressureInit=2` | From-file placeholder. | Early placeholder. | `[DELETE_CANDIDATE]` | Placeholder | Placeholder | Not implemented. | Do not use. | Turn into hard error or delete. |
| `PorePressureInit=3`, `PorePressureExcessAmp`, `PorePressureAnalyticalProfile` | Hydrostatic plus analytical initial excess pressure. | L3a/L3c/L4/L5. | `[PRODUCTION]` for Level-1 diffusion gates | Yes | Yes | Best current 1D PR diffusion/boundary validation route. | Use for L3c/L4/L5-style gates. | Keep. |
| `InitialStressMode`, `InitialEffectiveStressIso`, `InitialEffectiveStressTargetMk` | Initial effective-stress initializer. | C4, L3c audit, triaxial/MCC smokes. | `[ACTIVE_EXPERIMENTAL] [CPU_ONLY] [GPU_HARD_ERROR]` | Yes | Hard error | Isotropic only; not vertical surcharge/total-stress initializer. | Use only when isotropic compression is intended. | Keep active until L5b decides stress-initializer direction. |
| `MechanicalTopLoad*`, `SaveMechanicalTopLoadDiagnostics` | CPU direct top material surface force. | L3b. | `[DEPRECATED] [CPU_ONLY] [GPU_HARD_ERROR]` | Yes | Hard error | Stable but generated unrealistic dynamic pressure peak. | Do not use as strict Terzaghi route. | Archive; candidate delete after L3d route chosen. |
| Future `PorePressureTimeIntegrationMode` | TINT2 pressure update staging selector. | Planned TINT2. | `[ACTIVE_EXPERIMENTAL] [CPU_ONLY] [GPU_HARD_ERROR]` when added | Planned | Hard error for nonzero mode | Not implemented yet. | Only mode `0/1`; no mode creep. | Immediate TINT2-clean decision after tests. |
| Future `SavePorePressureTimeStageDiagnostics` | Optional pressure-stage diagnostics. | Planned TINT2. | `[DELETE_CANDIDATE]` if added | Planned | No | Temporary only. | Prefer scripts/logs first. | Delete or archive after TINT2. |

## Immediate Governance Decisions

- Keep `PorePressureBoundaryOperator=0` as default.
- Keep `PorePressureBoundaryOperator=1` as the current feedback-on 1D gate.
- Do not promote or port `PorePressureBoundaryOperator=2` until TINT2/BND2
  explain or fix the feedback-on instability.
- Do not continue adding Cryer curved-boundary modes. Archive or delete failed
  modes `5-8` first.
- Do not tune MCC with more submodes; current MCC route is a caveated CPU
  reduced prototype.
- Do not use `MechanicalTopLoad` as strict Terzaghi validation.
- TINT2 may add only the minimal pressure time-staging interface described in
  `tint2_interface_constraint.md`.
