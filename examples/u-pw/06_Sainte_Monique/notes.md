# Notes: Sainte-Monique

## Current Purpose

`CaseSainteMonique_PR_ReducedSmoke_Def.xml` is a synthetic reduced geometry used
only to keep the final field-case directory smoke-testable before GPU work.

It does not contain Sainte-Monique topography, material zoning, or calibrated
sensitive clay parameters.

## Current Setup

- Synthetic coarse 3D field-like slope geometry.
- Body gravity and hydraulic gravity are both `(0,0,-9.81)`.
- `PorePressureInit=1` with a fully saturated placeholder water level.
- `PorePressureModel=1` and `SavePorePressure=1`.
- `PorePressureFeedback=0` in the first reduced smoke.
- Current material model is Drucker-Prager, not calibrated sensitive clay.

## Data Blockers

See `data/README.md`. A validated reproduction needs:

- field topography / terrain surface;
- material zoning;
- sensitive clay parameters and remolding/softening law;
- groundwater or initial pore-pressure state;
- field boundary and drainage assumptions;
- validation data.

## Readiness Decision

The directory is no longer empty TODO-only: it has a reduced CPU smoke that
verifies geometry, PR pore-pressure fields, and output health.

Strict Sainte-Monique reproduction remains data-blocked and GPU/material-model
blocked. It should not be treated as a validated application case.
