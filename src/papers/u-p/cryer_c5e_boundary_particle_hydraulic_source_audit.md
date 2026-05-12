# C5e Boundary-Particle Hydraulic Source Audit

Date: 2026-05-12

## Objective

C5e audits and implements the next Cryer drained-boundary route after LIT-B:
selected dummy/boundary particles carry a prescribed hydraulic Dirichlet state
and participate in the PR hydraulic operator. This is intended to move away
from the material-side spherical ghost/quadrature tuning used in C4-C through
C5d.

The scope is deliberately narrow: CPU-only `PorePressureBoundaryOperator=3`
with `PorePressureCurvedDrained=1`. Existing modes `0`, `1`, and `2` are not
changed.

## Boundary-Particle Identification

In the current particle arrays, fixed/dummy boundary particles occupy the
indices before `pini`. Material particles occupy `pini ... pini+n-1`.

The C5e mode selects boundary particles using:

- `CODE_IsNormal(code[pb]) && !CODE_IsFluid(code[pb])`;
- optional `CurvedDrainedBoundaryTargetMkBound`;
- spherical geometry selection around `CurvedDrainedBoundaryCenter` and
  `CurvedDrainedBoundaryRadius`;
- `CurvedDrainedBoundarySelectionTolerance`.

This avoids using all fixed particles blindly. In the retained C5e tests, the
dummy shell uses `mkbound=0`, and mode 4 selected `2418` boundary particles.

## Available Boundary-Particle Quantities

The operator has access to:

- boundary particle position `pos[pb]`;
- density in `velrhop[pb].w`;
- common boundary mass `MassBound`;
- marker/type from `CODE_GetTypeValue(code[pb])`.

For hydraulic quadrature, C5e estimates the boundary-particle effective volume
as:

```text
V_b = MassBound / rho_b
```

The selected boundary particle provides the angular quadrature site. The
hydraulic Dirichlet state is evaluated at the prescribed drained spherical
surface, so a mechanically separated dummy shell can still represent a
hydraulic boundary at radius `R`.

## Existing PR Operator Filtering

The production PR loops remain material-oriented. Prior modes filter neighbor
participation through material/fluid checks and do not generally include
boundary particles as hydraulic degrees of freedom. Earlier mode 3 submodes
therefore added virtual material-side samples rather than using actual boundary
particles.

Mode 4 changes only the curved-drained CPU branch: selected boundary particles
are added to the `LapPorePress` and `LapZ` contributions for near-surface
material particles before `PorePressRate` is formed.

## Mode 4 Hydraulic State

For strict Cryer with `HydraulicElevationSource=0`, the drained state is:

```text
p_b = 0
excess_b = 0
```

The implementation keeps the general excess/total-pressure convention:

- if `CurvedDrainedBoundaryUseExcess=1`, `p_b = p_hydro + value`;
- if `CurvedDrainedBoundaryUseExcess=0`, `p_b = value`.

In Cryer no-elevation mode, `p_hydro=0`, so prescribed total and prescribed
excess are identical for `value=0`.

## Operator Participation

For each near-surface material particle and selected boundary particle within
kernel support, mode 4 adds:

```text
LapP += 2 V_b (p_i - p_b) (r_ij . grad W_ij) / (|r_ij|^2 + eps)
LapZ += 2 V_b (z_i - z_b) (r_ij . grad W_ij) / (|r_ij|^2 + eps)
```

The material pore pressure is not clamped. The contribution enters before
`PorePressRate`. With `HydraulicElevationSource=0`, `LapZ` is still available
as a diagnostic but is not used in the PR rate.

## Adami / MLS Diagnostic

`CurvedDrainedBoundaryAdamiDiagnostic=1` computes a normalized-kernel
extrapolated boundary excess from material neighbors:

```text
excess_b^Adami = sum_i V_i W_bi excess_i / sum_i V_i W_bi
```

This value is diagnostic only. It is not used as the drained boundary value,
because the Cryer drained condition is prescribed `p_w=0`; using extrapolated
interior pressure as the boundary value would weaken the Dirichlet drainage.

## Separation from Mechanical Boundary Handling

Mode 4 does not alter mDBC/cDBC mechanics, boundary normals, particle motion,
or fixed-particle treatment. It only gives selected boundary particles an
on-the-fly hydraulic state for the curved-drained PR operator.

## GPU Status

The curved drained boundary remains CPU-only. GPU execution with
`PorePressureBoundaryOperator=3` or `PorePressureCurvedDrained=1` is unsupported
and should hard-error rather than silently falling back.

## Main Implementation Risk

The current effective boundary volume and projected-surface participation make
the drained influence much stronger than old mode 3. This is useful for testing
the boundary-particle route, but the C5e pressure-only diffusion result shows
over-drainage and pressure-rate artifacts. A later MLS/Adami-normalized
boundary-volume treatment is still needed before strict quantitative Cryer
comparison.
