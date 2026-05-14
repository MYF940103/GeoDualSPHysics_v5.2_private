# M3n Smooth Layout Feasibility Audit

## Question

Can a smooth/fan-like triaxial specimen layout be produced through the current
XML/GenCase workflow, or is an external particle generator required?

## Existing XML / GenCase Capability

Repository examples show extensive use of standard GenCase geometry commands
such as:

- `drawcylinder`;
- `drawbox`;
- `drawpoint`;
- `drawfilestl`;
- `drawfilevtk`.

These are shape-rasterization tools on the GenCase point lattice.  The current
triaxial XML uses `drawcylinder`, which yields the Cartesian/cut-cell cylinder.

I did not find an existing triaxial example or GenCase XML pattern that
directly generates a polar, radial, or fan-shaped specimen point cloud while
preserving the current mkfluid/mkbound grouping and motion workflow.

## Can Existing Geometry Combinations Improve Smoothness?

XML shape combinations can improve some boundary roles:

- platen overhang is feasible and effective;
- shape trimming or stepped caps can be expressed in XML;
- higher resolution changes the realized particle set.

However, M3m showed that trimming/stepping at `Dp=0.01 m` does not necessarily
change the actual particles.  XML-only shape combinations are therefore
limited by lattice resolution.

## External Generator Feasibility

A Python radial/fan-like particle generator is feasible as an isolated tool,
but it is not yet a drop-in solver workflow in this branch.  It would need a
confirmed path to feed custom particles back into the standard
GenCase/DualSPHysics pipeline while preserving:

- material and platen mk grouping;
- moving top platen and fixed bottom platen;
- output fields needed by u-pw/MCC diagnostics;
- lateral FlexibleConfiningStress geometric selectors;
- restart/output compatibility if used later.

This is a stronger route for strict validation, but it is too large for the
minimal M3n task without first proving the input workflow.

## Higher-Resolution Smooth Cylinder Feasibility

The smallest executable option is a higher-resolution smooth cylinder
diagnostic:

- reduce `Dp` from `0.01 m` to `0.0075 m`;
- keep the physical radius, height, platen overhang, MCC parameters, feedback
  state, and loading unchanged;
- use the same GenCase/DualSPHysics workflow;
- compare geometry/support metrics and return statuses against the M3m
  overhang045 reference.

This does not create a true fan-like layout, but it does answer whether the
coarse Cartesian rasterization alone is the immediate bottleneck.

## Cost and Risk

The `Dp=0.0075` diagnostic roughly increases specimen particles from `407` to
`1035`.  This is still cheap for a very-short dense-output CPU run.

Risks:

- it is still a Cartesian/cut-cell surface;
- improved support does not guarantee a cleaner local stress path;
- smaller `Dp` changes time step and local contact dynamics, so results are
  not a pure geometry-only perturbation.

## M3n Decision

M3n implements the higher-resolution overhang045 candidate first.  A true
fan-like generator remains the recommended next engineering route only if a
clean MCC validation route remains a priority after this diagnostic.
