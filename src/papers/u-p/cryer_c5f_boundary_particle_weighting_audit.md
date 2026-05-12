# C5f Boundary-Particle Weighting Audit

Date: 2026-05-12

## Objective

C5e showed that `CurvedDrainedBoundaryMode=4` is physically pointed in the
right direction: selected spherical boundary particles carry a prescribed
drained hydraulic state (`p_w=0`) and enter the PR `LapPorePress` / `LapZ`
operator. However, the raw boundary-particle volume contribution over-drained
the pressure-only diffusion smoke and produced large pressure-rate artifacts.

This audit records the source mechanism and the numerical reason for the
over-drainage before introducing normalized weighting.

## Current Mode 4 Path

Mode 4 is active only when:

```text
PorePressureBoundaryOperator=3
PorePressureCurvedDrained=1
CurvedDrainedBoundaryMode=4
```

The CPU path:

1. selects boundary particles on the spherical exterior using the configured
   center, radius, tolerance, and optional `mkbound`;
2. assigns the prescribed drained value to those boundary particles;
3. collects material-boundary hydraulic neighbor pairs;
4. contributes each pair to `LapPorePress` and `LapZ` before `PorePressRate`;
5. never clamps material pore pressure after the update.

For the C5e/C5f geometry, mode 4 selected `2418` boundary particles and
created `194490` material-boundary hydraulic pairs, about `328.53` pairs per
target material particle.

## Raw Weighting Issue

The raw C5e weighting used the boundary particle effective volume directly in
the pairwise Laplacian contribution. In the C5f normalized/capped diagnostics,
the same neighborhood has:

| Quantity | Mean | Max |
|---|---:|---:|
| Material partition `S_m = sum V_j W_ij` | 0.760021 | 0.995324 |
| Boundary partition `S_b = sum V_b W_ib` | 2.70005 | 3.23115 |
| Boundary fraction `S_b/(S_m+S_b)` | 0.770829 | 0.839209 |

This means the selected boundary shell contributes more kernel partition than
the local material neighborhood. With raw volume weighting, the drained
Dirichlet state is therefore counted too strongly. This is consistent with the
C5e pressure-only result:

- final center pressure: `-97.17 Pa`, i.e. negative over-drainage from an
  initially positive uniform excess field;
- final `PorePressRate` maxAbs: about `9.38e5 Pa/s`;
- final surface LapPorePress rate contribution estimate: about `1.62e5 Pa/s`.

The artifact is concentrated in the near-boundary hydraulic operator rather
than plasticity or source terms: all C5e/C5f runs have `Kplastic=0`, use
`HydraulicElevationSource=0`, and use the same linear elastic skeleton.

## Normalization Need

The boundary value must remain prescribed drained pressure (`p_b=0`), because
Cryer’s exterior condition is Dirichlet. The Adami/MLS idea should therefore be
used to normalize the boundary particle quadrature, not to extrapolate the
drained value from interior pore pressure.

C5f introduces a local weighting switch for mode 4:

```text
CurvedDrainedBoundaryWeighting=0  raw boundary-particle volume weighting
CurvedDrainedBoundaryWeighting=1  Adami-style local partition normalization
CurvedDrainedBoundaryWeighting=3  diagnostic missing-support capped weighting
```

Mode `1` computes `S_m` and `S_b` per material target and scales boundary
particle effective volume by:

```text
scale = min(1, 1 / (S_m + S_b))
```

Mode `3` is diagnostic only and scales by the missing-support estimate:

```text
scale = min(1, max(0, 1 - S_m) / S_b)
```

Neither mode changes the PR governing equation, the prescribed boundary value,
the material stress state, or the pressure update sequence.

## Audit Conclusion

Raw mode 4 over-drains because selected boundary particles add an excessive
local boundary partition to the Laplacian operator. A local normalized
partition weighting is the correct next limited refinement. It is still a
first-order normalization, not a full MLS boundary reconstruction.
