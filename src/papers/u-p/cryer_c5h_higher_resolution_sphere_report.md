# C5h Higher-Resolution Cryer Sphere Diagnostic

## Objective

C5h tests one additional sphere resolution after C5g. The goal is to decide whether the excessive center pressure peak and surface residual are mainly caused by the still-coarse sphere geometry, or whether the normalized boundary-particle drained operator remains the main blocker.

No source files were modified. No GPU run was performed. No Poisson-ratio sweep or Figure 7B quantitative comparison is claimed.

## Setup

The C5h package is retained under:

`examples/u-pw/03_Cryer_Problem/strict_reproduction_plan/C5h_HigherResolutionSphere/`

The higher-resolution cases copy the C5g normalized mode-4 setup:

- `SoilConstitutiveModel=0`
- `FlexibleConfiningStress=1`, `ConfiningStressP0=50 Pa` for compression
- `HydraulicElevationSource=0`
- `PorePressureBoundaryOperator=3`
- `PorePressureCurvedDrained=1`
- `CurvedDrainedBoundaryMode=4`
- `CurvedDrainedBoundaryWeighting=1`
- `SavePorePressure=1`
- CPU Release only

Only the particle spacing was changed for C5h:

| Resolution | dp | Material particles | Selected drained boundary particles | Material-boundary pairs |
|---|---:|---:|---:|---:|
| C5g coarse | 0.0100 | 739 | 2418 | 194490 |
| C5g finer | 0.0080 | 1213 | 3794 | 315386 |
| C5h higher | 0.0065 | 2601 | 5802 | 650052 |

Two C5h cases were run:

- higher-resolution compression Cryer smoke;
- higher-resolution pressure-only spherical diffusion.

## Geometry Quality

The higher-resolution sphere increases particle counts substantially, but the shell quality does not improve monotonically:

| Metric | C5g coarse | C5g finer | C5h higher |
|---|---:|---:|---:|
| material particles | 739 | 1213 | 2601 |
| max material radius | 0.05477 | 0.05246 | 0.05554 |
| max surface radius abs error | 0.00641 | 0.00692 | 0.00738 |
| mean surface radius error | 0.000153 | -0.002015 | -0.000364 |
| surface roughness std | 0.00358 | 0.00303 | 0.00365 |
| center count `r<0.1R` | 1 | 1 | 1 |
| center count `r<0.15R` | 1 | 1 | 7 |
| center count `r<0.2R` | 7 | 7 | 19 |
| center count `r<0.4R` | 33 | 81 | 123 |
| surface count `r>0.85R` | 398 | 594 | 1412 |

The center averaging population improves, but the generated spherical surface is not smoother at `dp=0.0065`. This matters: more particles do not automatically mean a cleaner curved-boundary discretization for this lattice-generated sphere.

## Run Status

Both C5h CPU Release cases completed successfully:

| Case | code | excluded | Kplastic max | runtime | steps | frames |
|---|---:|---:|---:|---:|---:|---:|
| higher compression | 0 | 0 | 0 | 25.42 s | 88 | 7 |
| higher diffusion | 0 | 0 | 0 | 25.80 s | 88 | 7 |

The linear-elastic skeleton remained active and no plasticity occurred.

## Compression Response

The higher-resolution sphere continues to lower the averaged center peak, but only moderately:

| Metric | C5g coarse | C5g finer | C5h higher |
|---|---:|---:|---:|
| center peak `p_w/p0` | 7.448 | 7.058 | 6.731 |
| peak time | 0.002011 s | 0.002011 s | 0.002026 s |
| final center `p_w/p0` | 1.607 | -0.740 | -1.815 |
| final velocity max | 1.12e-3 m/s | 6.01e-3 m/s | 7.81e-3 m/s |

The peak reduction from `dp=0.008` to `0.0065` is about 4.6 percent. This confirms sphere resolution contributes to the center response, but the peak is still far above the Cryer `nu=0.3` reference scale.

## Surface Residual

The surface residual becomes worse in the higher-resolution compression case:

| Final `r>0.85R` metric | C5g coarse | C5g finer | C5h higher |
|---|---:|---:|---:|
| surface mean excess | 86.55 Pa | -66.38 Pa | -42.93 Pa |
| surface median excess | 85.30 Pa | -59.01 Pa | -77.82 Pa |
| surface p95 abs | 131.56 Pa | 131.42 Pa | 244.34 Pa |
| surface p99 abs | 182.96 Pa | 273.33 Pa | 351.37 Pa |
| surface max abs | 182.96 Pa | 273.33 Pa | 762.49 Pa |

This is the most important C5h result: adding particles does not solve the drained material-surface coupling. The current boundary-particle selection / normalized weighting remains sensitive to the generated shell geometry and can amplify surface residuals.

## Center Averaging Sensitivity

At the peak frame:

| Averaging radius | C5g coarse | C5g finer | C5h higher |
|---|---:|---:|---:|
| nearest | 8.236 | 6.980 | 5.613 |
| `0.1R` | 8.236 | 6.980 | 5.613 |
| `0.15R` | 8.236 | 6.980 | 6.171 |
| `0.2R` | 7.959 | 7.022 | 6.478 |
| `0.3R` | 7.713 | 7.060 | 6.780 |
| `0.4R` | 7.448 | 7.058 | 6.731 |

The finer `dp=0.008` case had the smallest center-averaging spread. The `dp=0.0065` case has more center particles but a stronger radius dependence, with the nearest particle lower than the wider average. Center extraction is therefore not cleanly converged.

## Pressure-Only Diffusion

Pressure-only diffusion does not improve at the higher resolution:

| Metric | C5g coarse | C5g finer | C5h higher |
|---|---:|---:|---:|
| final center pressure | 529.96 Pa | 468.25 Pa | 746.40 Pa |
| final mean excess pressure | 492.92 Pa | 367.19 Pa | 524.07 Pa |
| final surface p95 | 527.39 Pa | 350.91 Pa | 1023.40 Pa |
| final max pressure-rate | 3.33e5 Pa/s | 3.86e5 Pa/s | 1.55e6 Pa/s |

The `dp=0.008` case was the best of the three for pressure-only diffusion. The higher-resolution case has stronger pressure-rate artifacts and larger final surface residuals.

## Interpretation

C5h confirms that sphere resolution matters, but it does not support a simple “increase resolution and proceed to C6” path:

- center peak decreases monotonically with refinement, but slowly;
- surface residual does not decrease and becomes worse at `dp=0.0065`;
- pressure-only diffusion becomes worse at `dp=0.0065`;
- center averaging improves in particle count but not in monotonic stability;
- the generated sphere surface quality is not monotonic with `dp`.

The main blocker remains the drained spherical boundary / radial flux consistency, not just particle count. A better geometric surface representation may be useful later, but broad dp refinement should not be the next step.

## Decision

C6 quantitative Figure 7B comparison remains premature.

Recommended next step:

1. Return to MLS / flux-consistent drained spherical boundary calibration.
2. Use pressure-only spherical diffusion as the first gate.
3. After the boundary rule is stable, repeat the modest geometry diagnostic and then decide whether a planned resolution trend is useful.

GPU remains deferred because the strict Cryer route still depends on CPU-only `FlexibleConfiningStress`, `PorePressureBoundaryOperator=3`, `CurvedDrainedBoundaryMode=4`, and `HydraulicElevationSource=0`.
