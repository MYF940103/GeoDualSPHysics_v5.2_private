# 03 Cryer Problem

Reduced launch workflow and CPU smoke scaffold for the PR-formulation Cryer benchmark.

This directory now contains a runnable **Cryer-like strict/minimal smoke** case.
It is not a strict Cryer reproduction because the exact paper geometry/radius
and particle-consistent drained curved boundary treatment are still TODO.

It also contains an example-style **baseline launch workflow** for manual CPU/GPU
Release reruns. This workflow is intended to make Cryer setup exploration
reproducible before strict analytical reproduction is attempted.

## Files

- `CaseCryer_PR_Smoke_Def.xml`: reduced 2D column-style smoke using u-pw PR settings.
- `xCaseCryer_PR_Smoke_win64_CPU_debug.bat`: CPU Debug smoke runner.
- `CaseCryer_PR_Baseline_Def.xml`: reduced Cryer baseline launch XML using production `PorePressureBoundaryOperator=0`.
- `xCaseCryer_PR_Baseline_win64_CPU_release.bat`: example-style CPU Release workflow.
- `xCaseCryer_PR_Baseline_win64_GPU_release.bat`: example-style GPU Release workflow.
- `analyze_cryer_smoke.py`: near-center pore-pressure history helper.
- `cryer_smoke_center_pressure.csv`: latest smoke postprocessing summary.
- `CaseCryer_PR_TODO_Def.xml`: historical strict-reproduction placeholder.
- `smoke_status.md`: latest reduced smoke result.

## Current Status

- Cryer-like strict/minimal smoke is CPU runnable.
- Latest smoke: GenCase `code=0`, DualSPHysics `code=0`, `excluded=0`.
- Key pore-pressure fields are written.
- No NaN/Inf was detected in the generated `PartCsv_*.csv` files.
- The analysis helper reports a bounded near-center pore-pressure proxy.
- Baseline CPU/GPU Release BATs are prepared but were not run in C1-revised.
- Strict Cryer reproduction is still feature-blocked.

## Baseline Launch Workflow

The new baseline BATs follow the normal example pattern:

`GenCase -> DualSPHysics Release -> PartVTK`

CPU:

```bat
xCaseCryer_PR_Baseline_win64_CPU_release.bat
```

GPU:

```bat
xCaseCryer_PR_Baseline_win64_GPU_release.bat
```

The BATs generate complete raw output folders and complete fluid/material
particle VTK output for visualization. They do not run Python analysis, extract
selected frames, generate previews, or create metadata packages.

The baseline uses:

- `HydromechCoupling=1`
- `PorePressureModel=1`
- `SavePorePressure=1`
- `PorePressureBoundaryOperator=0`
- `PorePressureFeedback=1`
- `PorePressureFeedbackMode=1`
- `PorePressureFeedbackOperator=1`
- `PorePressureShepard=1`
- `PorePressureShepardInterval=10`
- `PorePressureShepardMode=1`
- `PorePressureDtSafety=0.20`

This remains a reduced workflow. It should not be cited as strict Cryer
analytical reproduction.

## Strict Reproduction Reclassification

This Cryer-like smoke must not be counted as strict Cryer reproduction complete.
It does not yet include the paper Cryer geometry, a drained spherical/curved
pore-pressure boundary, boundary ghost / MLS pressure reconstruction, or center
pore-pressure analytical postprocessing. Under the full CPU pre-GPU gate, Cryer
still blocks full strict reproduction until these gaps are implemented or
explicitly deferred.

## Missing Before Strict Cryer Reproduction

- Paper geometry/radius and exact benchmark parameters.
- 3D spherical or validated axisymmetric geometry.
- Drained pore-pressure boundary around the specimen.
- Pore-pressure ghost / MLS boundary treatment or another strict drained boundary strategy.
- Analytical center-pressure postprocessing.
- Likely GPU support for useful resolution.

## Minimum Future Strict Smoke Standard

A future strict smoke should be coarse and short:

- `code=0`;
- `excluded=0`;
- no NaN;
- pressure fields written;
- symmetric qualitative pressure response;
- center pore-pressure history available for later comparison.
