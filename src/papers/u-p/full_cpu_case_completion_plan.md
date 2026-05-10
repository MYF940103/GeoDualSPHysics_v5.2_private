# Full CPU Case Completion Plan Before GPU

## 1. GPU-Entry Gate

GPU coding is blocked until all paper reproduction case directories reach CPU
smoke readiness or are explicitly marked data/feature blocked with a concrete
path forward. The earlier gate of "PR core plus 01/02 readiness" is not enough.

Before GPU G1 starts:

- 01-06 must each have a case directory with README, notes, and XML/BAT or an
  explicit data/feature block.
- Every case must use paper-oriented parameters where known. Unknown values must
  be marked `TODO`, not invented.
- Every case must either run a short CPU smoke or document the exact missing
  feature/data that blocks it.
- TODO scaffold alone is not enough.
- No CUDA, `JSphGpu*`, `JCellDivGpu*`, or `.cu` work should start until this
  gate is revisited.

## 2. Current Case Status After Strict Re-Audit

| Case | Current state | CPU smoke status | Gate status |
| --- | --- | --- | --- |
| 01 1D consolidation / pressure-only | Runnable pressure-only baseline; SW3h result archived as diagnostic. | Short pressure-only smoke passed. | Complete for regression-anchor scope. |
| 02 Self-weight consolidation | Formal Scenario 1 Stage A/B and Scenario 2 smoke scaffolds. | Short Stage A/B and Scenario 2 smoke passed. | Complete for smoke scope. |
| 03 Cryer | Reduced PR smoke XML plus TODO scaffold. | GenCase code=0, Dual code=0, excluded=0, fields written. | Reduced smoke only. Strict Cryer remains boundary/geometry/postprocessing blocked and now blocks the full CPU gate. |
| 04 Undrained triaxial | Reduced DP/u-pw AccInput smoke plus TODO scaffold. | GenCase code=0, Dual code=0, excluded=0, fields written, small positive excess under tiny compression. | Reduced smoke only. Strict triaxial remains loading/confinement/stress-path/MCC blocked and now blocks the full CPU gate. |
| 05 Retrogressive slope | Reduced 3D wedge PR smoke plus TODO scaffold. | GenCase code=0, Dual code=0, excluded=0, fields written. | Reduced smoke only. Strict retrogression remains sensitive-clay/initial-state/boundary/GPU blocked. |
| 06 Sainte-Monique | Reduced synthetic field placeholder smoke plus data README. | GenCase code=0, Dual code=0, excluded=0, fields written. | Placeholder smoke only. Field reproduction remains data/material/calibration/GPU blocked. |

## 3. Missing Strict-Reproduction Features

### 01 1D Consolidation

- No blocker for pressure-only smoke.
- Strict external-load Terzaghi still needs a stable loading/traction strategy
  and stronger boundary treatment, but it is not the current GPU-entry gate.

### 02 Self-Weight Consolidation

- No blocker for short CPU smoke.
- Long-time tuning and strict SI curves are deferred to GPU or explicit manual
  requests.
- Boundary ghost and corrected-gradient diagnostics remain non-production.

### 03 Cryer Problem

- Strict spherical/cylindrical benchmark geometry and analytical
  postprocessing need refinement.
- Drained boundary treatment likely needs pore-pressure ghost/MLS or a
  documented simplified boundary for smoke.
- High-resolution Cryer is a GPU-stage task.

### 04 Undrained Triaxial

- Strict axial strain/stress control is missing.
- Prescribed confinement/lateral stress boundary is missing.
- Current DP material is only an approximation; strict matching may require MCC.
- Stress-path script exists as a scaffold, but `p'`/`q` validation remains.

### 05 Retrogressive Slope

- Strict reproduction needs sensitive clay / strain-softening and material
  zoning.
- Initial effective stress and pore-pressure construction for a real slope are
  not validated.
- Coupled feedback is off in the reduced smoke and must be revisited after GPU.

### 06 Sainte-Monique

- Field topography/material zoning/groundwater data are missing.
- Sensitive clay calibration and validated field initial state are missing.
- Full field runs require GPU and checkpoint/restart workflow.

## 4. Recommended Execution Order From Here

1. Keep 01/02 as regression anchors.
2. Complete or explicitly defer strict blockers for 03/04/05/06:
   - Cryer geometry, boundary, and center-pressure postprocessing;
   - triaxial loading/confinement, stress path, and material decision;
   - sensitive clay / initial state for slope and field cases;
   - Sainte-Monique field data and calibration.
3. Keep the current CPU production PR path documented:
   - uncorrected material-only PR operators;
   - `PorePressureAccelDiff` as the coupled feedback candidate;
   - no source-side `TopLoad*`;
   - no `PorePressureAccelSymCorr`;
   - simple ghost and corrected-gradient outputs remain diagnostics only.
4. Do not start GPU coding until the full CPU gate is revisited.

## 5. GPU Block Statement

GPU coding remains blocked under the user's stricter full CPU completion
standard. Reduced CPU smokes for 03-06 are useful health checks but do not
authorize GPU G1. A later decision may explicitly defer some strict
application-level blockers, but that decision has not been made in this plan.

## 6. New Design Documents Added After Re-Audit

- `full_paper_case_audit.md`
- `full_cpu_implementation_backlog.md`
- `pore_pressure_boundary_production_design.md`
- `triaxial_loading_confinement_plan.md`
- `triaxial_constitutive_gap.md`
- `sensitive_clay_model_plan.md`
- `effective_stress_initialization_plan.md`
