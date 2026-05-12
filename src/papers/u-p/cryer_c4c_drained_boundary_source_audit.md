# C4-C Drained Curved Boundary Source Audit

Date: 2026-05-12

## Objective

C4-C audits and extends the CPU pore-pressure boundary path for a future strict
Cryer sphere. The remaining blocker after the flexible confining stress work is
a drained curved exterior pore-pressure boundary that enters the PR hydraulic
operator, rather than a post-update material-pressure clamp.

This audit is limited to the CPU prototype. GPU support is intentionally
unsupported while the strict CPU behavior is still being tested.

## Existing Boundary Modes

| Mode | Mechanism | Source location | Curved exterior suitability |
|---:|---|---|---|
| 0 | Legacy top drained / bottom no-flux layer projection after pressure update. | Parser/logging in `JSph.cpp`; pressure update/corrections in CPU/GPU PR path. | Not suitable for a spherical drained exterior because it is layer/elevation based. |
| 1 | Simple virtual top/bottom ghost contribution in `LapPorePress` / `LapZ`, with legacy projection retained as safety. | `JSphCpu::ApplyPorePressureBoundaryOperatorT`, GPU counterpart from B4/B5. | Not suitable as-is; it assumes hydraulic top/bottom elevation layers. |
| 2 | CPU-only hydraulic mDBC-style boundary-particle reconstruction. Boundary particles contribute reconstructed hydraulic state to `LapPorePress` / `LapZ`. | `JSphCpu::ApplyPorePressureBoundaryOperatorT`, mode 2 branch. | Conceptually closer, but tied to existing boundary-particle normals and top/bottom classification; not a clean spherical drained surface. |
| 3 | New CPU-only curved drained Dirichlet ghost prototype. | `JSphCpu::ApplyPorePressureBoundaryOperatorT`, mode 3 branch. | Designed for a spherical exterior drained boundary smoke. |

## Current PR Operator Entry Point

The CPU PR diagnostic/update path computes material-material `DivVel`,
`LapPorePress`, and `LapZ`, then calls:

```cpp
ApplyPorePressureBoundaryOperator(..., PorePressc, LapPorePressc, LapZc, ...)
```

from `JSphCpuSingle.cpp` when `PorePressureBoundaryOperator` is `1`, `2`, or
`3`. The C4-C branch therefore modifies `LapPorePress` and `LapZ` before
`PorePressRate` is evaluated. This is an operator-level contribution, not a
post-update pressure clamp.

## Mode 3 Interface

C4-C adds the CPU-only `PorePressureBoundaryOperator=3` path. It requires:

```xml
<parameter key="PorePressureBoundaryOperator" value="3" />
<parameter key="PorePressureCurvedDrained" value="1" />
<parameter key="CurvedDrainedBoundaryCenterX" value="0" />
<parameter key="CurvedDrainedBoundaryCenterY" value="0" />
<parameter key="CurvedDrainedBoundaryCenterZ" value="0" />
<parameter key="CurvedDrainedBoundaryRadius" value="0.05" />
<parameter key="CurvedDrainedBoundaryTargetMk" value="0" />
<parameter key="CurvedDrainedBoundaryValue" value="0" />
<parameter key="CurvedDrainedBoundaryUseExcess" value="1" />
<parameter key="CurvedDrainedBoundaryThickness" value="0.018" />
<parameter key="CurvedDrainedBoundaryMode" value="0" />
```

Defaults keep mode `0`; old XML files are unchanged. GPU execution hard-errors
if mode `3` or `PorePressureCurvedDrained=1` is requested.

## Numerical Treatment

Mode `3` identifies target material particles in a spherical near-surface shell:

```text
r = |x_i - center|
r >= radius - thickness
```

For each selected material particle, a ghost point is placed outward along the
radial direction by a mirrored distance to the nominal surface. The ghost
hydraulic state is:

```text
if CurvedDrainedBoundaryUseExcess:
    p_ghost = p_hydro(z_ghost) + CurvedDrainedBoundaryValue
else:
    p_ghost = CurvedDrainedBoundaryValue
```

For strict Cryer without a hydrostatic elevation reference, this corresponds to
`p_w=0` when `CurvedDrainedBoundaryValue=0`. In the current PR implementation,
`HydraulicGravity` is still required for hydraulic scaling, so the C4-C smokes
use the existing hydrostatic/excess convention and explicitly document this
remaining Cryer blocker.

The ghost contributes to:

- `LapPorePress`
- `LapZ`

using the same kernel Laplacian form as the other CPU PR boundary-operator
branches. It does not overwrite `PorePress` and does not project material
particles to the boundary value.

## Diagnostics

The CPU log prints a one-time mode `3` diagnostic:

- active flag;
- center and radius;
- shell thickness;
- target marker;
- prescribed boundary value and whether it is excess or total pressure;
- number of affected material particles;
- skipped particle count;
- affected radius range;
- near-boundary residual proxy.

The C4-C smoke scripts additionally compute:

- center excess pressure;
- surface/interior excess pressure;
- `PorePressRate`, `LapPorePress`, `LapZ`, and `DivVel` max magnitudes;
- `Kplastic` max;
- velocity and radial surface velocity diagnostics for the compression smoke.

## Limitations

- Mode `3` is a first-order Dirichlet ghost prototype, not MLS or full boundary
  quadrature.
- It currently uses a spherical center/radius selector and is not a general
  arbitrary curved-surface boundary.
- It is CPU-only.
- It does not solve the separate Cryer no-elevation-source issue: current PR
  diffusion scaling still requires positive `HydraulicGravity`.
- The C4-C tests are short smokes, not strict Cryer analytical reproduction.
