# Full CPU Case Completion Report Before GPU

Date: 2026-05-10

## Scope

This report closes the CPU case-completion pass requested before any GPU work.
No CUDA, `JSphGpu*`, `JCellDivGpu*`, or `.cu` files were modified.

The goal was not long-time calibration or strict reproduction. The goal was to
ensure that all paper-case directories 01-06 have CPU smoke-ready XML/BAT/files
or explicit data/feature blockers.

## Commits Created In This Pass

| Commit | Purpose |
| --- | --- |
| `03cb076` | Define full CPU case completion gate before GPU |
| `da80604` | Add Cryer PR smoke case |
| `982e274` | Add undrained triaxial PR smoke case |
| `811524a` | Add retrogressive slope PR reduced smoke case |
| `022df90` | Add Sainte-Monique reduced smoke scaffold |
| `1732b95` | Update full CPU case smoke matrix |

## Completed CPU Case Smokes

| Case | XML exists | CPU smoke run | Code | Excluded | Strict-reproduction status |
| --- | --- | --- | --- | --- | --- |
| 01 1D consolidation / pressure-only | Yes | Yes | 0 | 0 | Pressure-only regression anchor complete; strict coupled external-load Terzaghi deferred. |
| 02 Self-weight consolidation Scenario 1/2 | Yes | Yes | 0 | 0 | Stage A/B restart and Scenario 2 short smoke complete; long tuning deferred. |
| 03 Cryer | Yes | Yes, reduced PR smoke | 0 | 0 | Strict Cryer remains geometry / drained-boundary / analytical-postprocessing blocked. |
| 04 Undrained triaxial | Yes | Yes, reduced DP/u-pw AccInput smoke | 0 | 0 | Strict triaxial remains loading / confinement / possible MCC blocked. |
| 05 Retrogressive slope | Yes | Yes, reduced 3D wedge smoke | 0 | 0 | Strict retrogression remains sensitive-clay / softening / GPU blocked. |
| 06 Sainte-Monique | Yes | Yes, reduced synthetic placeholder smoke | 0 | 0 | Validated field reproduction remains data / material / GPU blocked. |

## New Or Updated Case Files

### 03 Cryer

- `CaseCryer_PR_Smoke_Def.xml`
- `xCaseCryer_PR_Smoke_win64_CPU_debug.bat`
- `smoke_status.md`
- updated `README.md` and `notes.md`

### 04 Undrained Triaxial

- `CaseUndrainedTriaxial_PR_Smoke_Def.xml`
- `xCaseUndrainedTriaxial_PR_Smoke_win64_CPU_debug.bat`
- `TriaxialAxialAcc_m1.csv`
- `analyze_triaxial_smoke.py`
- `smoke_status.md`
- updated `README.md` and `notes.md`

### 05 Retrogressive Slope

- `CaseRetrogressiveSlope_PR_ReducedSmoke_Def.xml`
- `xCaseRetrogressiveSlope_PR_ReducedSmoke_win64_CPU_debug.bat`
- `smoke_status.md`
- updated `README.md` and `notes.md`

### 06 Sainte-Monique

- `CaseSainteMonique_PR_ReducedSmoke_Def.xml`
- `xCaseSainteMonique_PR_ReducedSmoke_win64_CPU_debug.bat`
- `data/README.md`
- `smoke_status.md`
- updated `README.md` and `notes.md`

## Smoke Metrics Summary

| Case | TimeMax | Material particles | Key result |
| --- | --- | --- | --- |
| 03 Cryer reduced | ~0.0005 s | 500-scale reduced setup | Required u-pw fields written; strict analytical behavior not claimed. |
| 04 Triaxial reduced | 0.001 s | 1000 | Tiny AccInput compression produced small positive excess pore pressure; fields written. |
| 05 Slope reduced | 0.0002 s | 602 | Gravity-driven wedge smoke ran with PR fields and no excluded particles. |
| 06 Sainte-Monique placeholder | 0.0002 s | 556 | Synthetic field-like placeholder ran with PR fields and no excluded particles. |

Generated outputs were removed after extracting smoke metrics.

## Deferred Features

These remain important but are not part of the CPU smoke gate:

- production pore-pressure boundary ghost / MLS;
- production corrected-gradient PR operators;
- strict external-load Terzaghi traction/loading plate;
- strict Cryer boundary and analytical comparison;
- triaxial confinement / axial-control boundary;
- Modified Cam Clay;
- sensitive clay / strain-softening / remolding law;
- Sainte-Monique field topography and material zoning;
- long-time parameter sensitivity and high-resolution runs.

## Frozen Production Scope For GPU G1-G4

The CPU production target for the first GPU stages remains:

- `PorePress`
- `PorePressRate`
- `DivVel`
- `LapPorePress`
- `LapZ`
- `PorePressureAccelDiff`
- current uncorrected material-only PR operators
- current layer-style top drained / bottom no-flux corrections for existing
  smoke cases
- optional later ports of Shepard and hydromechanical damping

Explicit exclusions:

- no `PorePressureAccelSymCorr`;
- no source-side `TopLoad*`;
- no production ghost-boundary Laplacian;
- no production corrected-gradient PR switch;
- no PPE;
- no full landslide material model in PR core GPU G1.

## GPU Readiness Decision

The full CPU case-smoke gate is now satisfied for the reduced/current smoke
scope: 01-06 all have runnable CPU smoke cases or, for strict reproduction,
clear data/feature blockers with a reduced smoke substitute.

Recommendation:

- GPU coding may start next only as **G1 passive `PorePressg`**.
- This does not authorize the full GPU PR loop, feedback, Shepard, damping,
  boundary ghost production, corrected-gradient production, or long GPU runs.
- Strict paper reproduction remains blocked until the deferred features above
  are designed and implemented in later CPU/GPU phases.

## Current Dirty-State Note

At report generation, `git status --short` still showed unrelated untracked
reference/example files outside the u-pw case-completion work, including legacy
example CSVs and reference source folders. They were intentionally not touched
or committed in this pass.
