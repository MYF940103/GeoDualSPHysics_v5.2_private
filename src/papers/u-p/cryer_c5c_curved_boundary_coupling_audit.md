# Cryer C5c Curved Boundary Coupling Audit

Date: 2026-05-12

## Purpose

C5b showed that the coarse strict-sphere Cryer smoke is stable over short
windows, but the material near-surface excess pressure remains large even
though the curved drained ghost diagnostic reports zero residual. This audit
checks whether the current `PorePressureBoundaryOperator=3` material-surface
coupling is too weak for strict Cryer-style drainage.

## Current Mode 3 Path

The CPU curved drained boundary is implemented in
`JSphCpu::ApplyPorePressureBoundaryOperatorT()` for
`PorePressureBoundaryOperator=3` and `PorePressureCurvedDrained=1`.

For each target material particle in the spherical shell

```text
R - CurvedDrainedBoundaryThickness <= r <= R
```

the code:

1. computes the outward radial normal from
   `CurvedDrainedBoundaryCenter` to the material particle;
2. constructs a ghost point outside the spherical surface;
3. assigns the ghost hydraulic value from the prescribed drained value
   (`excess=0` for the Cryer tests);
4. adds the pair contribution to `LapPorePress` and `LapZ` before
   `PorePressRate` is computed.

This is an operator contribution, not a post-update clamp.

## Why Ghost Residual Can Be Zero While Material Residual Is High

The previous diagnostic `boundary_residual_max` was printed from the boundary
operator when it first logged. In the C5/C5b cases, that first diagnostic occurs
when the pore-pressure field is still zero, so the reported residual is the
prescribed ghost-state residual, not the full material surface excess through
time.

Therefore:

- `ghost residual = 0` means the prescribed boundary ghost value is correctly
  constructed;
- it does not prove that the material particles in the outer shell remain close
  to the drained boundary value during the coupled run.

The C5b retained frame summaries show large near-surface material excess
(`~263 Pa` for `p0=50 Pa`), so the material-side coupling is the part that must
be checked.

## Candidate Refinements

### Mode 0: Existing first-order ghost

This is retained unchanged:

```text
ghost value = prescribed drained value
ghost location = exterior mirror point
```

It remains the baseline mode.

### Mode 1: Strengthened image Dirichlet ghost

C5c adds a limited refinement:

```text
ghost excess = 2 * prescribed_excess - material_excess
```

for excess-pressure mode. This mirrors the material-side value around the
Dirichlet boundary value and strengthens the operator-level boundary influence
without changing the PR governing equation or directly overwriting material
pressure.

For the gravity-free Cryer convention, this reduces to:

```text
ghost pressure = - material pressure
```

when the drained value is zero.

### Mode 2: Diagnostic material surface clamp

C5c also adds a diagnostic-only upper-bound test:

```text
material surface excess = prescribed drained excess
```

after the pore-pressure update for target particles in the curved shell.

This is not a production method. It intentionally overwrites the material
surface pressure so we can test whether perfect material-side drainage would
substantially reduce the center-pressure peak. If it does, the drained boundary
coupling is confirmed as a controlling issue; if it does not, geometry or
dynamic response is more likely.

## Scope of Source Changes

The refinement is intentionally local:

- `CurvedDrainedBoundaryMode=0` keeps the old behavior;
- `CurvedDrainedBoundaryMode=1` changes only the mode-3 ghost value;
- `CurvedDrainedBoundaryMode=2` adds a diagnostic CPU post-update clamp;
- modes `0`, `1`, and `2` of `PorePressureBoundaryOperator` are untouched;
- `FlexibleConfiningStress`, `SoilConstitutiveModel`, and
  `HydraulicElevationSource` are untouched;
- GPU remains unsupported for mode `3`.

## Expected C5c Signals

C5c should be interpreted as follows:

- if mode 1 lowers near-surface residual and center peak, the ghost coupling was
  too weak but can be improved without direct clamping;
- if mode 2 strongly lowers the peak while mode 1 does not, material-surface
  drainage is likely the controlling issue but needs a better operator or
  quadrature treatment;
- if neither mode changes the response, geometry/free-sphere dynamics are more
  likely than the drained boundary coupling.
