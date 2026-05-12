# C4-D Hydraulic Scaling / Elevation Source Audit

## Objective

Strict Cryer is a gravity-free poroelastic benchmark. The existing PR path used
`HydraulicGravity` for three different concepts:

1. hydraulic diffusivity scaling through `k/(rho_w g_h) * LapPorePress`;
2. elevation-source contribution through `k * LapZ`;
3. hydrostatic pore-pressure reference used by initialization, excess output,
   Shepard/feedback excess mode, and hydraulic boundary conventions.

Cryer still needs a positive `g_h` in the hydraulic-conductivity scaling because
the code stores hydraulic conductivity in `[m/s]`, but it must not include a
hydrostatic elevation source.

## Source Audit

| Use | Source location | Previous behavior | C4-D requirement |
|---|---|---|---|
| hydraulic gravity vector | `JSph::GetHydraulicGravity()` | custom vector or body-gravity fallback | unchanged |
| hydraulic scaling magnitude | `JSph::GetHydraulicGmag()` | positive `g_h` required when `HydraulicConductivity>0` | unchanged, still positive |
| hydraulic elevation | `JSph::GetHydraulicElevation()` | coordinate along `-HydraulicGravity/g_h` | unchanged for diagnostics/geometry |
| hydrostatic reference | initialization/output/feedback helpers | `rho_w g_h max(waterlevel-z_h,0)` | zero when no-elevation mode is active |
| PR rate | `JSphCpu::ComputeHydroPorePressRatePR()` | `Kw/n*(-DivVel+k/(rho g)LapP+k*LapZ)` | omit `k*LapZ` in no-elevation mode |
| curved drained boundary | `PorePressureBoundaryOperator=3` | Dirichlet ghost can use excess/hydrostatic split | with no-elevation, excess equals total pore pressure |

The CPU material-material `LapZ` diagnostic is still computed when the field is
allocated. In no-elevation mode this diagnostic is not multiplied into
`PorePressRate`; the retained `LapZ` output is therefore diagnostic-only.

## Implemented Switch

New XML parameter:

```xml
<parameter key="HydraulicElevationSource" value="0" />
```

Semantics:

- `1` default: legacy behavior, including hydrostatic reference and `k*LapZ`.
- `0`: gravity-free representation. `HydraulicGravity` still supplies positive
  `g_h` for `k/(rho_w g_h)`, but hydrostatic reference is zero and `k*LapZ` is
  omitted from `PorePressRate`.

GPU support is not implemented in C4-D. GPU execution with
`HydraulicElevationSource=0` hard-errors during XML loading.

## Cryer Convention

For strict Cryer drafts:

- mechanical gravity remains zero;
- `HydraulicGravity=(0,0,-9.81)` is retained only as a hydraulic scaling
  magnitude;
- `HydraulicElevationSource=0`;
- drained curved boundary uses `p_w=0` / `excess=0`, with excess equal to total
  pore pressure under the gravity-free convention.
