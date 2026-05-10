# Autonomous Strict CPU Smoke Run Log

Date: 2026-05-11

## Current Commit

`696a824` - `Add Sainte-Monique reduced CPU smoke scaffold`

## Goal

Continue CPU-only pre-GPU work from the previous readiness pass. The previous
pass confirmed 01/02 micro smoke readiness, but 03-06 remained reduced/scaffold
cases. This run does not accept a TODO-only state as completion.

## Hard Scope

- No GPU coding.
- No `JSphGpu*`, `JCellDivGpu*`, `.cu`, CUDA kernel, or GPU build changes.
- No CPU long-time reproduction or parameter sweeps.
- Every run must be short. A single run over 90 minutes is stopped and recorded
  as deferred.
- Generated outputs are removed after extracting smoke summaries.

## Starting Case State

| Case | Starting state |
|---|---|
| 03 Cryer | Reduced runnable smoke exists; strict geometry/boundary/postprocessing still missing. |
| 04 Undrained triaxial | Reduced AccInput smoke exists; strict confinement/loading/MCC still missing. |
| 05 Retrogressive slope | Reduced slope smoke exists; sensitive clay / softening still missing. |
| 06 Sainte-Monique | Reduced field-like placeholder exists; field data/zoning/calibration still missing. |

## Planned Automatic Steps

1. Re-run and update 03 Cryer-like CPU smoke, adding a center-pressure analysis
   helper if needed.
2. Re-run and update 04 triaxial CPU smoke and postprocessing status.
3. Re-run and update 05 retrogressive slope reduced CPU smoke.
4. Re-run and update 06 Sainte-Monique reduced placeholder smoke.
5. Update the global smoke matrix and final strict-smoke completion report.

## Readiness Philosophy

These smokes are stricter than empty TODO scaffolds because they exercise
geometry, GenCase, DualSPHysics, hydromechanical fields, and postprocessing
paths. They are still not full paper reproduction curves. Any remaining strict
reproduction gaps must stay explicit in README, notes, and the final report.

## Completed Automatic Steps

| Case | Result |
|---|---|
| 03 Cryer | Re-ran reduced Cryer-like PR smoke, added `analyze_cryer_smoke.py`, recorded center-pressure proxy summary, cleaned generated output, committed `2cc452a`. |
| 04 Undrained triaxial | Re-ran reduced AccInput triaxial smoke, upgraded stress-path proxy script, recorded `triaxial_smoke_summary.csv`, cleaned generated output, committed `4085086`. |
| 05 Retrogressive slope | Re-ran reduced wedge/slope smoke, added `analyze_slope_smoke.py`, recorded displacement/velocity/pore-pressure summary, cleaned generated output, committed `a3219b8`. |
| 06 Sainte-Monique | Re-ran reduced field-like smoke, added `analyze_sainte_smoke.py`, recorded `sainte_smoke_summary.csv`, cleaned generated output, committed `696a824`. |

No GPU source files, CUDA kernels, GPU builds, or GPU runs were touched.
