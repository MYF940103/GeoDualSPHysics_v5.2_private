# 03 Cryer Problem

Reduced CPU smoke scaffold for the PR-formulation Cryer benchmark.

This directory now contains a runnable **Cryer-like strict/minimal smoke** case.
It is not a strict Cryer reproduction because the exact paper geometry/radius
and particle-consistent drained curved boundary treatment are still TODO.

## Files

- `CaseCryer_PR_Smoke_Def.xml`: reduced 2D column-style smoke using u-pw PR settings.
- `xCaseCryer_PR_Smoke_win64_CPU_debug.bat`: CPU Debug smoke runner.
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
- Strict Cryer reproduction is still feature-blocked.

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
