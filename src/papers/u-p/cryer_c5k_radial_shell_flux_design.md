# C5k Radial-Shell Flux Boundary Design

## Scope

C5k adds one narrow CPU-only experimental route for the existing
`PorePressureBoundaryOperator=3` curved drained spherical boundary. The goal is
to test a radial-shell / finite-volume consistency idea on the pressure-only
spherical diffusion gate before any Cryer compression run.

The implementation must not change the PR governing equation,
`FlexibleConfiningStress`, `SoilConstitutiveModel`, `HydraulicElevationSource`,
or existing mode `0` to mode `5` behavior. It must not clamp material pore
pressure and it must not make the new route the default.

## Why Mode 5 Failed

C5j mode `5` replaced raw boundary-particle volume counting with a constrained
radial MLS normal-gradient estimate. That removed one source of nonuniform pair
over-counting, but it still failed the pressure-only gate:

- the FV reference at `t ~= 0.00603 s` has center pressure `999.998 Pa`,
  volume mean `615.7 Pa`, and surface-shell mean `85.9 Pa`;
- mode `5`, `dp=0.008`, ended with center `446.1 Pa`, volume mean `356.6 Pa`,
  and surface shell `311.1 Pa`;
- mode `5`, `dp=0.010`, ended with center `579.2 Pa`, volume mean `550.6 Pa`,
  and surface shell `557.8 Pa`;
- final flux ratios were still about `4`.

The failure is not simply that the local normal gradient is noisy. A local
gradient correction can still drain the wrong radial storage, leave the
near-surface shell too pressurized, and force the center to decay too early.
The pressure-only gate requires a boundary rule that is tested against the
integrated radial diffusion balance, not only against local support quality.

## FV Conservation Target

The pressure-only reference problem is

```text
u_t = D * (1/r^2) d/dr (r^2 du/dr)
du/dr = 0 at r = 0
u = 0 at r = R
```

For the full sphere, the storage balance is

```text
d/dt int_V u dV = -4*pi*R^2*q_R
```

where `q_R` is the outward drained pressure flux. In the C5k prototype the
outer shell mean pressure `u_s` and mean radius `r_s` define the positive
outward loss magnitude:

```text
q_R = D * (u_s - u_b) / (R - r_s)
u_b = 0 Pa
```

This is a geometry-derived flux estimate. It is not a scalar fit to the C5i FV
reference.

## Mode 6 Interface

`CurvedDrainedBoundaryMode=6` is added as:

```text
0 = first-order spherical Dirichlet ghost
1 = strengthened image ghost
2 = diagnostic material surface clamp, not production
3 = material-side multi-sample spherical Dirichlet quadrature
4 = boundary-particle prescribed Dirichlet hydraulic state
5 = radial MLS / integrated flux correction
6 = radial-shell / FV-consistent spherical drained boundary flux
```

Mode `6` is CPU-only experimental. GPU execution remains guarded by the
existing hard error for `PorePressureBoundaryOperator=3` /
`PorePressureCurvedDrained=1`.

## Numerical Form

Mode `6` uses `CurvedDrainedBoundaryThickness` as the shell width. Four inward
spherical shells are accumulated for diagnostics. The first shell next to the
physical surface supplies the active boundary flux estimate:

```text
shell 0: R - h_s <= r <= R
shell 1: R - 2*h_s <= r < R - h_s
shell 2: R - 3*h_s <= r < R - 2*h_s
shell 3: R - 4*h_s <= r < R - 3*h_s
```

Each shell stores material-particle volume, volume-weighted pressure, and
volume-weighted radius. For `HydraulicElevationSource=0`, pressure equals
excess pressure and no `LapZ` source is added to `PorePressRate`.

The integrated boundary flux is converted to an explicit `LapPorePress`
correction over the same outer material shell:

```text
Q_R = 4*pi*R^2*q_R
LapPorePress += -Q_R / (D * V_shell0)
```

This gives the outer shell a storage-rate correction of `-Q_R` while leaving
interior material-material `LapPorePress` unchanged. Material `PorePress` is
not overwritten.

## Avoiding Arbitrary Fitting

Mode `6` intentionally has no calibrated multiplier. Its only geometric inputs
are the prescribed sphere center/radius, shell width, material volumes, and the
same effective diffusivity used by the PR pressure equation:

```text
D = (Kw/n) * k/(rho_w*g_h)
```

If a limiter becomes necessary later, it should be reported as a stability
limiter and tested independently, not hidden as a reference-matching
coefficient.

## Diagnostics

Mode `6` prints per-step diagnostics when `CurvedDrainedFluxDiagnostics=1`:

- shell bin populations;
- shell pressure means;
- shell radius means;
- outer shell volume;
- estimated `du/dr` at the boundary;
- boundary flux density;
- integrated boundary flux;
- storage-rate correction;
- flux/storage residual;
- maximum absolute `LapPorePress` correction;
- fallback flag if the shell population or volume is insufficient.

The C5k analysis script additionally compares center pressure, volume mean,
surface-shell pressure, apparent storage flux, flux ratio, pressure-rate
artifacts, and radial profiles against the C5i FV reference and the retained
mode `4` / mode `5` gates.

## Acceptance Before Compression

Mode `6` can justify a Cryer compression smoke only if the pressure-only
diffusion gate clearly improves:

- center pressure closer to FV than modes `4` and `5`;
- volume mean closer to FV;
- surface-shell pressure closer to FV;
- apparent flux ratio closer to `1`;
- no final flux reversal;
- no negative over-drain;
- `PorePressRate` maxAbs lower or at least not worse than mode `5`;
- `code=0`, `excluded=0`, and `Kplastic=0`.

If those criteria are not met, C5k stops at the pressure-only report and C6
remains blocked.
