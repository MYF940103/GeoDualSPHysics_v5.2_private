# M3o Smooth / Fan-Like Layout Prototype Report

## Objective

M3o tests whether the next plausible route for clean MCC return robustness is a
true smooth/fan-like specimen layout rather than another Cartesian refinement or
another MCC return-mapping patch.  This stage does not change source and does
not run a solver case.

## Implemented Prototype

The prototype is retained under:

```text
examples/u-pw/04_Undrained_Triaxial/experiments/M3o_SmoothFanLayoutPrototype/
```

It adds `generate_smooth_triaxial_layout.py`, which generates:

- radial-ring / fan-like specimen particles with `mk=0` metadata;
- ring-based top platen particles with `mk=1` metadata;
- ring-based bottom platen particles with `mk=2` metadata;
- a lightly rounded specimen cap edge;
- core, interior, lateral, cap, and edge/corner region labels;
- CSV diagnostics and SVG/PNG preview figures.

The script passed `py_compile` and generated the CSV/figure package.

## Geometry Metrics

The M3o radial-ring prototype produced:

| Metric | Value |
|---|---:|
| Specimen particles | 555 |
| Top platen particles | 369 |
| Bottom platen particles | 369 |
| Measurement core particles | 45 |
| Edge/corner particles | 94 |
| Edge support / core support, unweighted | 0.749 |
| Edge support / core support, volume-weighted | 0.559 |
| Cap support / core support, unweighted | 1.091 |
| Cap support / core support, volume-weighted | 0.963 |
| Edge specimen-neighbor mean | 113.64 |
| Nearest-neighbor distance coefficient of variation | 0.102 |
| Outer-ring angular gap coefficient of variation | ~0 |
| Platen contamination in measurement core | 0 |

Compared with M3m `overhang045`, the radial-ring prototype improves the
edge-neighbor proxy (`96.25 -> 113.64`) and angular regularity.  Compared with
the M3n `Dp=0.0075 m` Cartesian candidate, it is smoother and less over-dense,
but it does not improve the scalar edge support/core ratio.  Cap support is
good; the lateral edge remains the weak region.

## Solver Integration Decision

No solver run was performed.  The current examples show GenCase shape/mesh
generation and `drawfilestl` / `drawfilevtk` geometry import, but no confirmed
low-risk route for importing an arbitrary particle cloud with per-particle
`mkfluid` / `mkbound` assignments.  Running the solver from this CSV would
therefore require a separate custom-particle input pipeline or a conversion
strategy, which is outside M3o.

Because no solver run was performed:

- ReturnStatus `-3` / `-1` changes are not measured;
- no clean MCC candidate is claimed;
- p'-q, reaction, and pore-pressure curves are not regenerated.

## Interpretation

The generator proves that an external fan-like layout can be produced and
diagnosed reproducibly.  It also shows that fan-like angular regularity alone is
not automatically enough: the lateral edge support ratio remains below the best
Cartesian overhang diagnostics.  This supports the M3m conclusion that geometry
quality must be judged by local support and strain-path diagnostics, not by
particle count alone.

## Next Step

Recommended next step: M3p custom particle input / smooth-layout solver
integration planning.

M3p should decide whether to:

1. add or discover a safe particle-cloud import route;
2. convert the radial-ring layout into an accepted GenCase mesh/geometry input;
3. add a hybrid radial boundary shell with better lateral support before solver
   integration;
4. or stop clean validation and publish the MCC route as a caveated feedback-off
   reduced package.

Until a generated smooth layout can be run through the CPU solver, the current
MCC route remains caveated and not clean validation.  Full pore-pressure
feedback and GPU remain deferred.
