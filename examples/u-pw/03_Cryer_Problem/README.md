# 03 Cryer Problem

TODO scaffold for a PR-formulation Cryer consolidation benchmark.

This case is not yet runnable as a strict reproduction. It should remain a
planning/scaffold directory until the required boundary and operator features
are available.

## Current Status

- Status: TODO scaffold only.
- `CaseCryer_PR_TODO_Def.xml` is a placeholder, not a validated runnable case.
- No DualSPHysics smoke test is required at this stage.
- Do not force a run from this XML until geometry, pressure boundary treatment,
  and postprocessing are defined.

## Missing Before a Meaningful Smoke Test

- 3D spherical or axisymmetric geometry.
- Drained pore-pressure boundary around the specimen.
- Pore-pressure ghost / MLS boundary treatment.
- Decision on corrected-gradient PR operators.
- Analytical center-pressure postprocessing.
- GPU support for useful resolution.

## Minimum Future Smoke Standard

The first real smoke test should be coarse and short:

- `code=0`;
- `excluded=0`;
- no NaN;
- pressure fields written;
- symmetric qualitative pressure response;
- center pore-pressure history available for later comparison.
