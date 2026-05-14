# M3n Smooth Layout Diagnostic

This directory contains the M3n smooth-layout feasibility diagnostic.

It compares:

- `CaseM3n_Overhang045Reference`: `Dp=0.01 m` overhang045 reference.
- `CaseM3n_Dp0075Overhang045`: `Dp=0.0075 m` higher-resolution cut-cell candidate.

This is not a clean MCC validation case. It is CPU-only, feedback-off, and uses
pairwise interaction reaction diagnostics rather than actuator reaction.
