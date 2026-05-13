# C5j MLS Boundary Source Audit

## Scope

C5j adds a narrow CPU-only experimental submode for the existing
`PorePressureBoundaryOperator=3` curved drained route. The goal is only the
pressure-only spherical radial diffusion gate. It does not change the PR
governing equation, the flexible confining stress implementation, the
constitutive model, the hydraulic elevation convention, or any mode `0` to
mode `4` behavior.

## Why Mode 4 Was Not Enough

C5i showed that `CurvedDrainedBoundaryMode=4` with
`CurvedDrainedBoundaryWeighting=1` behaves like an over-strong, nonuniform
Robin-like boundary rather than a true spherical Dirichlet boundary. The
problem is not just a scalar boundary strength:

- the apparent volume-storage flux is usually stronger than the FV radial
  reference;
- the near-surface material shell remains much too pressurized;
- the specimen center drains much earlier than the radial Dirichlet reference;
- the selected boundary-particle cloud grows nonmonotonically with refinement;
- the `dp=0.0065` case has a late flux reversal and a large pressure-rate
  spike.

The mode-4 pair rule still depends on many material-boundary pair
contributions. Even with local partition normalization, it does not enforce a
radial linear pressure reconstruction or an integrated spherical flux balance.

## New Mode 5 Interface

`CurvedDrainedBoundaryMode=5` is added as:

```text
0 = first-order spherical Dirichlet ghost
1 = strengthened image ghost
2 = diagnostic material surface clamp, not production
3 = material-side multi-sample spherical Dirichlet quadrature
4 = boundary-particle prescribed Dirichlet hydraulic state
5 = radial MLS / flux-consistent spherical drained boundary, CPU-only experimental
```

New parameters:

| parameter | default | meaning |
|---|---:|---|
| `CurvedDrainedMLSOrder` | `1` | `1`: constrained radial linear MLS; `0`: fallback route. |
| `CurvedDrainedMLSRadiusFactor` | `1` | MLS support radius multiplier on `KernelH`; `0` also uses `KernelH`. |
| `CurvedDrainedFluxDiagnostics` | `0` | Print per-step integrated flux diagnostics for mode `5`. |
| `CurvedDrainedMLSConditionLimit` | `1e8` | Maximum accepted local moment condition number. |
| `CurvedDrainedMLSFallbackMode` | `3` | Fallback route: mode-3-like ghost or local-gap mode-4-like estimate. |

The default behavior is unchanged because mode `5` is never selected by
default. The existing CPU-only guard for `PorePressureBoundaryOperator=3` and
`PorePressureCurvedDrained=1` still makes GPU execution a hard error.

## Numerical Form

Mode `5` uses a Route-C style boundary flux correction. For a near-surface
material particle `i`, it projects to the physical drained sphere:

```text
n_i = (x_i - c) / |x_i - c|
x_b = c + R n_i
u_b = 0
```

The local coordinate is the inward radial distance:

```text
s_j = max(0, R - |x_j - c|)
```

Nearby material particles inside the MLS support are used to fit the
Dirichlet-constrained radial linear profile:

```text
u_j - u_b ~= g_i s_j
```

with compact local weights based on the distance from the projected boundary
point `x_b`. The fitted gradient is:

```text
g_i = sum(w_j s_j (u_j - u_b)) / sum(w_j s_j^2)
```

A two-by-two moment condition estimate is recorded. If support is insufficient
or ill-conditioned, mode `5` falls back to the configured fallback route and
reports the fallback count.

The first implementation distributed the local correction directly. The final
C5j prototype uses the same local MLS fits to compute an integrated shell
flux, then applies a shell-average LapPorePress correction:

```text
LapPorePress += -g_bar * A_sphere / V_shell
```

where `g_bar` is the shell-area-weighted average of the local MLS gradients.
This keeps the integrated flux diagnostic consistent while reducing local
over-correction. It is still a prototype, not a production boundary.

## Boundary Constraint

The drained boundary value remains prescribed:

```text
p_b = 0 Pa
```

For `HydraulicElevationSource=0`, this is an excess-pressure Dirichlet value
and `LapZ` is not used by the pressure-rate equation. Mode `5` does not
overwrite material `PorePress`; it only contributes before `PorePressRate` is
computed.

## Avoiding Raw Boundary Over-Counting

Mode `5` does not volume-count selected dummy boundary particles. Boundary
particles are not used as quadrature volumes. They are replaced by the
physical spherical surface projection and by a local material-side MLS support.
This avoids the mode-4 pair explosion mechanism, but the C5j gate shows that
this alone is still not sufficient for FV-quality radial diffusion.

## Diagnostics Added

With `CurvedDrainedFluxDiagnostics=1`, the CPU log now records:

- number of mode-5 target particles;
- total and average MLS material samples;
- fallback count and fallback mode;
- support radius and condition-number statistics;
- sphere area and shell volume;
- mean and maximum normal-gradient estimates;
- maximum applied LapPorePress correction;
- integrated boundary flux and storage-rate correction.

The C5j postprocessor parses these logs and combines them with PartCsv fields
to write pressure-only gate CSVs and figures.

## Source Touch Points

- `source/JSph.h`: parameters and mode-5 declarations.
- `source/JSph.cpp`: defaults, XML parsing, validation, CPU-only logging.
- `source/JSphCpuSingle.cpp`: enables per-step mode-5 diagnostics when
  requested.
- `source/JSphCpu.cpp`: implements the constrained radial MLS flux correction
  in `ApplyPorePressureBoundaryOperatorT`.

No GPU kernels were modified.
