# Notes: Cryer Problem

## Status

This directory is scaffold-only. The placeholder XML is intentionally marked as
TODO and should not be interpreted as a validated runnable reproduction.

## Missing Before Strict Reproduction

- 3D spherical or axisymmetric geometry.
- Drained pore pressure boundary around the specimen.
- Pore-pressure ghost / MLS boundary treatment.
- Corrected-gradient PR operator decision for strict boundary consistency.
- Analytical solution and center-pressure postprocessing.
- Likely GPU support for useful resolution.

## Smoke Readiness

No GenCase or DualSPHysics run was executed during the pre-GPU readiness pass.
This is intentional: the placeholder XML does not yet define the benchmark
geometry or boundary conditions.

A future minimal smoke test should use a coarse geometry, verify `code=0`,
`excluded=0`, no NaN, pressure-output availability, and a qualitatively symmetric
response. It should not attempt a strict analytical Cryer comparison until the
boundary treatment is promoted beyond the current layer/diagnostic-only state.
