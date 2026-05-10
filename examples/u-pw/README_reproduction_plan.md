# u-pw PR Reproduction Roadmap

This roadmap organizes the remaining work needed to reproduce the PR-formulation cases from **A Coupled u-pw SPH Formulation for Hydromechanical Modeling of Retrogressive Landslides and Comparison With a Penalty-Based Approach** in this GeoDualSPHysics v5.2 branch.

Scope:

- Target formulation: PR only. PPE is intentionally unsupported in this branch.
- Solver priority: CPU first, then GPU planning/porting after CPU behavior is stable.
- Current reference inputs: `src/papers/u-p/*.md`, `doc/xml_format`, `doc/guides`, and existing `examples` templates.
- Note: at the time this file was generated, `src/papers/u-p` contained markdown notes and reviews, not the original PDF files.

## R1-R4 CPU Smoke Update

After the full CPU case-completion pass, every target directory now has either a
runnable reduced CPU smoke or an explicit data/feature block:

- `01_1D_Consolidation`: pressure-only regression anchor remains runnable.
- `02_SelfWeight_Consolidation`: Scenario 1 staged restart and Scenario 2
  short smoke scaffolds are formalized.
- `03_Cryer_Problem`: reduced PR smoke runs, but strict Cryer remains boundary
  and analytical-postprocessing blocked.
- `04_Undrained_Triaxial`: reduced native-AccInput DP/u-pw smoke runs, but
  strict triaxial remains loading/confinement/MCC blocked.
- `05_Retrogressive_Slope`: reduced wedge PR smoke runs, but strict
  retrogression remains sensitive-clay/GPU blocked.
- `06_Sainte_Monique`: reduced placeholder smoke runs, but field reproduction
  remains data/material/GPU blocked.

These smokes are not long-time calibrations. Under the stricter full CPU
completion gate, they also are not enough to authorize GPU work by themselves.
Reduced smoke proves that the directories and current PR fields are wired; it
does not prove strict reproduction of the original paper case.

GPU coding remains blocked until every paper case is either strict-smoke
runnable or explicitly deferred with a documented reason in the CPU backlog.

## 1. Target Case List

| Case | Purpose | Paper / SI role | Current priority |
|---|---|---|---|
| 1D consolidation / Terzaghi pressure-only baseline | Verify PR pore-pressure diffusion, drainage, no-flux behavior, and analytical decay without mechanics feedback. | First hydraulic sanity check before coupled reproduction. | Complete baseline exists. Keep as regression test. |
| Self-weight consolidation Scenario 1 | Generate self-weight undrained pore pressure, then switch body gravity off and dissipate with hydraulic gravity retained. | Supporting Information Scenario 1. | Next major missing verification. |
| Self-weight consolidation Scenario 2 | Generate self-weight pore pressure and keep body gravity on during drainage; total pressure should trend to hydrostatic. | Supporting Information Scenario 2. | Stable long-run line exists for xi=0.10; needs paper-compatible xi and formal comparison. |
| Cryer problem | Coupled consolidation under spherical/cylindrical symmetry with pore-pressure Mandel-Cryer-type behavior. | Strong coupled u-pw benchmark. | Reduced PR CPU smoke exists only. Strict Cryer still needs paper geometry, drained curved boundary, boundary ghost/MLS, and center-pressure postprocessing. |
| Undrained triaxial tests | Validate undrained response, effective stress, pore-pressure feedback, and constitutive behavior. | Material-level coupled validation. | Reduced DP/u-pw AccInput CPU smoke exists only. Strict reproduction still needs axial loading/confinement, stress-path output, and MCC/DP material decision. |
| Retrogressive slope / landslide benchmark | Demonstrate PR formulation on idealized retrogressive slope. | Main hydromechanical landslide benchmark before field case. | Reduced PR wedge CPU smoke exists only. Strict retrogression needs sensitive/softening material, initial-state workflow, boundary treatment, and GPU-scale execution. |
| Sainte-Monique landslide case | Field-scale reproduction. | Final application case. | Reduced placeholder CPU smoke exists only. Validated field case remains data/material/calibration/GPU blocked. |

## 2. Recommended Directory Layout

Proposed final structure under `examples/u-pw`:

| Directory | Role | Notes |
|---|---|---|
| `01_1D_Consolidation` | Current pressure-only baseline, self-weight diagnostics, and SW3h Scenario 2 long-run result. | Keep current formal baseline and SW3h result here. Experiments remain under `experiments/`. |
| `02_SelfWeight_Consolidation` | Formal Supporting Information Scenario 1 / Scenario 2 cases. | Create once Scenario 1 restart/gravity-switch route is defined. Could reuse assets from `01_1D_Consolidation`. |
| `03_Cryer_Problem` | Cryer benchmark scaffold and reduced PR smoke. | Strict case still requires geometry, analytical solution notes, and boundary-pressure strategy. |
| `04_Undrained_Triaxial` | Undrained triaxial scaffold and reduced AccInput smoke. | Strict case still needs loading/control boundary design, confinement, and stress-path validation. |
| `05_Retrogressive_Slope` | Idealized retrogressive slope scaffold and reduced wedge smoke. | Strict case waits for GPU port and sensitive/softening material decisions. |
| `06_Sainte_Monique` | Sainte-Monique field scaffold and reduced placeholder smoke. | Validated field case remains data/material/GPU blocked. |

`01_1D_Consolidation` can keep both pressure-only and current self-weight material for now because the files share geometry, parameters, scripts, and analysis tooling. A separate `02_SelfWeight_Consolidation` should be created when Scenario 1 and Scenario 2 become formal reproducible cases rather than diagnostics.

## 3. Current Case Status

| Case | Current status | Strict reproduction status |
|---|---|---|
| 1D pressure-only consolidation | Existing runnable baseline: `Case1DConsolidation_PR_Def.xml`; pressure diffusion sanity check passed. | Good regression baseline, but not a coupled Terzaghi reproduction. |
| Self-weight Scenario 2 | Existing long-run line: `Case1DConsolidation_PR_SelfWeight_Scenario2_T3p6_Xi010_Def.xml`, `SW3h_scenario2_T3p6_xi010/`; stable to 3.6 s, excluded=0, pressure trends toward hydrostatic. | Promising but still needs formal SI-style comparison and paper-compatible damping line. |
| Self-weight Scenario 1 | Not implemented as a formal restart workflow. | Needs body-gravity switch or restart with gravity off, and likely PorePress restart support. |
| External-load Terzaghi | Pressure-only baseline works; coupled external-load smoke tests now use native `AccInput`; the earlier source-side `TopLoad` path has been removed after proving unsuitable for formal cases. | Current route is experimental only. Need traction/loading strategy and/or better coupled stabilization. |
| Cryer problem | Reduced PR smoke exists in `03_Cryer_Problem`; TODO XML retained. | Strict geometry, drained pressure boundary, and analytical postprocessing still required. |
| Undrained triaxial | Reduced DP/u-pw AccInput smoke exists in `04_Undrained_Triaxial`; stress-path script scaffold added. | Strict loading/control, confinement, and possible MCC still required. |
| Retrogressive slope | Reduced wedge PR smoke exists in `05_Retrogressive_Slope`; TODO XML retained. | Strict retrogression needs sensitive/softening material, initial state, and GPU. |
| Sainte-Monique | Reduced synthetic placeholder smoke exists in `06_Sainte_Monique`; `data/README.md` records missing field data. | Field reproduction remains data/material/GPU blocked. |

## 4. Missing Function Matrix

| Feature | Why it matters | Affected cases | Current status |
|---|---|---|---|
| Pore-pressure boundary ghost / MLS extrapolation | Layer corrections are stable enough for 1D diagnostics, but strict drained/no-flux boundaries need particle-consistent pressure values. | Terzaghi, self-weight, Cryer, slopes. | Missing. Current top drained and bottom no-flux are layer corrections. |
| Corrected-gradient PR operators | Paper operators use corrected gradients; current PR `DivVel`, `LapPorePress`, and `LapZ` are not globally corrected. | Strict analytical comparisons, boundaries, Cryer. | Only a failed diagnostic for symmetric feedback existed; PR operators not corrected. |
| Lateral no-flux boundary | Needed for non-periodic Terzaghi, Cryer, triaxial cells, and slopes. | Terzaghi, Cryer, triaxial, landslides. | Not implemented; current 1D case avoids it with x-periodic domain. |
| Body gravity stop / switch | Supporting Information Scenario 1 requires gravity-on generation then gravity-off dissipation. | Self-weight Scenario 1. | Not implemented as time-dependent parameter. Can be approximated with restart if pore pressure is preserved. |
| PorePress restart | Needed to carry generated pore pressure from undrained stage into Scenario 1/2 restarts. | Self-weight Scenario 1, staged coupled tests. | Not confirmed/implemented. Stress and density restart were fixed; pore pressure restart remains a likely gap. |
| AccInput-based loading | Required external-load path for targeted acceleration on a top mkfluid layer. | External-load Terzaghi, triaxial loading experiments. | XML mechanism exists and was tested, but coupled response remains stiff. |
| Proper traction / loading plate | More physical than top-layer body acceleration for q0. | External-load Terzaghi, triaxial. | Missing. Native motion/floating/Chrono patterns may help but not designed yet. |
| Modified Cam Clay | Needed if reproducing cases that use MCC rather than Drucker-Prager. | Triaxial and some literature comparisons if MCC is specified. | Missing. Current soil model is DP-style effective stress. |
| Sensitive clay / strain softening | Needed for retrogressive landslide and Sainte-Monique-style remolding behavior. | Retrogressive slope, Sainte-Monique. | Existing GeoDualSPHysics may have some soil plasticity, but PR-specific sensitive clay calibration is not ready. |
| GPU kernels | Required for long 3D/field runs. | Cryer 3D, slopes, Sainte-Monique. | Missing for u-pw arrays/operators. CPU-only prototype. |
| Output postprocessing | Needed for paper-style plots and metrics. | All cases. | Good start for SW3h; needs general scripts per case. |
| Cleanup of debug interfaces | Keeps production XML/API clean. | All formal cases. | `PorePressureAccelSymCorr` and source `TopLoad*` have been removed; continue avoiding debug-only interfaces in formal cases. |

## 5. Minimum Smoke Test Standards

Every new case should have a tiny CPU Debug smoke test before longer runs:

| Standard | Requirement |
|---|---|
| Process status | `code=0`; no exception, no access violation. |
| Particle status | `excluded=0`; no NaN/Inf in key fields. |
| Output | Required fields written: position, velocity, rhop, `PorePress`, `ExcessPorePress`, `PorePressRate`, `DivVel`, `LapPorePress`, `LapZ`, `PorePressureAccelDiff` when applicable. |
| Time step | `dt_pore` active and reported when `PorePressureModel=1`; no manual `DtFixed` unless a specific comparison requires it. |
| Boundary behavior | Top drained layer stays near zero excess after activation; bottom no-flux gradient proxy remains bounded. |
| Physics trend | Pressure-only cases diffuse monotonically in amplitude; self-weight Scenario 2 trends toward hydrostatic; coupled tests do not show explosive `Kw/n * DivVel` feedback. |
| Runtime | CPU Debug for smoke; CPU Release for long 1D; GPU only after parity plan exists. |

Additional case-specific smoke checks:

- Terzaghi pressure-only: fitted amplitude follows the analytical diffusion trend within a coarse tolerance.
- Self-weight undrained: generated pore pressure has the same sign as Supporting Information Eq. (4), with total/excess comparison defined explicitly.
- Scenario 1: after gravity-off restart, pore pressure dissipates rather than recharging toward hydrostatic.
- Scenario 2: total pressure tends toward hydrostatic and excess tends toward zero.
- Cryer: pore pressure remains bounded and symmetry is preserved.
- Triaxial: axial strain, volumetric response, and pore-pressure trend have correct sign.
- Landslide: no early numerical blow-up; failure mechanism qualitatively plausible before calibration.

## 6. Recommended Implementation Order

### Phase R0: Freeze current CPU PR baseline

- Keep `01_1D_Consolidation` as regression suite.
- Maintain pressure-only baseline and SW3h long-run result.
- Keep experiments archived, not mixed with formal templates.

### Phase R1: Finish self-weight reproduction on CPU

1. Formalize Scenario 2 comparison using the existing long-run path.
2. Add paper-compatible damping line, e.g. `HydromechDampingXi=0.05`, if runtime allows.
3. Implement or approximate Scenario 1:
   - preferred: PorePress restart plus restart with body gravity off;
   - alternative: time-dependent `BodyGravityStopTime` if restart path is insufficient.
4. Produce SI-style plots for both scenarios.

### Phase R2: Improve pore-pressure boundaries and restart

Priority features:

1. PorePress restart from `Part_XXXX.bi4` or an explicit pore-pressure initial file.
2. Boundary pore-pressure ghost / MLS treatment for top drained and no-flux boundaries.
3. Lateral no-flux for non-periodic 1D/2D tests.

Do this before strict Cryer or external-load Terzaghi.

### Phase R3: External-load Terzaghi and loading strategy

1. Keep pressure-only baseline separate.
2. Use native `AccInput` or a controlled traction/loading plate; source `TopLoad*` has been removed.
3. Use long ramps, damping, and Shepard smoothing.
4. Only compare to Terzaghi analytical solution once loading-generated excess pressure is stable and boundary treatment is trustworthy.

### Phase R4: Cryer and undrained triaxial CPU smoke tests

1. Create scaffolds and README notes first.
2. Use small CPU Debug smoke tests.
3. Add postprocessing scripts before tuning.
4. Decide whether current DP effective stress is enough or whether MCC/sensitive clay is required.

### Phase R5: GPU port planning

Status update, 2026-05-11: this phase is paused. GPU planning documents can
remain as references, but GPU coding must not start until the stricter full CPU
case gate is satisfied or explicitly relaxed.

Before writing CUDA kernels, freeze the formal CPU data model:

- `PorePress` double or GPU-compatible precision strategy.
- `PorePressRate`, `DivVel`, `LapPorePress`, `LapZ`.
- `PorePressureAccelDiff` feedback.
- Shepard regularization.
- Hydraulic boundary data and any ghost/MLS fields.
- Restart and output requirements.

Then port arrays, sorting/duplicate, interaction kernels, update kernels, output, and restart in a staged CPU/GPU parity workflow.

### Phase R6: GPU implementation and long cases

1. GPU smoke parity on pressure-only 1D.
2. GPU parity on self-weight Scenario 2 short window.
3. GPU long Scenario 2.
4. Only then scale to Cryer, retrogressive slope, and Sainte-Monique.

## 7. Per-Case Roadmap

### 01: 1D Consolidation

Current directory: `examples/u-pw/01_1D_Consolidation`

Status:

- Pressure-only PR baseline exists.
- Self-weight Scenario 2 diagnostic/long-run exists.
- Experiments are organized under `experiments/`.

Keep in root:

- `Case1DConsolidation_PR_Def.xml`
- `xCase1DConsolidation_PR_win64_CPU_debug.bat`
- `Case1DConsolidation_PR_SelfWeight_Scenario2_T3p6_Xi010_Def.xml`
- `xCase1DConsolidation_PR_SelfWeight_Scenario2_T3p6_Xi010_win64_CPU_release.bat`
- `SW3h_scenario2_T3p6_xi010/`

Next actions:

1. Use this as regression suite for future source changes.
2. Add formal comparison README for pressure-only and SW3h results.
3. Do not add more exploratory files to root; put them under `experiments/`.

### 02: SelfWeight_Consolidation

Suggested directory: `examples/u-pw/02_SelfWeight_Consolidation`

Status: needs scaffold.

Purpose:

- Formal Supporting Information Scenario 1 and Scenario 2 reproduction.

Needed functionality:

- Scenario 2 can reuse current CPU functionality.
- Scenario 1 needs either PorePress restart or body gravity switching.
- Better postprocessing scripts for SI-style nondimensional time and profiles.

Smoke test:

- CPU Debug, `TimeMax=0.005` or `0.01`, excluded=0.
- Correct sign for undrained self-weight pore pressure.
- Top drained delayed; bottom no-flux stable.

### 03: Cryer_Problem

Suggested directory: `examples/u-pw/03_Cryer_Problem`

Status: reduced PR CPU smoke exists, but current code/setup is not ready for
strict Cryer reproduction.

Likely needed:

- 3D or axisymmetric geometry.
- Spherical/cylindrical drained boundary handling.
- Pore-pressure ghost/MLS and corrected operators.
- GPU for useful resolution.

Smoke test:

- Coarse CPU Debug geometry with pressure output only.
- Verify symmetry and bounded pressure before comparing peak/center response.

### 04: Undrained_Triaxial

Suggested directory: `examples/u-pw/04_Undrained_Triaxial`

Status: reduced DP/u-pw AccInput CPU smoke exists, but strict triaxial
reproduction is not complete.

Likely needed:

- Controlled axial loading or prescribed boundary motion.
- Lateral stress/confinement representation.
- Pore-pressure feedback stable under undrained deformation.
- Stress-path postprocessing: deviatoric stress, mean effective stress, pore pressure, axial strain.
- Possibly MCC if the paper uses it; otherwise DP calibration must be documented as an approximation.

Smoke test:

- Very small strain, CPU Debug.
- Pore pressure sign and effective stress trend correct.
- No excluded particles, no NaN.

### 05: Retrogressive_Slope

Suggested directory: `examples/u-pw/05_Retrogressive_Slope`

Status: reduced wedge CPU smoke exists, but strict retrogressive slope
reproduction is not complete.

Likely needed:

- Larger geometry and long runtime; GPU required.
- Sensitive clay / strain-softening or remolding behavior if matching the paper.
- Robust pore-pressure boundaries and seepage/drainage setup.
- Postfailure visualization and run monitoring.

Smoke test:

- 2D coarse CPU Debug or Release short run to validate setup.
- GPU parity before production-size run.
- Key outputs: displacement, velocity, pore pressure, excess pressure, plasticity indicators.

### 06: Sainte_Monique

Suggested directory: `examples/u-pw/06_Sainte_Monique`

Status: reduced synthetic placeholder smoke exists, but validated field
reproduction is not ready.

Likely needed:

- Field geometry preparation and material zoning.
- GPU u-pw implementation.
- Sensitive clay calibration.
- Initial stress and pore-pressure state construction.
- Long-run monitoring and checkpoint/restart.

Smoke test:

- Geometry-only or reduced CPU smoke with outputs.
- Do not use this placeholder as field validation.
- GPU/production run only after data, material calibration, and initial-state
  workflow are available.

## 8. Next Code Feature Recommendations

Ranked by current roadmap value:

1. **PorePress restart**
   - Highest value for Scenario 1 and staged coupled tests.
   - Should restore `PorePress`, and optionally diagnostics if present.
   - Must preserve stress/density restart fixes.

2. **BodyGravityStopTime or staged gravity switch**
   - Useful for Scenario 1.
   - Restart may be cleaner because it preserves a clear stage boundary; a runtime switch is simpler for XML but touches mechanics semantics.

3. **Boundary pore-pressure ghost / MLS**
   - Needed before strict Terzaghi/Cryer comparisons.
   - Should target PR `LapPorePress`, `LapZ`, and feedback consistency.

4. **Lateral no-flux boundary**
   - Needed once leaving x-periodic 1D setup.
   - Can share ghost/MLS infrastructure.

5. **GPU port planning**
   - Do not start kernels until CPU formal field set is frozen.
   - Start with a document listing arrays, sorting, duplicate, update, output, and restart needs.

6. **External loading strategy**
   - Prefer native `AccInput` or a real traction/loading plate.
   - Source `TopLoad*` has been removed; formal external-load cases should use `AccInput` or a future traction/loading plate.

## 9. Debug / Temporary Interfaces To Clean Later

Keep until self-weight and Scenario 1 are locked:

- `PorePressureAccel` symmetric diagnostic.
- `PorePressureAccelSymCorr` diagnostic.
- Historical source-side `TopLoad*` parameters are removed.

Cleanup candidates:

| Interface | Recommendation |
|---|---|
| `PorePressureAccelSymCorr` | Remove after current self-weight verification; it amplified boundary fake force and is not recommended. |
| Source `TopLoadEnabled`, `TopLoad`, `TopLoadThickness`, `TopLoadRampStart`, `TopLoadRampEnd` | Removed in CPU-F6a; use native `AccInput` for formal external-load cases. |
| `PorePressureModel=2` | Already hard error / unsupported. Keep as explicit unsupported label if useful. |
| Excessive experiment XML in root | Keep all exploratory files under `experiments/`, as now done for `01_1D_Consolidation`. |

## 10. Immediate Next Step

Recommended next step after this roadmap:

1. Create scaffold directories only:
   - `02_SelfWeight_Consolidation/`
   - `03_Cryer_Problem/`
   - `04_Undrained_Triaxial/`
   - `05_Retrogressive_Slope/`
   - `06_Sainte_Monique/`
2. Add `README.md` and `notes.md` to each.
3. Add draft XML/BAT only where the required current functionality exists.
4. Do not run new calculations until the scaffold and missing-feature table are reviewed.

The short version: keep `01_1D_Consolidation` as the regression anchor; formalize self-weight next; defer GPU and landslides until pore-pressure restart, boundary treatment, and CPU smoke standards are stable.
