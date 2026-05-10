# CPU Case Smoke Completion Plan Before GPU G1

This plan freezes the remaining CPU-side case-readiness work before starting
GPU Phase G1.  It is intentionally limited to CPU feature status, case
scaffolds, and short smoke-test readiness.  It does not define CUDA work.

Related planning documents:

- `examples/u-pw/README_reproduction_plan.md`
- `src/papers/u-p/cpu_pre_gpu_freeze_plan.md`
- `src/papers/u-p/gpu_port_plan.md`
- `src/papers/u-p/pore_pressure_boundary_ghost_plan.md`
- `src/papers/u-p/corrected_gradient_pr_operator_plan.md`

## 1. Completed CPU Function Nodes

The following CPU-side hydromechanical PR features are considered available for
short smoke testing and case scaffolding.

| Feature / node | Current status | Notes |
|---|---|---|
| PR pressure-only baseline | Complete | `01_1D_Consolidation` pressure-only diffusion passed the 1D sanity check. |
| Self-weight Scenario 2 | Complete as a stable CPU line | Gravity-on dissipation reached the long diagnostic line; future CPU work should only use short smoke tests unless explicitly requested. |
| `BodyGravityStopTime` | Complete | Enables Scenario 1-style gravity-on generation followed by mechanical body-gravity stop while hydraulic gravity remains active. |
| `PorePress` restart | Complete | CPU restart restores `PorePress` from `Part_XXXX.bi4` by `Idp` mapping; used for staged workflows. |
| Scenario 1 staged smoke | Complete | Stage A / Stage B workflow ran as a short smoke test. It should now be formalized, not extended on CPU. |
| Boundary ghost diagnostics | Complete as diagnostic-only | `PorePressGhost`, `ExcessPorePressGhost`, boundary mode, `LapPorePressGhost`, and `LapZGhost` are diagnostic-only. BG3 showed the simple ghost Laplacian should not become production. |
| Corrected-gradient PR diagnostics | Complete as diagnostic-only | `DivVelCorr`, `LapPorePressCorr`, and `LapZCorr` output works, but CPU-CG1 did not improve the short metrics. Production switch is deferred. |
| `HydromechDampingXi` | Complete | Paper-compatible damping input; internally converted to `c_d = xi * sqrt(E/(rho*h^2))`. |
| `PorePressureShepard` | Complete | Optional pressure regularization; mode 1 regularizes excess pressure and is recommended for self-weight/Terzaghi-style coupled smoke cases. |
| Material constants in `StSoilCte` | Complete | `Porosity0`, `HydraulicConductivity`, `WaterBulkModulus`, and `WaterDensity` moved to soil constants with deprecated `<parameters>` fallback. |
| `PorePressureModel=2` hard error | Complete | PPE remains unsupported in this branch. |
| Common formatting / safe `snprintf` fix | Complete in current CPU utility path | General formatting utilities were fixed after Debug CRT stack corruption around `main.cpp` catch exit. This is a common-tool fix, not hydromech physics. |

## 2. Remaining CPU Items Before GPU G1

The goal before GPU G1 is not strict reproduction.  The goal is to ensure each
paper case has either a short runnable smoke path or an explicit TODO scaffold
with missing features documented.

| Item | Status | GPU-G1 impact | Required action |
|---|---|---|---|
| 02 SelfWeight formal smoke | Mostly available | Blocks GPU G1 only as a case-readiness gate | Formalize Scenario 1/2 XML/BAT and record one short smoke result for each. |
| 03 Cryer scaffold/smoke | Scaffold exists, smoke not done | Does not block G1 if marked TODO | Keep TODO XML until boundary strategy and geometry are clearer; define minimum smoke criteria. |
| 04 Undrained triaxial scaffold/smoke | Scaffold exists, smoke not done | Does not block PR core G1 | Define loading/confinement gaps; do not force runnable XML before boundary/control design. |
| 05 Retrogressive slope scaffold/smoke | Scaffold exists, TODO only | Does not block PR core G1 | Keep scaffold-only; GPU and material-model decisions are needed before meaningful runs. |
| 06 Sainte-Monique scaffold/smoke | Scaffold exists, TODO only | Does not block PR core G1 | Keep scaffold-only; full field case is post-GPU and post-material-model. |
| `TopLoad*` cleanup/deprecation | Source-side path removed in CPU-F6a | Complete before GPU G1 | Formal external-load path is native `AccInput`; formal XML no longer depends on source `TopLoad*`. Archived experiments are historical only. |
| Boundary ghost production decision | Diagnostic result is negative for simple ghost Laplacian | Must be documented before GPU boundary kernels | Keep current layer corrections as production baseline for G1-G4; defer proper MLS/mirror design. |
| Corrected-gradient production decision | Diagnostic result is negative/neutral | Must be documented before GPU PR kernels | Keep current uncorrected PR operators for G1-G4; corrected diagnostics remain CPU-only. |
| Case smoke matrix | Complete for pre-GPU readiness | Case-readiness gate satisfied for G1 scope | 01/02 have short smoke status; 03-06 have explicit TODO/deferred status. |

## 3. Per-Case Smoke Readiness Matrix

### 01: `01_1D_Consolidation`

| Field | Status |
|---|---|
| Current state | Existing pressure-only baseline; self-weight diagnostic history and SW3h long result archived. |
| Short runnable? | Yes. |
| Missing features | None for pressure-only baseline. Strict coupled Terzaghi still needs better external loading and boundary treatment. |
| Minimum smoke test | CPU Debug short run: `code=0`, `excluded=0`, `SavePorePressure` fields present, pressure-only trend not obviously broken. |
| Blocks GPU G1? | Yes as the primary pressure-only regression anchor. It is already available. |

### 02: `02_SelfWeight_Consolidation`

| Field | Status |
|---|---|
| Current state | Scenario 1 Stage A/B and Scenario 2 formal smoke files exist. Latest CPU Release smoke passed for Stage A, Stage B restart, and Scenario 2 short copy. |
| Short runnable? | Yes for Scenario 1 Stage A/B and Scenario 2, assuming current CPU tools are built. |
| Missing features | Formal smoke summary and cleanup of generated Stage run directories; no further long CPU runs needed. |
| Minimum smoke test | Stage A: body gravity on, positive excess generation, `code=0`, `excluded=0`. Stage B: restart reads `PorePress`, body gravity off/hydraulic gravity on, top drained active, `code=0`, `excluded=0`, no obvious restart impulse. Scenario 2: short gravity-on run, top drained/no-flux stable. |
| Blocks GPU G1? | No, after recorded smoke status. It does not require more CPU parameter tuning. |

### 03: `03_Cryer_Problem`

| Field | Status |
|---|---|
| Current state | README, notes, and TODO XML scaffold exist. |
| Short runnable? | Not yet. |
| Missing features | 3D/spherical or axisymmetric geometry, drained boundary treatment, pore-pressure ghost/MLS or equivalent boundary strategy, analytical postprocessing, likely GPU for useful resolution. |
| Minimum smoke test | For now: GenCase-only or TODO XML parse status with explicit unsupported notes. Future CPU smoke: coarse geometry, bounded pressure, symmetry preserved, no NaN/excluded. |
| Blocks GPU G1? | No. It should remain TODO until PR core GPU and boundary decisions mature. |

### 04: `04_Undrained_Triaxial`

| Field | Status |
|---|---|
| Current state | README, notes, and TODO XML scaffold exist. |
| Short runnable? | Not yet. |
| Missing features | Axial strain or stress control, confinement/lateral stress boundary, stress-path output (`p'`, `q`), and possibly MCC if strict material reproduction is required. Current DP can only be an approximate smoke path. |
| Minimum smoke test | Future CPU smoke should use tiny strain, `code=0`, `excluded=0`, correct pore-pressure sign, and bounded stress-path outputs. |
| Blocks GPU G1? | No. Loading/control and constitutive choices are case-specific and should not block PR core GPU. |

### 05: `05_Retrogressive_Slope`

| Field | Status |
|---|---|
| Current state | README, notes, and TODO XML scaffold exist. |
| Short runnable? | Not meaningfully yet. |
| Missing features | Sensitive clay / strain-softening model, robust large-deformation settings, pore-pressure initial/boundary strategy, GPU kernels, and postfailure monitoring. |
| Minimum smoke test | Future coarse CPU/GPU smoke: `code=0`, `excluded=0` for a tiny time window, key fields written, no immediate numerical blow-up. |
| Blocks GPU G1? | No. This is a post-GPU application benchmark. |

### 06: `06_Sainte_Monique`

| Field | Status |
|---|---|
| Current state | README, notes, and TODO XML scaffold exist. |
| Short runnable? | No. |
| Missing features | Field geometry/topography, material zoning, sensitive clay calibration, initial stress and pore-pressure state, GPU implementation, checkpoint/restart workflow. |
| Minimum smoke test | Future: geometry-only GenCase check, dry tiny run, then hydromechanical short run after smaller cases pass. |
| Blocks GPU G1? | No. Full field reproduction is a final target. |

## 4. Required Before GPU G1

The following should be complete, committed, or explicitly deferred before
starting CUDA implementation.

| Requirement | Status / decision |
|---|---|
| `PorePress` restart | Complete. |
| Scenario 1 route | Complete at smoke level through staged restart and/or `BodyGravityStopTime`; formalize the XML/BAT and record status. |
| Case scaffold/smoke matrix | Complete for pre-GPU gate: 01 and 02 smoke status recorded; 03-06 are explicitly documented as TODO/deferred scaffolds. |
| Failed diagnostic cleanup | `PorePressureAccelSymCorr` removed; keep `PorePressureAccel` only as optional symmetric compatibility diagnostic. |
| Deprecated source loading cleanup | Complete: source-side `TopLoad*` and `ApplyTopLoad()` removed; formal external-load path is `AccInput`. |
| Boundary ghost production decision | Simple ghost Laplacian remains diagnostic-only; production stays material-only + layer correction for G1-G4. |
| Corrected-gradient production decision | Corrected diagnostics remain CPU-only; G1-G4 ports current uncorrected PR operators. |
| Common utility stability | Common formatting fix should be committed separately from hydromech physics changes. |

GPU G1 should not start until the above list is either complete or explicitly
deferred in this file and `gpu_port_plan.md`.

## 5. Work That Can Happen After GPU G1-G4

These items are important for strict paper reproduction but should not block
the first PR core GPU port.

| Deferred item | Reason |
|---|---|
| Modified Cam Clay | Constitutive/model-specific; needed only if strict triaxial material matching requires MCC. |
| Sensitive clay / strain softening | Required for retrogressive slope and Sainte-Monique, but not for PR core GPU arrays. |
| Sainte-Monique full field run | Requires GPU, geometry, zoning, calibration, and restart workflow. |
| High-resolution Cryer | Needs GPU and stricter boundary treatment; coarse scaffold can remain TODO. |
| Long-time parameter sensitivity | Should be done on GPU after CPU/GPU parity, not on CPU. |
| Production boundary MLS/mirror operator | Needs a better design than CPU-BG3 simple ghost; can be a later CPU/GPU feature branch. |
| Corrected-gradient production PR operators | CPU-CG1 did not justify promotion; revisit only with targeted linear-field/boundary tests. |

## 6. Recommended Next Sequence

### A. Commit and organize current CPU nodes

Before new feature work:

1. Confirm commits exist for:
   - `PorePress` restart;
   - `BodyGravityStopTime`;
   - boundary ghost diagnostics;
   - corrected-gradient PR diagnostics;
   - common formatting / `snprintf` fix;
   - `TopLoad*` cleanup.
2. Check `git status --short`.
3. Keep source cleanup commits separate from case scaffold commits where possible.

### B. Formalize 02 SelfWeight Scenario 1/2 XML/BAT

Actions:

1. Keep Scenario 1 Stage A/B as formal staged smoke templates.
2. Keep Scenario 2 as the gravity-on smoke/diagnostic template.
3. Add or update README notes with:
   - required smoke duration;
   - expected sign/trend;
   - no long CPU tuning policy.
4. Clean generated output directories from `02_SelfWeight_Consolidation`.

Exit standard:

```text
Scenario 1 Stage A/B short smoke: code=0, excluded=0, PorePress restart confirmed.
Scenario 2 short smoke: code=0, excluded=0, top drained/no-flux stable.
```

### C. Create or refine 03 Cryer minimal scaffold

Actions:

1. Keep `CaseCryer_PR_TODO_Def.xml` as TODO unless a valid coarse geometry is ready.
2. Add notes for geometry, boundary conditions, and analytical postprocessing.
3. Do not force a runnable simulation before boundary strategy is selected.

Exit standard:

```text
README/notes/TODO XML exist and clearly state missing features.
No GPU block.
```

### D. Create or refine 04 Triaxial minimal scaffold

Actions:

1. Keep `CaseUndrainedTriaxial_PR_TODO_Def.xml` as TODO.
2. Document axial loading, confinement, and stress-path output requirements.
3. Decide whether initial smoke will use DP approximation or wait for MCC design.

Exit standard:

```text
README/notes/TODO XML exist and loading/control gaps are explicit.
No GPU block.
```

### E. Keep 05/06 as README/TODO scaffolds

Actions:

1. Do not create runnable production XML for retrogressive slope or
   Sainte-Monique until GPU and constitutive model decisions mature.
2. Keep the missing-feature lists explicit.

Exit standard:

```text
Scaffold-only status is explicit.
No accidental long CPU runs.
```

### F. Verify `TopLoad*` cleanup

Actions:

1. Confirm no formal XML under `examples/u-pw` depends on source-side
   `TopLoad*`.
2. Keep archived experiments as history, or update only the specific AccInput
   smoke template if it must remain runnable.
3. Keep the documented result: formal external loading uses native `AccInput`
   or a future traction/loading-plate design.

Exit standard:

```text
No active source TopLoad path in CPU production code.
No formal XML requires TopLoad*.
```

### G. Re-evaluate GPU G1 start

Start GPU G1 only when:

1. 01 pressure-only smoke is still runnable.
2. 02 Scenario 1/2 short smoke status is recorded.
3. 03-06 scaffolds clearly say runnable vs TODO.
4. Production arrays/operators for G1-G4 are frozen:
   - `PorePress`
   - `PorePressRate`
   - `DivVel`
   - `LapPorePress`
   - `LapZ`
   - `PorePressureAccelDiff`
   - optional Shepard/damping later.
5. Deferred diagnostics are explicitly out of GPU G1-G4.

## 7. Current Recommendation

Do not start GPU coding yet.

The next productive work is a case-readiness pass:

1. Commit/organize the current CPU functionality and utility fixes.
2. Formalize `02_SelfWeight_Consolidation` smoke templates and notes.
3. Confirm `03-06` are clean TODO scaffolds with missing-feature lists.
4. Keep `TopLoad*` cleanup marked complete; do not port it to GPU.
5. Update the smoke matrix status.

After that, GPU G1 can start from a cleaner target: the current uncorrected
material-only PR path plus `PorePressureAccelDiff` feedback as the production
coupled operator.

## Phase 6 Smoke Matrix Update

Updated after CPU pre-GPU automation:

| Case | Pre-GPU status | Smoke/readiness result | GPU G1 blocking? |
| --- | --- | --- | --- |
| 01 1D pressure-only | Runnable regression anchor | Short pressure-only smoke passed: `code=0`, `excluded=0`, `PorePress`, `ExcessPorePress`, `PorePressRate`, `DivVel`, `LapPorePress`, and `LapZ` written. | No |
| 01 SW3h result | Historical CPU long-run diagnostic | Kept as documented result only; no further CPU long-run tuning in this pass. | No |
| 02 Scenario 1 | Formal Stage A/B restart smoke scaffold | Stage A passed; Stage B restart passed and restored `PorePress` for `1040/1040` particles with XML initialization skipped. | No |
| 02 Scenario 2 | Formal short smoke scaffold | Short Scenario 2 copy passed with `code=0`, `excluded=0`. | No |
| 03 Cryer | TODO scaffold | No run by design; missing geometry, drained pressure boundary, boundary ghost/MLS, corrected operator decision, analytical postprocessing, and likely GPU resolution. | No for passive G1; blocks strict Cryer reproduction only |
| 04 Undrained triaxial | TODO scaffold | No run by design; missing axial control, confinement, stress-path output, and possible MCC. | No for PR core G1; blocks triaxial reproduction only |
| 05 Retrogressive slope | TODO scaffold | No run by design; requires sensitive clay/softening, large-deformation stability, initial state, and GPU. | No for PR core G1; post-GPU/material-model target |
| 06 Sainte-Monique | TODO scaffold | No run by design; requires field geometry, zoning, calibration, restart workflow, and GPU. | No for PR core G1; final application target |

Cleanup decisions now recorded:

- `TopLoad*` and `ApplyTopLoad()` are removed; formal external loading uses native `AccInput`.
- `PorePressureAccelSymCorr` is removed.
- Simple boundary ghost Laplacian remains diagnostic-only and is not promoted to production.
- Corrected-gradient PR diagnostics remain CPU-only and are not promoted to production.

Readiness judgment: CPU case readiness is sufficient to start **GPU G1 passive `PorePressg` planning/coding only**. This does not authorize the full GPU PR loop, feedback, boundary ghost production, corrected-gradient production, or long GPU reproduction runs.
