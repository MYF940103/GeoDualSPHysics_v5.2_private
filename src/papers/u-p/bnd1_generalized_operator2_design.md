# BND1 Design: Generalized CPU Operator 2

Date: 2026-05-14

## Objective

Generalize `PorePressureBoundaryOperator=2` from a top/bottom hydraulic boundary-particle prototype to a CPU-only solid-wall no-flux route suitable for later slope/landslide diagnostics.

The change remains opt-in. The default operator is not changed.

## New Mode 2 Semantics

`PorePressureBoundaryOperator=2` now means:

- use boundary particles as hydraulic samples in the PR `LapPorePress` / `LapZ` quadrature;
- classify top/free drained boundary particles as excess-pressure Dirichlet, `excess_b=0`;
- classify every other ordinary solid boundary particle as no-flux;
- reconstruct ordinary wall excess pressure from nearby material particles;
- respect the hydrostatic/elevation convention used by `HydraulicElevationSource`.

## No-Flux Formula

For a boundary hydraulic sample at elevation `z_b`:

```text
excess_b = weighted mean of nearby material excess pressure
p_b = p_hydrostatic(z_b) + excess_b
```

When `HydraulicElevationSource=1`, the PR update combines `LapPorePress` and `LapZ`; this mirror is intended to preserve zero normal hydraulic-head gradient. When `HydraulicElevationSource=0`, `p_hydrostatic=0` and the mirror becomes an excess-pressure reconstruction.

## Boundary Classification

Priority order:

1. If top drained is active and a boundary particle is in the top drained elevation band, use drained Dirichlet.
2. Else if a boundary particle is in the bottom band, count it as bottom no-flux.
3. Else use ordinary solid-wall no-flux.

This avoids the old behavior where lateral/ordinary walls were scanned and then skipped.

## Diagnostics Added

Mode `2` logs:

- drained boundary contribution pairs;
- no-flux boundary contribution pairs;
- bottom no-flux pairs;
- ordinary solid no-flux pairs;
- total boundary contribution pairs;
- inactive boundary-neighbour count;
- unique drained and no-flux boundary targets;
- unique bottom and ordinary solid no-flux targets;
- `BoundNormal` usage;
- MLS sample and fallback counts;
- reconstructed excess pressure range.

## Compatibility

Unchanged:

- `PorePressureBoundaryOperator=0`;
- `PorePressureBoundaryOperator=1`;
- PR governing equation;
- pore-pressure feedback formulation;
- mechanical boundary formulation;
- soil constitutive model;
- MechanicalTopLoad;
- GPU behavior.

GPU `PorePressureBoundaryOperator=2` remains a hard error.

## Validation Gate

BND1 verification must pass before considering mode `2` a recommended CPU operator:

- feedback-off L3c-style initial-pressure gate stable;
- feedback-on L5-style coupling gate stable;
- no excluded particles;
- no `DtMin` burst;
- top drained and bottom/lateral no-flux metrics acceptable;
- analytical comparison no worse than mode `1`;
- diagnostics prove ordinary solid boundary particles participate.
