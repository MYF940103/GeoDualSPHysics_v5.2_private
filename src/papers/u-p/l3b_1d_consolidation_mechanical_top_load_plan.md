# L3b Mechanical Top-Load Plan for 1D Consolidation

## Why L3b Is Needed

L3a isolates the pressure-diffusion initial-value problem.  It does not verify
that GeoDualSPHysics can generate the Terzaghi initial excess pore pressure
through a paper-faithful mechanical surcharge.  L3b should address that second
piece.

## Preferred Mechanical Route

The preferred future route is a top loading plate or surface traction:

1. Create a distinct top load boundary or plate group.
2. Apply a force-controlled vertical load equivalent to `q0=-10 kPa`.
3. Keep the top hydraulic boundary drained.
4. Keep bottom/lateral hydraulic boundaries no-flux.
5. Output load, reaction, specimen stress, pore pressure, and boundary residuals.

## Why AccInput Is Not the Strict Route

`AccInput` is a body acceleration on selected particles.  It has no direct
surface area/reaction definition and changes with the selected layer mass and
thickness.  It is useful as a reduced smoke route, but L2 shows it can create
large dynamic excess pressure that overwhelms the Terzaghi reference.

## Source Needs

Likely source work for a strict route:

- a top-surface traction or force-controlled plate interface;
- clear marker selection for top load boundaries;
- CPU-first force/reaction diagnostics;
- optional GPU implementation only after CPU behavior is locked;
- no resurrection of the deprecated `TopLoad*` code without redesign.

Alternative source route:

- initialize an internally consistent 1D stress and pore-pressure state:
  total stress from `q0`, effective stress, and pore pressure;
- use that state for drainage/dissipation;
- this requires explicit stress initialization semantics and restart tests.

## Validation Order

1. Complete L3a diffusion gate and document storage/analytical limitations.
2. Add a CPU-only mechanical top-load route or stress/pore-pressure
   initialization route.
3. Run short CPU comparisons against L3a and Terzaghi.
4. Only after CPU behavior is stable, add GPU parity.

## Deferred

- damping/viscosity sweeps;
- Cryer boundary changes;
- triaxial/MCC routes;
- long production runs.
