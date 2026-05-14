# L3d Future Mechanical Loading Plan

Date: 2026-05-14

## Why L3d Is Deferred

L2 and L3b both finished stably, but both produced dynamic pressure peaks near
`6e5 Pa` for a target `10 kPa` surcharge. This shows that the missing piece is
not a simple execution or CPU/GPU stability issue. The strict route needs a
paper-faithful mechanical loading method, not a damping sweep.

L3c already provides the clean PR diffusion and initial-state validation gate.
That reduces the urgency of mechanical load-generation work unless strict
paper reproduction of the loading stage is the active priority.

## Candidate Route 1: Quasi-Static Loading Plate

Concept:

- represent a top loading plate or boundary layer;
- apply load gradually or force-control it so the specimen approaches the
  target surcharge without a material-row impulse;
- use reaction diagnostics to confirm applied force.

Source needs:

- force-controlled plate or actuator abstraction;
- top plate force diagnostic;
- clear separation between plate constraint force and pore-pressure response;
- CPU-first implementation.

No-go criteria:

- excess pressure peak remains orders of magnitude above `10 kPa`;
- top drained or bottom no-flux residual becomes large;
- velocity/DivVel bursts dominate the pressure response.

## Candidate Route 2: True Surface Traction Boundary

Concept:

- apply traction as a boundary condition, not as body acceleration on material
  particles;
- distribute the load consistently over the top surface support.

Source needs:

- top-surface selector;
- traction-to-particle projection with area weighting;
- diagnostics for applied force and surface velocity;
- GPU deferred until CPU behavior is acceptable.

Risk:

- if implemented as a direct material force, it may repeat L3b dynamics.

## Candidate Route 3: Total-Stress Initializer

Concept:

- initialize pore pressure and effective/total stress consistently;
- avoid dynamic load generation;
- then run drainage.

Source needs:

- vertical or tensor initial stress fields, not just isotropic effective stress;
- optional z/mk targeting;
- clear sign convention;
- CPU/GPU initialization parity plan.

Scope caveat:

- this validates an initial-value problem rather than mechanical loading
  generation, but it may be a cleaner strict paper-comparison route than a
  dynamic top load.

## Diagnostics Required

Any L3d route should output:

- applied force or stress;
- top surface displacement/velocity;
- generated initial excess pressure;
- top drained residual;
- bottom no-flux proxy;
- bottom/profile analytical RMSE;
- velocity, DivVel, and PorePressRate indicators;
- CPU/GPU support status.

## Recommendation

Do not prioritize L3d immediately unless strict mechanical loading reproduction
is needed for the next milestone. Use L3c for current PR diffusion/boundary
validation and move to the next u-p module if that coverage is sufficient.
