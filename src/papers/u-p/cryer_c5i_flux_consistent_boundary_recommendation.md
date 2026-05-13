# C5i Flux-Consistent Boundary Recommendation

## Current Boundary Character

C5i maps the available pressure-only spherical diffusion diagnostics to an
effective boundary type.

The current `CurvedDrainedBoundaryMode=4` with
`CurvedDrainedBoundaryWeighting=1` is not behaving as a true drained
Dirichlet boundary. The apparent volume-storage flux is usually stronger than
the 1D radial FV reference, but the near-surface SPH pressure shell remains far
above the drained reference shell. At the higher `dp=0.0065` resolution, the
apparent flux reverses sign late in the short run.

Recommended classification:

```text
mode 4 normalized = over-strong, nonuniform Robin-like boundary
```

It is more stable than raw mode 4, but it is not flux-consistent.

## Why a Scalar Weight Change Is Not Enough

C5f showed that raw boundary-particle volume weighting was too strong and that
Adami-style normalization reduced the worst over-drainage artifact. C5i shows
that this does not fix the underlying boundary rule:

- volume-mean decay can be too fast;
- surface shell pressure can remain too high;
- center pressure decays too early for true radial diffusion;
- the error is nonmonotone with dp;
- the `dp=0.0065` boundary cloud produces a pressure-rate spike and flux
  reversal.

This is not a single global coefficient problem. The operator needs local
consistency with the spherical Dirichlet geometry and the radial flux.

## MLS / Flux-Consistent Boundary Requirements

The next source task should not implement a broad corrected-gradient path.
It should be a narrow CPU-only boundary-particle drained operator for the Cryer
spherical diffusion gate.

Minimum requirements:

1. Partition of unity
   - Constant pressure fields should reconstruct as constants near the boundary.
   - A uniform excess state should not create interior artifacts except through
     the prescribed drained boundary.

2. Linear consistency
   - Radial linear pressure profiles near the boundary should reconstruct the
     correct gradient against the physical spherical surface.
   - This is needed before trusting the boundary flux.

3. Local boundary flux consistency
   - For pressure-only spherical diffusion, the integrated SPH apparent flux
     should match the FV reference within a documented tolerance.
   - Acceptance should use both volume-mean decay and surface-shell pressure,
     not only center pressure.

4. Spherical normal consistency
   - Boundary particles should contribute according to the physical sphere
     normal and the projection to `R`, not only by cloud distance.
   - The selected boundary cloud should not amplify the operator when the
     generated lattice surface becomes rougher.

5. Diagnostics
   - Output local support sums, MLS condition/fallback counts, reconstructed
     boundary value residuals, and per-frame integrated boundary flux.
   - Keep pressure-only diffusion as the first gate before any compression run.

## Boundary Particle Selection

The current selected boundary count increases with refinement:

| dp | selected boundary particles | material-boundary pairs |
|---:|---:|---:|
| `0.010` | `2418` | `194490` |
| `0.008` | `3794` | `315386` |
| `0.0065` | `5802` | `650052` |

More selected particles did not improve the gate. The next source design should
therefore treat boundary selection as part of the operator, not a passive input.
Recommended checks:

- select particles relative to the physical sphere radius and shell tolerance;
- track angular coverage / patch uniformity;
- cap or normalize contributions through consistency equations, not through a
  diagnostic scalar cap;
- report fallback regions where MLS support is ill-conditioned.

## Sphere Generation

Sphere quality still matters. C5h/C5i show that the `dp=0.0065` generated
surface is not smoother than `dp=0.008`.

However, sphere generation should not be the next primary task. A cleaner
surface may reduce noise, but it will not by itself enforce the correct radial
diffusion flux. Revisit sphere generation after the pressure-only flux gate is
stable.

## Recommended Next Source Task

Implement a narrow CPU-only prototype:

```text
C5j: MLS / flux-consistent spherical drained boundary prototype
```

Scope:

- only pressure-only spherical diffusion first;
- no GPU;
- no Cryer compression initially;
- keep `SoilConstitutiveModel`, `FlexibleConfiningStress`,
  `HydraulicElevationSource`, and the PR governing equation unchanged;
- add a new experimental submode or clearly guarded option rather than changing
  the behavior of existing mode 4 normalized runs;
- include integrated boundary-flux diagnostics.

Acceptance gate before compression:

- FV volume-mean RMSE materially lower than C5i normalized mode 4;
- surface shell `0.95R-1.0R` pressure follows the FV reference trend;
- median flux ratio close to `1` without late sign reversal;
- no negative pressure overdrainage;
- no pressure-rate spike comparable to the C5h `dp=0.0065` case.

## C6 and GPU Decision

C6 remains blocked. The current boundary is not a validated drained spherical
Dirichlet operator.

GPU remains deferred. Porting the current CPU-only strict Cryer boundary would
only preserve a non-flux-consistent result. GPU work should resume only after
the CPU pressure-only radial diffusion gate passes.

