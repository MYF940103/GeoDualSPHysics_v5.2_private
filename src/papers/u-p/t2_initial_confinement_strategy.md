# T2 Initial Confinement Strategy

## Problem

Strict triaxial compression begins from an isotropically confined specimen, then applies axial loading while lateral confinement is maintained. The current T1 baseline only exercises axial AccInput loading without true lateral confining pressure.

Zhao's verification shows that suddenly applying confinement without an equivalent initial hydrostatic stress can launch stress waves. The paper controls this with damping and also demonstrates that starting with the matching hydrostatic stress state gives immediate equilibrium.

## Route 1: Ramped Confinement Only

Description:

- start with zero material stress or the existing initial stress state;
- ramp `ConfiningStressP0` from zero to target;
- use damping until velocities decay;
- then begin axial loading.

Advantages:

- minimal source work;
- uses the current ramp helper;
- good first smoke for `f_i` and lateral selector diagnostics.

Risks:

- stress waves during ramp;
- pore-pressure response may include ramp artifacts;
- final stress state may not match a clean hydrostatic initialization;
- requires a staged workflow or careful timing in one XML.

## Route 2: Initial Hydrostatic Stress Plus Confinement Term

Description:

- initialize material stress tensor so the specimen starts at the confining pressure;
- enable the flexible confinement term to maintain boundary pressure;
- then apply axial loading.

Advantages:

- closest to Zhao's stable verification setup;
- cleaner strict triaxial initial condition;
- reduces artificial stress-wave equilibration.

Risks:

- needs explicit source/XML support for initializing stress tensor fields;
- must be reconciled with effective stress, pore pressure, and sign conventions;
- more invasive than a diagnostic T3 step.

## Route 3: Staged Workflow

Description:

1. isotropic confinement stage;
2. damping/equilibration stage;
3. axial compression stage;
4. postprocess only after equilibrium is reached.

This can be implemented later using restart or a single-run staged input if the code supports enough timing controls.

Advantages:

- most similar to laboratory workflow;
- allows diagnostics for confinement quality before axial loading;
- can support both ramp-only and initial-stress routes.

Risks:

- requires careful restart/stage design;
- longer runtime;
- more output management.

## T3 Recommendation

Start with Route 1 for a CPU-only diagnostic smoke:

1. add `f_i` diagnostics;
2. add lateral/cap classification diagnostics;
3. run confinement-only cylinder smoke with ramped `ConfiningStressP0`;
4. verify inward radial acceleration and low axial leakage;
5. only then run axial compression plus confinement.

Do not implement initial hydrostatic stress in T3 unless the diagnostic route shows that the existing pair term and lateral selector behave correctly. Route 2 should be the next source feature after confinement selection is validated.

## Damping

The first confinement-only smoke should use a documented damping setting and should report:

- velocity max decay;
- COM acceleration;
- radial displacement;
- stress-wave residual through pressure/stress oscillations;
- net confining force.

Damping is a stabilization/equilibration tool, not a replacement for correct lateral confinement.
