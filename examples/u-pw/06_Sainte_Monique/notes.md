# Notes: Sainte-Monique

## Current Purpose

`CaseSainteMonique_PR_ReducedSmoke_Def.xml` is a synthetic reduced geometry used
only to keep the final field-case directory smoke-testable before GPU work.

It does not contain Sainte-Monique topography, material zoning, or calibrated
sensitive clay parameters.

This is a reduced placeholder smoke only. It is not a validated field
reproduction and should not be counted as strict CPU completion before GPU
unless the field data and material-model requirements are explicitly deferred.

## Current Setup

- Synthetic coarse 3D field-like slope geometry.
- Body gravity and hydraulic gravity are both `(0,0,-9.81)`.
- `PorePressureInit=1` with a fully saturated placeholder water level.
- `PorePressureModel=1` and `SavePorePressure=1`.
- `PorePressureFeedback=0` in the first reduced smoke.
- Current material model is Drucker-Prager, not calibrated sensitive clay.

## Paper Parameters Extracted From Main PDF

The converted main-paper text provides Table 1 values:

- initial interparticle distance `0.6 m`;
- smoothing length factor `1.5`;
- artificial viscosity parameters `0.1` and `0.0`;
- damping coefficient `1.0e-5`;
- mixture density `1700 kg/m3`;
- porosity `0.2`;
- `E=13 MPa`;
- `nu=0.33`;
- `Kw=200 MPa`;
- peak/residual friction `10/0 deg`;
- peak/residual cohesion `45/1 kPa`;
- permeability `k=1e-8 m/s`;
- softening coefficients `2`, `5`, `10`.

The paper reports a runout around `52 m` compared with field `50 m` and a
retrogression distance around `116 m` compared with field `100 m` for one
chosen softening line. The field topography itself is not available in this
repository.

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
