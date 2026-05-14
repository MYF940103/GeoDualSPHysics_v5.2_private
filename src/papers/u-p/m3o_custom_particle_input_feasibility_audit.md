# M3o Custom Particle Input Feasibility Audit

## Objective

M3o checks whether a smooth or fan-like triaxial specimen layout can be inserted
into the current GeoDualSPHysics workflow without changing solver source.  The
specific goal is an externally generated specimen/platen point cloud with clear
`mkfluid` / `mkbound` assignment, suitable for later MCC return-robustness
diagnostics.

## Current Workflow Findings

The existing examples expose several geometry import and generation paths:

- GenCase XML shape commands such as `drawbox`, `drawcylinder`, and `drawpoint`;
- mesh-based geometry import through `drawfilestl` and `drawfilevtk`;
- `setmkfluid` and `setmkbound` blocks for assigning generated geometry groups;
- generated output XML sections with particle records, for example `<particles
  np=...>`, after GenCase has already created particles.

The audit did not find a current triaxial or standard example that uses an
arbitrary CSV/point-cloud file as initial particles with direct per-particle
`mkfluid` / `mkbound` assignment.  The mesh import commands are geometry
descriptions that GenCase discretizes; they are not a direct particle-position
import path.  The `<particles>` records seen in generated XML are output state,
not a documented input mechanism for arbitrary particle clouds in the examples
checked here.

## Required Assignments

A fan-like triaxial import route would need to preserve:

- specimen material particles as `mkfluid=0`;
- top platen particles as a moving `mkbound`, currently `mkbound=1`;
- bottom platen particles as a fixed `mkbound`, currently `mkbound=2`;
- clean exclusion of both platens from measurement regions;
- optional labels for core, cap, edge, and lateral shell regions.

The standalone M3o generator writes these labels to CSV metadata, but the current
workflow does not yet consume that metadata as a solver input.

## Workflow Compatibility

The established workflow remains:

```text
GenCase -> DualSPHysics CPU -> PartVTK / PartCsv / postprocessing
```

For XML-native shapes, this remains intact.  For an external fan-like particle
cloud, a missing link remains between generated coordinates and GenCase-created
particle state.  Without that link, running the solver would require either a
new import route or a carefully audited conversion into existing geometry
commands.  M3o therefore stops at geometry/support diagnostics.

## Minimum-Risk Route

The lowest-risk route is:

1. keep the fan-like generator isolated from production source;
2. use it to evaluate support, neighbor, edge, cap, and measurement metrics;
3. only after a clearly better layout exists, design M3p custom particle import
   or mesh conversion support;
4. avoid claiming solver-level MCC improvement until the generated layout can be
   run through the standard CPU path.

## Feasibility Decision

Custom/fan-like layout generation is feasible as a standalone diagnostic.
Direct solver integration is not yet confirmed from the current XML/GenCase
workflow.  M3o therefore does not run a solver case and does not report
ReturnStatus changes.
