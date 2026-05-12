# C5f Boundary-Particle Weighting Report

Date: 2026-05-12

## Objective

C5f refines `CurvedDrainedBoundaryMode=4`, the CPU-only boundary-particle
drained Cryer boundary. The goal is to reduce the raw boundary-particle
over-drainage seen in C5e without changing the PR governing equation, without
clamping material pressure, and without touching the mechanical loading,
constitutive model, or no-elevation hydraulic mode.

## Implementation

The new XML switch is:

```xml
<CurvedDrainedBoundaryWeighting value="0" />
```

Values:

- `0`: raw boundary-particle volume weighting, preserving C5e behavior;
- `1`: Adami-style local partition normalization;
- `3`: diagnostic missing-support capped weighting, not production.

The switch is only used by `CurvedDrainedBoundaryMode=4`. Existing
`PorePressureBoundaryOperator` modes `0`, `1`, and `2` are unchanged, and
mode-4 default behavior remains raw weighting unless explicitly overridden.

The normalized weighting computes the local material and boundary kernel
partitions around each material target:

```text
S_m = sum_j V_j W_ij
S_b = sum_b V_b W_ib
```

and applies the boundary effective-volume scale:

```text
scale = min(1, 1 / (S_m + S_b))
```

The drained value remains prescribed `p_b=0`. No material pressure is clamped.
The contribution still enters `LapPorePress` and `LapZ` before `PorePressRate`.

## Test Matrix

All tests are CPU Release smokes under:

`examples/u-pw/03_Cryer_Problem/strict_reproduction_plan/C5f_BoundaryParticleWeighting/`

Cases:

| Case | Purpose | Weighting |
|---|---|---:|
| DiffusionRaw | pressure-only control | 0 |
| DiffusionNormalized | pressure-only normalized | 1 |
| DiffusionCapped | pressure-only diagnostic cap | 3 |
| CompressionRaw | C5e-style compression control | 0 |
| CompressionNormalized | normalized compression | 1 |
| CompressionCapped | diagnostic capped compression | 3 |

All six runs completed with `code=0`, `excluded=0`, and `Kplastic=0`.

## Weighting Diagnostics

The normalized/capped runs used the same boundary selection:

- selected boundary particles: `2418`;
- material-boundary hydraulic pairs: `194490`;
- average pairs per material target: `328.53`.

The local partition diagnostics are:

| Weighting | Mean `S_m` | Mean `S_b` | Mean boundary fraction | Mean scale |
|---|---:|---:|---:|---:|
| normalized | 0.760021 | 2.70005 | 0.770829 | 0.297224 |
| capped | 0.760021 | 2.70005 | 0.770829 | 0.0832761 |

This confirms that raw mode 4 over-drains because the boundary shell is counted
with a much larger kernel partition than the local material support.

## Pressure-Only Diffusion

| Case | Final center pressure | Final PorePressRate maxAbs | Interpretation |
|---|---:|---:|---|
| raw | `-97.17 Pa` | `9.38e5 Pa/s` | over-drains through zero |
| normalized | `529.96 Pa` | `3.33e5 Pa/s` | no negative over-drainage, artifact reduced |
| capped | `896.22 Pa` | `1.58e5 Pa/s` | too weak, close to under-drained behavior |

The normalized weighting removes the strong negative over-drainage seen in raw
mode 4 and reduces the pressure-rate artifact substantially. It does not yet
give an ideal spherical diffusion boundary.

## Compression Smoke

For the `p0=50 Pa` compression smoke:

| Case | Peak center `p_w/p0` | Final center `p_w/p0` | Final surface p95 `|p_w|`, `r>0.85R` |
|---|---:|---:|---:|
| raw | `6.908` | `-0.119` | `195.08 Pa` |
| normalized | `7.448` | `1.607` | `131.56 Pa` |
| capped | `7.605` | `2.386` | `178.89 Pa` |

Normalized weighting improves the material-surface residual substantially
relative to raw mode 4 and C5d mode 3, but the center peak is higher than raw
mode 4 and only modestly below the mode-3 peak of about `7.66 p0`. Raw mode 4
therefore lowers the peak partly by over-draining, while normalized weighting
is more stable but still not quantitatively Cryer-ready.

## Figures

Generated figures include:

- `c5f_pressure_only_mean_excess`;
- `c5f_center_normalized_pressure`;
- `c5f_surface_excess_p95_abs`;
- `c5f_surface_excess_max_abs`;
- `c5f_porepressrate_artifact_indicator`;
- `c5f_boundary_contribution_magnitude`;
- `c5f_normalized_boundary_scale_summary`;
- `c5f_radial_pressure_profiles`;
- `c5f_velocity_max`;
- `c5f_kplastic_max`.

Each figure is saved as SVG and PNG.

## Conclusions

Raw mode 4 over-drains because its boundary-particle kernel partition is too
large relative to the material partition. The Adami-style normalized weighting
reduces pressure-rate artifacts and prevents pressure-only diffusion from
crossing strongly negative. It also improves the compression surface residual.

However, the normalized compression center peak remains about `7.45 p0`, and
the pressure-only case still does not match an ideal drained spherical
diffusion behavior. C5f is therefore an improvement in boundary stability and
diagnostics, not a green light for Figure 7B quantitative comparison.

## Next Step

C6 remains paused. The next useful source-side step should be a true MLS /
partition-of-unity boundary-particle operator refinement, or a narrow boundary
flux calibration on pressure-only spherical diffusion. Geometry/dp refinement
should remain deferred until the boundary rule is less sensitive. GPU support
also remains deferred.
