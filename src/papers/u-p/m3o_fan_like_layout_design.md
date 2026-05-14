# M3o Fan-Like Layout Design

## Goal

The M3n Cartesian refinement showed that reducing `Dp` alone does not clean the
MCC return failures.  M3o therefore designs a smoother external layout that
targets the geometric mechanism identified in M3k-M3m: poor support and high
local strain path burden near platen/cap/edge regions.

## Candidate Layouts

### Option 1: Radial Ring / Fan-Like Specimen

The specimen is generated from radial rings at each axial station.  Particles on
each ring are angularly distributed with staggered phase offsets between layers,
creating a smooth outer radius and an even angular shell.  Top and bottom
planes remain explicit.  A small cap-edge smoothing radius can slightly reduce
the sharp corner without changing the measurement core.

Advantages:

- directly targets lateral and edge support regularity;
- easy to generate reproducibly in Python;
- natural region labels for core, cap, edge, and lateral shell;
- closest of the low-cost options to the smooth/fan-like layouts recommended by
  the literature audit.

Limitations:

- requires a custom particle import route before it can be used by the solver;
- radial rings need volume-aware diagnostics because particles do not represent
  equal cell volumes if spacing is not carefully controlled;
- support may still be truncated at the free lateral boundary unless a boundary
  shell or import-aware workflow is added.

### Option 2: Hybrid Cartesian Core + Radial Boundary Shell

The central core remains Cartesian while the outer boundary shell is radial.
This could preserve a familiar core while smoothing the failure-prone lateral
and edge zones.

Advantages:

- lower disruption to current measurement regions;
- can focus resolution where failures occur.

Limitations:

- harder to make spacing continuous at the Cartesian/radial transition;
- likely needs more careful mass/volume weighting;
- not the smallest standalone prototype.

### Option 3: Smooth Edge / Rounded Cap Geometry

The specimen keeps a cylinder-like layout but replaces the sharp top/bottom edge
with a chamfer or rounded edge.

Advantages:

- directly addresses edge/corner ReturnStatus failures;
- easier to reason about physically than arbitrary return-map patches.

Limitations:

- M3m showed that XML-level trimming at `Dp=0.01 m` may not change the actual
  particle set;
- without a custom generator or finer discretization, this route can become a
  no-op.

### Option 4: Caveated Reporting Only

Stop pursuing clean MCC validation for now and package the current feedback-off
route with explicit caveats.

Advantages:

- honest and low risk;
- avoids turning geometry diagnostics into over-tuned validation.

Limitations:

- does not solve the boundary-induced failure mechanism.

## Recommended M3o Prototype

M3o implements Option 1 as a standalone external radial-ring generator:

- specimen: radial-ring / fan-like `mkfluid=0` point cloud;
- top platen: separate ring-based `mkbound=1` metadata;
- bottom platen: separate ring-based `mkbound=2` metadata;
- edge: small rounded/chamfered cap-edge radius;
- diagnostics first: particle count, support proxy, neighbor proxy, nearest
  spacing, edge/cap/core region metrics, measurement contamination, and preview
  figures.

The prototype intentionally does not run the solver unless a direct, low-risk
particle-cloud import route is confirmed.
