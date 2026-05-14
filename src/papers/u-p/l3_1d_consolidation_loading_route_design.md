# L3 1D Consolidation Loading Route Design

## Objective

L2 showed that a paper-aligned geometry/material setup is not enough when the
load route is a reduced `AccInput` acceleration on the top material layer.  L3
therefore splits the problem into hydraulic diffusion validation and mechanical
load-generation validation.

## Candidate Routes

### Route 1: Current AccInput Body-Force Route

Pros:

- already implemented;
- CPU/GPU-supported;
- stable in L2;
- maps `q0` to `a_z = -q0/(rho * thickness)` in a simple way.

Cons:

- body acceleration, not surface traction;
- acts on a finite material layer;
- excites stress waves and `DivVel`;
- produced `~6.25e5 Pa` excess peak for a `10 kPa` target in L2;
- should remain a reduced smoke route only.

### Route 2: Top Loading Plate / Prescribed Stress Route

Pros:

- closer to a physical surface load;
- can separate specimen material from load application;
- compatible with reaction diagnostics if implemented as a platen.

Cons:

- current XML motion gives prescribed displacement/velocity, not constant load;
- a force-controlled plate or surface traction needs a source design;
- CPU/GPU parity would need to be planned.

### Route 3: Initial Undrained Excess-Pressure Route

Pros:

- matches the analytical Terzaghi initial condition most directly;
- no mechanical loading waves;
- supported by existing `PorePressureInit=3`;
- CPU/GPU-supported for boundary mode `0`;
- best immediate gate for PR diffusion and hydraulic boundaries.

Cons:

- bypasses mechanical generation of pore pressure;
- with `PorePressureFeedback=0`, it tests PR diffusion storage, not the full
  coupled skeleton-storage Terzaghi problem;
- not a complete paper reproduction by itself.

### Route 4: Initial Effective Stress + Pore Pressure Consistent Route

Pros:

- closer to undrained load equilibrium;
- can represent total stress/effective stress/pore pressure consistency.

Cons:

- current `InitialStressMode=1` is only a uniform isotropic CPU path;
- a 1D surcharge-consistent stress state needs a clearer initialization design;
- likely source support and restart/output checks are needed.

### Route 5: Ramped Surface Load + Damping

Pros:

- can reduce dynamic waves once a real surface-load route exists;
- may be useful for a coupled generation stage.

Cons:

- damping/viscosity does not fix a non-traction load route;
- broad damping sweeps would obscure the main formulation blocker.

## Recommended L3 Route

Proceed with Route 3 as L3a:

- `PorePressureInit=3`;
- uniform initial excess `10 kPa`;
- top drained from initialization;
- bottom no-flux;
- no `AccInput`;
- `PorePressureFeedback=0`;
- CPU Release and GPU Release short/medium comparison.

In parallel, keep Route 2/4 as L3b planning:

- do not treat `AccInput` as strict loading;
- design a top loading plate or surface traction route;
- define diagnostics before implementation.

## No-Go for L3

- no Cryer boundary changes;
- no deprecated modes `5/6/7/8`;
- no PR governing-equation change;
- no broad damping or viscosity sweep before the loading route is fixed.
