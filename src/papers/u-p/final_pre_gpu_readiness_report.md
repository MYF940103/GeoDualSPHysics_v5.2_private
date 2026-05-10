# Final Pre-GPU Readiness Report

Generated: 2026-05-11

## Decision

**Not ready for GPU G1 under the current full CPU reproduction gate.**

GPU planning is documented, but this automation run does not authorize GPU
coding. The current user-defined gate requires paper-case CPU readiness before
GPU work. Reduced execution smokes are useful diagnostics, but they are not
strict reproduction completion.

## Commits Created In This Automation

| Commit | Purpose |
|---|---|
| `198bad0` | Start autonomous pre-GPU completion run. |
| `b8d5cad` | Ingest u-pw reference documents for reproduction planning. |
| `a006f68` | Update u-pw case audit from available references. |
| `5799086` | Refresh CPU case smoke readiness matrix. |
| `d230c6d` | Finalize CPU interface cleanup before GPU. |
| `0d9e726` | Update pre-GPU readiness gate. |
| `557b389` | Record final CPU smoke status before GPU. |

All commits above were pushed to `origin/u-p`.

## Source Features Already Complete

- CPU PR pore-pressure state, rate diagnostics, and output.
- Compression-positive volumetric sign in PR pressure rate:
  `PorePressRate = Kw/n * (-DivVel + diffusion + elevation)`.
- `dt_pore` restriction.
- `PorePressureFeedbackMode=1` excess feedback.
- `PorePressureFeedbackOperator=1` difference-gradient feedback.
- `PorePressureShepard` and `PorePressureShepardMode=1`.
- `HydromechDampingXi` with Supporting Information style conversion.
- Hydromechanical material constants moved to `StSoilCte`.
- `BodyGravityStopTime`.
- CPU `PorePress` restart.
- `PorePressureModel=2` hard error for unsupported PPE.
- Source-side `TopLoad*` and `ApplyTopLoad()` removed.
- Failed `PorePressureAccelSymCorr` diagnostic removed.
- Boundary ghost and corrected-gradient PR paths retained as diagnostics only.

## Build And Smoke Status

CPU Debug rebuild succeeded:

```powershell
msbuild .\src\VS\DualSPHysics5ReCpu_vs2022.sln /m /t:Build /p:Configuration=DebugCPU /p:Platform=x64 /v:minimal
```

The final short smoke sanity set was attempted, but exceeded the allowed
automation runtime budget and was stopped after about 30 minutes. Temporary
`_autopregpu_smoke` generated output folders were removed. No new smoke result
from that attempt is accepted.

This does not change earlier smoke evidence; it simply prevents this automation
run from declaring a clean pre-GPU smoke pass.

## Case Readiness Table

| Case | Current CPU status | Strict reproduction status | GPU gate impact |
|---|---|---|---|
| 01 1D consolidation / Terzaghi | pressure-only baseline and historical long-run anchors exist | coupled external-load strict Terzaghi still needs cleaner boundary/loading validation | partially blocks full-paper gate |
| 02 self-weight consolidation | Scenario 1/2 CPU workflows and restart route exist | closest case to strict reproduction; still needs stricter boundary/postprocessing validation | not the main blocker |
| 03 Cryer problem | reduced/scaffold smoke only | missing strict sphere/traction geometry, drained curved boundary, center-pressure postprocessing | blocks full-paper gate |
| 04 undrained triaxial | reduced/scaffold smoke only | missing axial loading/control, lateral confinement, `p'`-`q` postprocessing, MCC/material calibration | blocks full-paper gate |
| 05 retrogressive slope | reduced/scaffold smoke only | missing sensitive clay / strain softening, initial state, validated large deformation workflow | blocks full-paper gate |
| 06 Sainte-Monique | placeholder/reduced scaffold only | missing field topography, material zoning, calibration, initial state, production workflow | blocks full-paper gate |

## Deferred Items

Deferred items that are not part of passive GPU G1, but still matter for strict
paper reproduction:

- production pore-pressure boundary ghost / MLS or equivalent boundary operator;
- production corrected-gradient PR operators, if later evidence shows they are
  needed;
- Cryer strict geometry, boundary, and analytical postprocessing;
- triaxial axial/confinement loading and stress-path postprocessing;
- Modified Cam Clay if strict triaxial reproduction requires it;
- sensitive clay / strain-softening model for slope and field cases;
- Sainte-Monique field data, zoning, calibration, and restart workflow;
- long-time parameter sensitivity and high-resolution production runs.

## Output Cleanup

Generated outputs from the final smoke attempt were removed:

- `examples/u-pw/01_1D_Consolidation/_autopregpu_smoke`
- `examples/u-pw/02_SelfWeight_Consolidation/_autopregpu_smoke`

No formal XML/BAT/README/notes/scripts/SVG/summary CSV files were deleted.

## GPU Scope Recommendation

Current recommendation: **do not start GPU G1 yet**.

The passive GPU plan remains technically scoped, but is not authorized by the
current full CPU case completion gate. If the gate is later relaxed, the only
allowed first GPU scope should be:

- passive `PorePressg` allocation/free/resize;
- sorting and periodic duplicate handling for `PorePressg`;
- output of `PorePress` / `ExcessPorePress`;
- one-frame hydrostatic parity check.

Explicitly forbidden next GPU scope:

- no GPU PR rate;
- no GPU feedback;
- no GPU Shepard or damping;
- no GPU boundary ghost;
- no long GPU run.

## Final Statement

Reduced smoke is not strict reproduction complete. Under the current standard,
GPU G1 remains blocked until the paper-case CPU readiness gaps are either
implemented or explicitly deferred by a revised gate.
