# Pre-GPU Readiness Check

Generated: 2026-05-11

Current decision: **Not ready for GPU G1 under the full CPU reproduction gate.**

## Completed Required CPU Infrastructure

The following GPU-pre infrastructure items are complete:

- `PorePress` double state and output;
- PR pressure-rate path with corrected compression-positive volumetric sign;
- `dt_pore`;
- `PorePressureFeedbackMode=1` and `PorePressureFeedbackOperator=1`;
- `PorePressureShepard`;
- `HydromechDampingXi`;
- hydromech material constants in `StSoilCte`;
- `BodyGravityStopTime`;
- CPU `PorePress` restart;
- source-side `TopLoad*` removed;
- `PorePressureAccelSymCorr` removed;
- PPE placeholder is a hard error.

## Completed But Diagnostic-Only

These features are available as diagnostics or research paths only:

- boundary ghost pressure and ghost Laplacian diagnostics;
- corrected-gradient PR diagnostics;
- symmetric pore-pressure acceleration compatibility diagnostic.

They are not production operators and should not be ported to GPU G1.

## GPU G1 Must Still Wait

The stricter gate defined by the user requires paper-case CPU readiness, not
only reduced execution smokes. The following strict reproduction blockers remain:

| Area | Blocking issue |
|---|---|
| 03 Cryer | strict sphere/traction geometry, drained curved boundary, pore-pressure ghost/MLS or equivalent, center-pressure analytical postprocessing. |
| 04 Triaxial | axial loading/control, lateral confinement, validated `p'`-`q` postprocessing, MCC support or documented DP approximation decision. |
| 05 Retrogressive slope | sensitive clay / strain softening, initial stress and pore-pressure workflow, non-horizontal boundary treatment, production GPU later. |
| 06 Sainte-Monique | field topography, material zoning, calibration, initial state, checkpoint/GPU workflow. |

## Deferred Items That Do Not Belong In Passive GPU G1

The following may be deferred from passive GPU storage design but still block
strict paper reproduction:

- production boundary MLS/mirror operator;
- production corrected-gradient PR operators;
- MCC implementation;
- sensitive clay / strain-softening implementation;
- high-resolution Cryer;
- field Sainte-Monique;
- long-time parameter sensitivity.

## Case Readiness Summary

| Case | Reduced smoke status | Strict reproduction status |
|---|---|---|
| 01 pressure-only / Terzaghi | pressure-only baseline exists | coupled external-load strict reproduction still needs loading/boundary work. |
| 02 self-weight | Scenario 1/2 short workflows exist | closest to strict, but boundary/postprocessing still needs finalization. |
| 03 Cryer | reduced smoke exists | not strict; boundary/geometry/postprocessing blocked. |
| 04 triaxial | reduced smoke exists | not strict; loading/confinement/MCC blocked. |
| 05 retrogressive slope | reduced smoke exists | not strict; sensitive clay/initial-state/GPU blocked. |
| 06 Sainte-Monique | placeholder smoke exists | not strict; data/material/GPU blocked. |

## Final Build / Smoke Sanity

CPU Debug rebuild was executed on 2026-05-11 and completed successfully.

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

This removes the previous automation smoke-timeout blocker. It does not remove
the stricter paper-case blockers for 03-06.

## Final Readiness Judgment

GPU G1 passive `PorePressg` is technically well scoped in `gpu_port_plan.md`, but
it is **not authorized yet** under the current full CPU completion standard.

Next recommended CPU tasks:

1. implement or design a better production pore-pressure boundary route for
   planar/Cryer boundaries;
2. define a strict triaxial loading/confinement path;
3. add Cryer center-pressure and triaxial stress-path postprocessing;
4. decide which strict slope/field material-model blockers are explicitly
   deferred.
