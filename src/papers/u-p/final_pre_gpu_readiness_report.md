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
| `139c359` | Add final pre-GPU readiness report. |

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
- CPU reduced DP-based sensitive-clay softening implemented for 05 reduced
  slope smokes through the soil parameter `Softening`.

## Build And Smoke Status

CPU Debug rebuild succeeded:

```powershell
msbuild .\src\VS\DualSPHysics5ReCpu_vs2022.sln /m /t:Build /p:Configuration=DebugCPU /p:Platform=x64 /v:minimal
```

The final CPU smoke sanity set was rerun with the user-approved extended timeout
budget. All requested 01/02 micro smokes completed:

| Smoke | GenCase | DualSPHysics | Excluded | Runtime | Key fields | Notes |
|---|---:|---:|---:|---:|---|---|
| 01 pressure-only micro | 0 | 0 | 0 | 19.95 s | ok | Pore-pressure diagnostics written. |
| 02 Scenario 1 Stage A | 0 | 0 | 0 | 52.40 s | ok | Self-weight generation stage. |
| 02 Scenario 1 Stage B restart | 0 | 0 | 0 | 25.50 s | ok | `PorePress` restored from restart; XML init skipped. |
| 02 Scenario 2 micro | 0 | 0 | 0 | 80.69 s | ok | Gravity-on short dissipation smoke. |

No `NaN` / `Inf` tokens were detected in the generated `PartCsv_*.csv` files.
The required pore-pressure output fields were present.

This removes the previous automation smoke-timeout blocker, but it does not
complete the strict 03-06 paper-case reproduction gate.

## Case Readiness Table

| Case | Current CPU status | Strict reproduction status | GPU gate impact |
|---|---|---|---|
| 01 1D consolidation / Terzaghi | pressure-only baseline and historical long-run anchors exist | coupled external-load strict Terzaghi still needs cleaner boundary/loading validation | partially blocks full-paper gate |
| 02 self-weight consolidation | Scenario 1/2 CPU workflows and restart route exist | closest case to strict reproduction; still needs stricter boundary/postprocessing validation | not the main blocker |
| 03 Cryer problem | reduced/scaffold smoke only | missing strict sphere/traction geometry, drained curved boundary, center-pressure postprocessing | blocks full-paper gate |
| 04 undrained triaxial | reduced/scaffold smoke only | missing axial loading/control, lateral confinement, `p'`-`q` postprocessing, MCC/material calibration | blocks full-paper gate |
| 05 retrogressive slope | reduced/scaffold smoke plus reduced `Softening=1` CPU smoke | missing calibrated initial state, production boundary treatment, full remolding/destructuration decision, and validated large deformation workflow | blocks full-paper gate |
| 06 Sainte-Monique | placeholder/reduced scaffold only; CPU softening path available | missing field topography, material zoning, calibration, initial state, production workflow | blocks full-paper gate |

## Deferred Items

Deferred items that are not part of passive GPU G1, but still matter for strict
paper reproduction:

- production pore-pressure boundary ghost / MLS or equivalent boundary operator;
- production corrected-gradient PR operators, if later evidence shows they are
  needed;
- Cryer strict geometry, boundary, and analytical postprocessing;
- triaxial axial/confinement loading and stress-path postprocessing;
- Modified Cam Clay if strict triaxial reproduction requires it;
- GPU softening and any fuller remolding/destructuration material model for
  slope and field cases. CPU reduced DP-based softening is available, but it is
  not part of passive GPU G1;
- Sainte-Monique field data, zoning, calibration, and restart workflow;
- long-time parameter sensitivity and high-resolution production runs.

## Output Cleanup

Generated outputs from the final smoke attempt were removed after extracting the
summary above:

- `examples/u-pw/01_1D_Consolidation/_autopregpu_smoke`
- `examples/u-pw/02_SelfWeight_Consolidation/_autopregpu_smoke`

No formal XML/BAT/README/notes/scripts/SVG/summary CSV files were deleted.

## GPU Scope Recommendation

Current recommendation under the full CPU paper-case gate:
**do not start GPU G1 yet**.

The 01/02 CPU smoke sanity now passes, so the previous timeout-specific blocker
is gone. However, the passive GPU plan is still not authorized by the current
full CPU case completion gate because 03-06 remain reduced/scaffold-level rather
than strict reproduction smokes. If the gate is later relaxed, the only allowed
first GPU scope should be:

- passive `PorePressg` allocation/free/resize;
- sorting and periodic duplicate handling for `PorePressg`;
- output of `PorePress` / `ExcessPorePress`;
- one-frame hydrostatic parity check.

CPU softening does not change the passive G1 scope. GPU softening is explicitly
not included in G1.

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
