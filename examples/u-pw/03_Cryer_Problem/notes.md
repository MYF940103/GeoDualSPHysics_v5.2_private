# Notes: Cryer Problem

## Status

This directory has a reduced CPU smoke case plus a strict-reproduction TODO
placeholder. The smoke case is intended only to verify that the current u-pw PR
fields and mechanics can run in a Cryer-labeled scaffold without crashing.

Reduced execution smoke is not strict reproduction. The strict Cryer path still
requires paper geometry, a drained curved boundary, pore-pressure ghost / MLS or
an equivalent boundary treatment, and center-pressure analytical
postprocessing. These gaps remain GPU-pre blockers under the current full CPU
completion standard unless explicitly deferred.

## Parameters

Known paper-specific Cryer values were not complete in the current notes. The
reduced smoke therefore uses the standard 1D consolidation material constants
already used in the u-pw development cases:

- `E = 2e6 Pa`
- `nu = 0.3`
- `Porosity0 = 0.3`
- `HydraulicConductivity = 1e-3 m/s`
- `WaterBulkModulus = 2e8 Pa`
- `WaterDensity = 1000 kg/m3`

Unknown strict Cryer parameters remain TODO:

- specimen radius / exact geometry;
- drainage boundary definition;
- analytical center-pressure normalization;
- strict boundary operator choice.

## Boundary Approximation

The reduced smoke reuses the current layer-style hydraulic boundary tools. This
is acceptable for smoke only. It is not a strict drained spherical Cryer boundary.
Boundary ghost and corrected-gradient diagnostics are not promoted to production
operators.

## Smoke Readiness

Latest reduced smoke status is recorded in `smoke_status.md`.
