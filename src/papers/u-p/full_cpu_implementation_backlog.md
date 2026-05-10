# Full CPU Implementation Backlog for u-pw Paper Reproduction

Date: 2026-05-11

This backlog is derived from `full_paper_case_audit.md`. It is intentionally
stricter than the earlier reduced-smoke roadmap: GPU coding remains blocked
until the CPU-side paper case requirements are either implemented, smoke-tested,
or explicitly deferred with a documented reason.

## Priority Legend

- **GPU-pre required**: must be completed or explicitly deferred before GPU G1.
- **Strict reproduction required**: needed before claiming strict paper
  reproduction, but may not be needed for the first passive GPU field.
- **Post-GPU / performance**: mainly relevant after CPU correctness is clear.

## Boundary Treatment Milestones

### BND-1: Production Boundary Condition Design for Pore Pressure

- **Goal:** Replace ad hoc layer-only thinking with a precise design for
  drained, no-flux, lateral, and curved pore-pressure boundaries.
- **Cases:** 01 Terzaghi, 02 self-weight, 03 Cryer, 04 triaxial, 05/06 slopes.
- **GPU-pre required:** Yes, as a design decision. Production implementation can
  be staged, but the operator contract must be frozen.
- **Needs design doc:** Yes.
- **Expected files:** `src/papers/u-p/pore_pressure_boundary_production_design.md`
- **Smoke test:** none for design; later hydrostatic/no-flux/Dirichlet short
  cases.
- **Expected outputs:** boundary mode table, selected production path, list of
  arrays and kernels affected.
- **Commit message:** `Design production pore pressure boundary treatment`
- **Blocks:** Cryer strict smoke, coupled Terzaghi strict smoke.

### BND-2: 1D/2D Planar Boundary Prototype

- **Goal:** Implement the selected minimal planar boundary treatment for top
  drained and bottom/lateral no-flux in CPU, initially pressure-only.
- **Cases:** 01, 02, preparatory for 04.
- **GPU-pre required:** Yes if strict 01/02/03 CPU smoke must be achieved before
  GPU.
- **Needs design doc:** BND-1 first.
- **Expected files:** likely `JSph.h`, `JSph.cpp`, `JSphCpu.h`,
  `JSphCpu.cpp`, `JSphCpuSingle.cpp`, docs.
- **Smoke test:** hydrostatic consistency, pressure-only diffusion, uniform
  excess no spurious boundary change.
- **Expected outputs:** boundary residual metrics and `code=0`, `excluded=0`.
- **Commit message:** `Add CPU planar pore pressure boundary operator`
- **Blocks:** strict 1D and self-weight boundary validation.

### BND-3: Curved / Cryer Boundary Prototype

- **Goal:** Support drained curved boundary approximation for Cryer.
- **Cases:** 03 Cryer.
- **GPU-pre required:** Yes under the full CPU gate if Cryer strict smoke is
  mandatory before GPU.
- **Needs design doc:** can extend BND-1.
- **Expected files:** boundary classification/normal and pore pressure ghost or
  MLS support.
- **Smoke test:** coarse Cryer geometry, center pressure field written.
- **Expected outputs:** center pore pressure time series and boundary diagnostics.
- **Commit message:** `Add CPU curved pore pressure boundary smoke support`
- **Blocks:** Cryer strict smoke.

## Corrected PR Operator Milestones

### CG-1: Targeted Linear-Field Diagnostics

- **Goal:** Decide whether corrected-gradient PR operators are required for
  strict reproduction after CPU-CG1 showed no improvement in the tested cases.
- **Cases:** 01, 02, 03.
- **GPU-pre required:** Yes as a decision; production implementation is not yet
  justified.
- **Needs design doc:** existing `corrected_gradient_pr_operator_plan.md` is
  enough; add test note if run.
- **Expected files:** optional analysis scripts or temporary XML only.
- **Smoke test:** hydrostatic field, linear `z` field, linear pressure field,
  boundary error metrics.
- **Expected outputs:** residual table proving defer/enable decision.
- **Commit message:** `Record corrected-gradient PR operator decision tests`
- **Blocks:** only if test shows production corrected operators are required.

### CG-2: Production Switch for PR Operators

- **Goal:** Add `PorePressurePROperator` or equivalent only if CG-1 proves it is
  needed.
- **Cases:** 01, 02, 03.
- **GPU-pre required:** Conditional.
- **Needs design doc:** Yes if promoted.
- **Expected files:** CPU operator code and docs.
- **Smoke test:** pressure-only 1D parity and hydrostatic consistency.
- **Expected outputs:** `DivVel`, `LapPorePress`, `LapZ` production switch
  diagnostics.
- **Commit message:** `Add selectable corrected-gradient PR operators`
- **Blocks:** deferred unless evidence demands it.

## Restart / Staged Workflow Milestones

### RST-1: PorePress Restart

- **Goal:** Restore `PorePress` from BI4 for staged u-pw runs.
- **Cases:** 02 Scenario 1, 05/06 future field workflows.
- **GPU-pre required:** Completed.
- **Needs design doc:** Completed in `porepress_restart_plan.md`.
- **Expected files:** implemented in `JPartsLoad4.*`, `JSphCpuSingle.cpp`.
- **Smoke test:** same-gravity restart and gravity-off restart.
- **Expected outputs:** restart logs and matching `PorePress`.
- **Commit message:** completed as `Restore pore pressure state during CPU restart`.
- **Blocks:** none currently.

### RST-2: Restart Documentation and Case Workflows

- **Goal:** Make Stage A/B workflows explicit for 02 and future field cases.
- **Cases:** 02, 06.
- **GPU-pre required:** Yes for workflow clarity.
- **Needs design doc:** no.
- **Expected files:** case README/notes.
- **Smoke test:** Scenario 1 short staged smoke.
- **Expected outputs:** status table.
- **Commit message:** `Document staged pore pressure restart workflows`
- **Blocks:** Scenario 1 strict smoke documentation.

## Loading and Mechanical Boundary Milestones

### LOAD-1: AccInput External Load Path Freeze

- **Goal:** Document native AccInput as the formal external-load route after
  source-side `TopLoad*` removal.
- **Cases:** 01 external Terzaghi, 04 triaxial loading experiments.
- **GPU-pre required:** Yes as an interface decision.
- **Needs design doc:** no; update notes.
- **Expected files:** `u_pw_parameters.md`, case READMEs.
- **Smoke test:** AccInput template XML parse / very short run if needed.
- **Expected outputs:** AccInput history file examples.
- **Commit message:** `Document AccInput external load path`
- **Blocks:** external-load Terzaghi and triaxial setup.

### LOAD-2: Triaxial Axial Loading Design

- **Goal:** Design a controlled axial loading method using native motion,
  moving boundary, or AccInput without source-side load hacks.
- **Cases:** 04.
- **GPU-pre required:** Yes for strict triaxial smoke.
- **Needs design doc:** Yes.
- **Expected files:** `src/papers/u-p/triaxial_loading_confinement_plan.md`
- **Smoke test:** none for design.
- **Expected outputs:** selected loading mechanism and XML requirements.
- **Commit message:** `Design triaxial loading and confinement workflow`
- **Blocks:** 04 strict CPU smoke.

### LOAD-3: Triaxial Confinement Boundary Prototype

- **Goal:** Provide a minimal confinement approximation sufficient for a short
  undrained triaxial smoke.
- **Cases:** 04.
- **GPU-pre required:** Yes if 04 strict smoke is mandatory before GPU.
- **Needs design doc:** LOAD-2 first.
- **Expected files:** likely XML/motion setup first; source only if native
  mechanisms are insufficient.
- **Smoke test:** small strain, no NaN, plausible pore pressure sign.
- **Expected outputs:** axial strain, pore pressure, stress path data.
- **Commit message:** `Add triaxial confinement smoke workflow`
- **Blocks:** 04 strict smoke.

## Constitutive Model Milestones

### MAT-1: DP vs MCC Decision for Triaxial

- **Goal:** Decide whether paper triaxial reproduction can be approximated by
  current Drucker-Prager or requires Modified Cam-Clay.
- **Cases:** 04.
- **GPU-pre required:** Decision yes; MCC implementation no unless strict gate
  says so.
- **Needs design doc:** Yes.
- **Expected files:** `src/papers/u-p/triaxial_constitutive_gap.md`
- **Smoke test:** none.
- **Expected outputs:** explicit accept/defer statement.
- **Commit message:** `Document triaxial constitutive model gap`
- **Blocks:** strict 04 reproduction claim.

### MAT-2: Sensitive Clay / Strain Softening Design

- **Goal:** Design material model requirements for retrogressive slope and
  Sainte-Monique.
- **Cases:** 05, 06.
- **GPU-pre required:** Design yes; implementation should not block passive PR
  GPU if slope/field strict reproduction is explicitly deferred.
- **Needs design doc:** Yes.
- **Expected files:** `src/papers/u-p/sensitive_clay_model_plan.md`
- **Smoke test:** none for design.
- **Expected outputs:** state variables, parameters, output needs.
- **Commit message:** `Design sensitive clay constitutive requirements`
- **Blocks:** strict 05/06 reproduction.

### MAT-3: Sensitive Clay Minimal CPU Prototype

- **Goal:** Implement only if user accepts scope after MAT-2.
- **Cases:** 05, 06.
- **GPU-pre required:** No for PR core; yes if strict 05/06 must run before GPU.
- **Needs design doc:** MAT-2 first.
- **Expected files:** constitutive model source, docs, examples.
- **Smoke test:** element-like or small slope smoke.
- **Expected outputs:** softening/remolding diagnostics.
- **Commit message:** `Add CPU sensitive clay softening prototype`
- **Blocks:** do not auto-implement without explicit approval.

## Initial Condition Milestones

### IC-1: Effective-Stress Initial State Audit

- **Goal:** Clarify how current `Sigmac` effective stress, hydrostatic pore
  pressure, body gravity, and excess pressure should be initialized for each
  paper case.
- **Cases:** 01-06.
- **GPU-pre required:** Yes as a setup contract.
- **Needs design doc:** Yes.
- **Expected files:** `src/papers/u-p/effective_stress_initialization_plan.md`
- **Smoke test:** self-weight short and hydrostatic-only.
- **Expected outputs:** per-case initialization table.
- **Commit message:** `Document u-pw effective stress initialization strategy`
- **Blocks:** slope/field and triaxial strict setup.

### IC-2: Slope / Field Initial State Workflow

- **Goal:** Build a restart/dynamic relaxation or explicit initialization path
  for slopes and field cases.
- **Cases:** 05, 06.
- **GPU-pre required:** No for PR core; yes for strict 05/06.
- **Needs design doc:** IC-1 first.
- **Expected files:** case scripts / XML workflows.
- **Smoke test:** reduced slope with bounded velocity and no NaN.
- **Expected outputs:** initial stress and pore pressure summary.
- **Commit message:** `Add slope initial state smoke workflow`
- **Blocks:** 05/06 strict reproduction.

## Case Scaffold Milestones

### CASE-1: 03 Cryer Strict Parameter Reconstruction

- **Goal:** Extract or manually record Cryer paper parameters from the PDF/SI.
- **Cases:** 03.
- **GPU-pre required:** Yes.
- **Needs design doc:** no, but needs source citation.
- **Expected files:** `examples/u-pw/03_Cryer_Problem/notes.md`
- **Smoke test:** no run until parameters are known.
- **Expected outputs:** complete parameter table or explicit unknown list.
- **Commit message:** `Record Cryer paper parameters`
- **Blocks:** 03 strict smoke.

### CASE-2: 04 Triaxial Strict Parameter Reconstruction

- **Goal:** Extract material/loading/confinement table for triaxial tests.
- **Cases:** 04.
- **GPU-pre required:** Yes.
- **Needs design doc:** no, but may need PDF text extraction/manual review.
- **Expected files:** `examples/u-pw/04_Undrained_Triaxial/notes.md`
- **Smoke test:** none until setup is known.
- **Expected outputs:** parameter table and output targets.
- **Commit message:** `Record undrained triaxial paper parameters`
- **Blocks:** 04 strict smoke.

### CASE-3: 05/06 Field Data Inventory

- **Goal:** Identify whether required slope/field data exists locally.
- **Cases:** 05, 06.
- **GPU-pre required:** Yes as a data-block decision.
- **Needs design doc:** no.
- **Expected files:** case `data/README.md`, notes.
- **Smoke test:** none.
- **Expected outputs:** data availability table.
- **Commit message:** `Record landslide case data inventory`
- **Blocks:** 06 strict reproduction.

## Postprocessing Milestones

### POST-1: Terzaghi / Self-Weight Plot Scripts

- **Goal:** Produce lightweight scripts for pressure profiles and nondimensional
  time, without long CPU runs.
- **Cases:** 01, 02.
- **GPU-pre required:** Yes for strict smoke reporting.
- **Needs design doc:** no.
- **Expected files:** analysis scripts in case folders.
- **Smoke test:** run on short outputs or existing summaries.
- **Expected outputs:** profile/error CSV/SVG.
- **Commit message:** `Add 1D consolidation postprocessing scripts`
- **Blocks:** strict comparison reporting.

### POST-2: Cryer Center Pressure Script

- **Goal:** Extract center pore pressure and compare to reference once geometry
  exists.
- **Cases:** 03.
- **GPU-pre required:** Yes for Cryer strict smoke.
- **Needs design doc:** no.
- **Expected files:** `analyze_cryer_smoke.py`
- **Smoke test:** run on short output.
- **Expected outputs:** center pressure CSV.
- **Commit message:** `Add Cryer center pressure smoke analysis`
- **Blocks:** 03 strict smoke.

### POST-3: Triaxial Stress Path Script

- **Goal:** Compute axial strain, `p'`, `q`, and pore-pressure trend from output.
- **Cases:** 04.
- **GPU-pre required:** Yes for triaxial strict smoke.
- **Needs design doc:** no.
- **Expected files:** `analyze_triaxial_smoke.py`.
- **Smoke test:** run on reduced triaxial output.
- **Expected outputs:** stress path CSV.
- **Commit message:** `Add triaxial stress path smoke analysis`
- **Blocks:** 04 strict smoke.

### POST-4: Slope / Field Failure Metrics

- **Goal:** Define displacement, velocity, and retrogression metrics.
- **Cases:** 05, 06.
- **GPU-pre required:** No for PR core; yes for strict slope/field.
- **Needs design doc:** yes if metrics are complex.
- **Expected files:** analysis notes/scripts.
- **Smoke test:** reduced outputs only.
- **Expected outputs:** displacement/failure extent summary.
- **Commit message:** `Add landslide smoke postprocessing notes`
- **Blocks:** strict 05/06 reproduction.

## Immediate Recommended Order

1. BND-1: production pore-pressure boundary design.
2. LOAD-2: triaxial loading/confinement design.
3. MAT-1: DP vs MCC decision for triaxial.
4. MAT-2: sensitive clay model design for 05/06.
5. IC-1: effective-stress initialization plan.
6. CASE-1/2/3: parameter/data reconstruction from paper/PDF/manual notes.
7. POST-2/3: Cryer and triaxial minimal postprocessing scripts.
8. Decide which strict reproduction blockers are implemented before GPU and
   which are explicitly deferred by user decision.

## Current GPU Gate Status

GPU coding is still blocked under the full CPU case completion standard. The
branch has a useful CPU PR core, but strict CPU smokes for Cryer, triaxial, and
landslide cases require boundary, loading, constitutive, setup, and
postprocessing decisions that are not yet complete.

