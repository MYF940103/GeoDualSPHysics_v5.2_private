# Final CPU Strict Smoke Completion Report

Date: 2026-05-11

## Scope

This report closes the CPU-only strict/minimal smoke pass before any GPU work.
No GPU source, CUDA kernel, GPU memory path, or GPU build was modified or run.

This pass does not claim full paper-level reproduction. It upgrades the paper
case directories from empty/TODO-only scaffolds to short CPU execution smokes
where possible, with the remaining strict reproduction gaps explicit.

## Commits Created In This Pass

| Commit | Purpose |
|---|---|
| `1d03468` | Start autonomous strict CPU smoke completion run. |
| `2cc452a` | Add Cryer-like strict CPU smoke scaffold and center-pressure analysis. |
| `4085086` | Add undrained triaxial CPU smoke workflow and stress-path proxy analysis. |
| `a3219b8` | Add retrogressive slope CPU smoke workflow and displacement summary. |
| `696a824` | Add Sainte-Monique reduced CPU smoke scaffold and field-like summary. |
| `17b4cbb` - `fed3e2b` | Audit, plan, implement, and smoke-test CPU DP-based sensitive-clay softening. |

## Case Smoke Matrix

| Case | Smoke type | Run status | Key outputs | Strict reproduction gaps | GPU blocker? |
|---|---|---|---|---|---|
| 01 1D consolidation | Pressure-only regression and historical SW3h result | Previously passed in the extended pre-GPU sanity pass: `code=0`, `excluded=0`. No new long run in this pass. | `PorePress`, `ExcessPorePress`, `PorePressRate`, `DivVel`, `LapPorePress`, `LapZ`, `PorePressureAccelDiff`. | Full long-time parameter tuning is deferred. | No for passive G1. |
| 02 Self-weight consolidation | Scenario 1 staged restart and Scenario 2 short smoke | Previously passed: Stage A/B restart restored `PorePress`, Scenario 2 micro smoke `code=0`, `excluded=0`. No new long run in this pass. | Restarted `PorePress`, top drained, bottom no-flux, PR fields. | Long-time paper curve tuning remains GPU/post-GPU work. | No for passive G1. |
| 03 Cryer problem | Reduced Cryer-like PR execution smoke | GenCase `code=0`, DualSPHysics `code=0`, `excluded=0`, no NaN/Inf. | Center-pressure proxy, min/max pore pressure, PR field output. | Strict sphere/axisymmetric geometry, drained spherical pressure boundary, center analytical comparison, and boundary MLS remain missing. | No for passive G1; yes for strict Cryer reproduction. |
| 04 Undrained triaxial | Reduced DP/u-pw AccInput execution smoke | GenCase `code=0`, DualSPHysics `code=0`, `excluded=0`, no NaN/Inf. | Approximate axial strain, mean pore pressure, p'/q proxy from stress fields, loading health. | Strict axial strain/stress control, confinement boundary, MCC calibration, and validated stress path remain missing. | No for passive G1; yes for strict triaxial reproduction. |
| 05 Retrogressive slope | Reduced 3D wedge/slope execution smoke plus CPU softening smoke | GenCase `code=0`, DualSPHysics `code=0`, `excluded=0`, no NaN/Inf. The softening-on/off reduced smoke pair also passed. | Displacement, velocity, pore-pressure range, `Kplastic` range, reconstructed local cohesion from `Kplastic`. | Full remolding/destructuration, validated initial state, production boundary model, calibrated parameters, and large-deformation validation remain missing. | No for passive G1; yes for strict slope reproduction. |
| 06 Sainte-Monique | Reduced synthetic field-like execution smoke | GenCase `code=0`, DualSPHysics `code=0`, `excluded=0`, no NaN/Inf. | Displacement, velocity, pore-pressure range, `PorePressRate`, `DivVel`, `Kplastic`. | Field topography, material zoning, calibration, initial stress/pore-pressure state, and full field workflow remain data/material/GPU blocked. | No for passive G1; yes for field reproduction. |

## Source Features Complete

- CPU PR pressure-only path with double `PorePress`.
- Full PR rate with corrected compression-positive `-DivVel` volumetric term.
- `PorePressureFeedbackMode=1` excess feedback.
- `PorePressureFeedbackOperator=1` difference-gradient feedback.
- `PorePressureShepard` regularization and `PorePressureShepardMode=1`.
- `HydromechDampingXi` paper-style damping input.
- `BodyGravityStopTime`.
- CPU `PorePress` restart.
- CPU Drucker-Prager exponential softening controlled by the soil parameter
  `Softening`, using `Kplastic` with peak/residual `coh`/`phi` evolution.
- Boundary ghost and corrected-gradient PR diagnostics, both diagnostic-only.
- Removed failed `PorePressureAccelSymCorr`.
- Removed deprecated source-side `TopLoad*`; external loading path is native `AccInput`.

## Deferred Features

The following remain deferred and must not be silently treated as completed:

- Production pore-pressure boundary MLS/mirror/ghost operator.
- Production corrected-gradient PR operators.
- Modified Cam Clay for strict triaxial matching.
- Full sensitive-clay remolding/destructuration and calibrated field-scale
  material workflow for slope and field cases. A reduced CPU DP softening path
  is implemented and smoke-tested, but full strict reproduction remains open.
- Strict Cryer geometry and analytical center-pressure reproduction.
- Strict triaxial confinement/loading/stress-path validation.
- Sainte-Monique field topography, material zoning, and calibration.
- High-resolution and long-time parameter sensitivity.

## Readiness Judgment

Full strict paper reproduction complete: **No**.

CPU strict/minimal smoke gate complete: **Yes, for the current reduced/minimal
CPU smoke definition**. Every paper-case directory now has either a short
CPU-runnable smoke with recorded output summaries or an explicit data/material
blocker. Reduced smoke is not strict reproduction complete.

GPU G1 passive `PorePressg` allowed: **Yes, narrowly**.

Allowed G1 scope:

- Passive GPU `PorePress` allocation/free/resize.
- Sorting and periodic duplicate support for passive `PorePress`.
- Output of GPU `PorePress`/`ExcessPorePress`.
- One-frame hydrostatic or restart parity checks.

Explicitly forbidden next scope:

- No GPU PR rate.
- No GPU feedback.
- No GPU Shepard or damping.
- No GPU boundary ghost.
- No long GPU run.
- No CUDA production operator changes beyond passive `PorePressg` plumbing.
