# C5e Boundary-Particle Drained Boundary Report

Date: 2026-05-12

## Objective

C5e tests a paper-style CPU-only boundary-particle hydraulic drained boundary
for the strict Cryer route. The goal is to stop tuning material-side spherical
ghost weights and instead let selected dummy/boundary particles carry a
prescribed drained hydraulic state and enter the PR `LapPorePress`/`LapZ`
operator.

This is still not a strict Cryer reproduction. No GPU run, Poisson-ratio sweep,
long run, or Figure 7B quantitative comparison was attempted.

## Source Change

C5e adds `CurvedDrainedBoundaryMode=4` under:

```xml
<parameter key="PorePressureBoundaryOperator" value="3" />
<parameter key="PorePressureCurvedDrained" value="1" />
```

Mode meanings now include:

- `0`: first-order spherical Dirichlet ghost;
- `1`: strengthened image ghost;
- `2`: diagnostic material surface clamp, not production;
- `3`: material-side multi-sample spherical Dirichlet quadrature;
- `4`: selected boundary-particle prescribed Dirichlet hydraulic state.

Additional mode-4 parameters are:

```xml
<parameter key="CurvedDrainedBoundaryTargetMkBound" value="0" />
<parameter key="CurvedDrainedBoundaryUseBoundaryParticles" value="1" />
<parameter key="CurvedDrainedBoundarySelectionTolerance" value="0.10" />
<parameter key="CurvedDrainedBoundaryAdamiDiagnostic" value="1" />
```

The drained value is prescribed `p_w=0`. Under
`HydraulicElevationSource=0`, this also means `ExcessPorePress=0`.

Mode 4 does not clamp material particles. It projects selected boundary
particles to the drained spherical surface as hydraulic quadrature sites and
adds their prescribed state to `LapPorePress` and `LapZ` before
`PorePressRate`.

## Test Package

Retained package:

```text
examples/u-pw/03_Cryer_Problem/strict_reproduction_plan/C5e_BoundaryParticleDrained/
```

CPU Release tests:

| Case | Purpose |
|---|---|
| `mode3_shell` | Compression control using C5d mode 3. |
| `mode4_boundary_particles` | Compression with boundary-particle Dirichlet mode 4. |
| `diffusion_mode3_shell` | Pressure-only diffusion control using mode 3. |
| `diffusion_mode4_boundary_particles` | Pressure-only diffusion with mode 4. |

All four cases completed with `code=0`, `excluded=0`, and `Kplastic=0`.

## Boundary Selection

Mode 4 selected `2418` boundary particles with `mkbound=0`. The compression
and diffusion runs recorded `194490` material-boundary hydraulic pairs, or
about `328.53` boundary pairs per material target.

The Adami diagnostic was enabled:

- compression: diagnostic boundary excess mean/max `0 Pa`, because the
  boundary field starts from zero;
- diffusion: diagnostic boundary excess mean/max `1000 Pa`, showing that an
  extrapolated boundary value would have copied the interior excess and would
  not represent a drained boundary.

## Compression Results

| Metric | Mode 3 control | Mode 4 boundary particles |
|---|---:|---:|
| Center peak | `7.657 p0` | `6.908 p0` |
| Peak time | `0.002011 s` | `0.002011 s` |
| Final center pressure | `2.796 p0` | `-0.119 p0` |
| Final `r>0.85R` surface p95 | `208.90 Pa` | `195.08 Pa` |
| Final `r>0.85R` surface maxAbs | `252.39 Pa` | `195.08 Pa` |
| Final velocity max | `1.05e-3 m/s` | `1.71e-3 m/s` |

Mode 4 materially reduces the center peak compared with the current mode-3
quadrature and slightly lowers the material surface residual. However, the
final center pressure crosses slightly negative and the operator contribution
is much stronger, indicating that the present boundary-volume normalization is
too aggressive.

## Pressure-Only Diffusion Results

| Metric | Mode 3 control | Mode 4 boundary particles |
|---|---:|---:|
| Final center average | `946.83 Pa` | `-97.17 Pa` |
| Final material mean excess | `935.71 Pa` | `-21.22 Pa` |
| Final surface p95 `r>0.85R` | `946.35 Pa` | `336.16 Pa` |
| Final velocity max | `1.91e-4 m/s` | `2.67e-3 m/s` |
| Final `PorePressRate` maxAbs | `3.47e4 Pa/s` | `9.38e5 Pa/s` |

Mode 4 strongly increases drainage compared with mode 3, but it overshoots
the pressure-only diffusion case and introduces large pressure-rate
oscillations. This is the clearest pressure-rate artifact in C5e.

## Interpretation

Mode 4 confirms that boundary-particle hydraulic participation can strongly
affect the material surface layer. It is more aligned with the literature route
identified in LIT-B than the previous material-side virtual samples.

The current implementation is not yet a production-quality drained curved
boundary:

- the center peak is reduced, but remains far above the analytical Cryer range;
- pressure-only diffusion over-drains and becomes oscillatory;
- boundary contribution magnitudes are much larger than the mode-3 control;
- the effective boundary volume/quadrature normalization needs a principled
  MLS/Adami-style treatment.

## Answers to C5e Questions

1. `CurvedDrainedBoundaryMode=4` is implemented.
2. It uses selected boundary particles, not material-side virtual samples.
   The boundary particles provide angular quadrature sites projected to the
   drained spherical surface.
3. The drained boundary value is prescribed `p_w=0`; with
   `HydraulicElevationSource=0`, `excess=0` as well.
4. Boundary particles enter `LapPorePress` and `LapZ` before `PorePressRate`.
5. Surface residual decreases only moderately in compression:
   p95 `208.90 Pa -> 195.08 Pa`.
6. Center peak decreases from `7.657 p0` to `6.908 p0`, which is material but
   not enough for C6.
7. Pressure-only diffusion is faster, but not cleanly improved; it over-drains
   and oscillates.
8. Pressure-rate artifacts are present in mode 4, especially in the
   pressure-only diffusion case.
9. `Kplastic` remains exactly zero in all retained tests.
10. Mode 4 is a better direction than continuing mode-3 quadrature tuning, but
    it needs MLS/Adami-normalized boundary-volume refinement before dp/geometry
    refinement or C6.

## Recommendation

Do not enter C6 quantitative Figure 7B comparison yet. The next useful step is
a focused MLS/Adami boundary-particle normalization refinement:

- keep prescribed drained value `p_w=0`;
- use boundary particles as operator quadrature;
- normalize boundary contribution so pressure-only diffusion drains without
  negative overshoot or large pressure-rate artifacts;
- only then revisit modest geometry/dp refinement.

GPU remains deferred.
