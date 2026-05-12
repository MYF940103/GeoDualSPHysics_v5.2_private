# C5g Cryer Sphere Geometry and dp Diagnostic

## Objective

C5g tests whether the high center pressure peak in the coarse CPU Cryer smoke is mainly caused by coarse sphere geometry / particle spacing rather than the current drained boundary operator. This is a narrow diagnostic only: no source files were modified, no GPU run was performed, no Poisson-ratio sweep was run, and no Figure 7B quantitative claim is made.

The C5f normalized boundary-particle drained setup was used as the baseline:

- `SoilConstitutiveModel=0`
- `FlexibleConfiningStress=1` for compression tests
- `ConfiningStressP0=50 Pa`
- `HydraulicElevationSource=0`
- `PorePressureBoundaryOperator=3`
- `PorePressureCurvedDrained=1`
- `CurvedDrainedBoundaryMode=4`
- `CurvedDrainedBoundaryWeighting=1`
- CPU Release only

## Cases

The retained diagnostic package is:

`examples/u-pw/03_Cryer_Problem/strict_reproduction_plan/C5g_GeometryDpDiagnostic/`

Four CPU Release cases were prepared and run:

| Case | Purpose | dp | Flexible confining stress | Initial pressure |
|---|---:|---:|---:|---:|
| coarse compression | C5f normalized baseline replay | 0.010 | on, `p0=50 Pa` | 0 Pa |
| finer compression | one-level finer geometry diagnostic | 0.008 | on, `p0=50 Pa` | 0 Pa |
| coarse diffusion | pressure-only baseline | 0.010 | off | 1000 Pa |
| finer diffusion | one-level finer pressure-only diagnostic | 0.008 | off | 1000 Pa |

The sphere radius was kept fixed at `R=0.05`. Only the particle spacing / generated particle cloud was changed in the finer variant.

## Geometry Quality

The one-level finer sphere reduced `dp` by 20 percent and increased the material particle count from `739` to `1213`.

| Metric | Coarse | Finer | Interpretation |
|---|---:|---:|---|
| configured `dp` | 0.010 | 0.008 | one modest refinement level |
| material particles | 739 | 1213 | +64 percent |
| selected drained boundary particles | 2418 | 3794 | +57 percent |
| material-boundary pairs | 194490 | 315386 | +62 percent |
| surface roughness std | 0.00358 | 0.00303 | improved by about 15 percent |
| max material radius | 0.05477 | 0.05246 | closer to target radius |
| center count, `r<0.1R` | 1 | 1 | unchanged |
| center count, `r<0.2R` | 7 | 7 | unchanged |
| center count, `r<0.4R` | 33 | 81 | substantially improved |

The finer cloud is smoother, but the strict center still has only one particle for `0.1R` and `0.15R`, and seven particles for `0.2R`. This remains a coarse center-pressure extraction.

## Run Status

All four C5g cases completed successfully:

| Case | code | excluded | Kplastic max |
|---|---:|---:|---:|
| coarse compression | 0 | 0 | 0 |
| finer compression | 0 | 0 | 0 |
| coarse diffusion | 0 | 0 | 0 |
| finer diffusion | 0 | 0 | 0 |

The linear-elastic skeleton switch remained active and no plasticity occurred.

## Compression Response

The finer sphere modestly lowered the center peak:

| Metric | Coarse | Finer |
|---|---:|---:|
| center peak | 372.40 Pa | 352.88 Pa |
| normalized center peak | 7.448 p0 | 7.058 p0 |
| peak time | 0.002011 s | 0.002011 s |
| final averaged center pressure | 80.37 Pa | -36.98 Pa |
| final normalized center pressure | 1.607 p0 | -0.740 p0 |
| final velocity max | 1.12e-3 m/s | 6.01e-3 m/s |

The peak reduction is real but small: about 5.2 percent. The response remains far above the expected Cryer `nu=0.3` reference scale, so coarse geometry is not the dominant blocker by itself.

## Surface Residual

The compression surface residual did not materially improve in the main `r>0.85R` p95 metric:

| Metric, final `r>0.85R` shell | Coarse | Finer |
|---|---:|---:|
| surface p95 abs | 131.56 Pa | 131.42 Pa |
| surface max abs | 182.96 Pa | 273.33 Pa |

The p95 residual is nearly unchanged, and the maximum residual becomes larger in the finer case. This points back to boundary/operator coupling rather than only geometric roughness.

## Center Averaging Sensitivity

At the peak frame (`t=0.002011 s`), the coarse sphere shows visible center-averaging sensitivity:

| Averaging radius | Coarse `p_w/p0` | Finer `p_w/p0` |
|---|---:|---:|
| nearest | 8.236 | 6.980 |
| `0.1R` | 8.236 | 6.980 |
| `0.2R` | 7.959 | 7.022 |
| `0.3R` | 7.713 | 7.060 |
| `0.4R` | 7.448 | 7.058 |

The finer case reduces the spread between nearest-particle and larger-radius averages. Center extraction noise is therefore part of the C5/C5f error budget, but it cannot explain the remaining peak near `7 p0`.

## Pressure-Only Diffusion

The optional pressure-only diffusion diagnostic was run for both resolutions. The finer sphere improved drainage without the strong negative over-drainage seen in raw C5e mode 4:

| Metric | Coarse | Finer |
|---|---:|---:|
| final center pressure | 529.96 Pa | 468.25 Pa |
| final mean excess pressure | 596.96 Pa | 445.67 Pa |
| final `r>0.85R` surface p95 | 527.39 Pa | 350.91 Pa |
| final pressure-rate maxAbs | 2.71e5 Pa/s | 2.30e5 Pa/s |

This indicates that geometry quality matters for diffusion behavior. However, the compression surface residual remains nearly unchanged, so a better geometry alone is unlikely to produce a C6-ready Cryer response.

## Figures and Metrics

Generated CSV outputs include:

- `c5g_case_summary.csv`
- `c5g_sphere_quality_metrics.csv`
- `c5g_geometry_comparison_metrics.csv`
- `c5g_center_pressure_comparison.csv`
- `c5g_surface_residual_comparison.csv`
- `c5g_center_averaging_sensitivity.csv`
- `c5g_radial_profile_metrics.csv`
- `c5g_boundary_selection_metrics.csv`
- `c5g_pressure_only_diffusion_metrics.csv`

Generated figures include center pressure, surface residuals, radial profiles, averaging sensitivity, sphere quality summaries, pressure-rate diagnostics, velocity, and `Kplastic` checks.

## Decision

C5g shows that geometry resolution is a secondary contributor:

- finer geometry lowers the normalized center peak from `7.45 p0` to `7.06 p0`;
- center averaging sensitivity decreases;
- pressure-only diffusion improves;
- compression surface residual does not materially decrease;
- the center peak remains much too high for Figure 7B comparison.

Therefore, the coarse sphere is not the main blocker. C6 quantitative comparison remains paused. The recommended next step is not a broad dp study, but a boundary/operator refinement focused on MLS or flux-consistent radial diffusion at the drained spherical surface. A later modest geometry refinement will be useful after the boundary rule is improved.

GPU remains deferred because the strict Cryer path still depends on CPU-only `FlexibleConfiningStress`, `PorePressureBoundaryOperator=3`, `CurvedDrainedBoundaryMode=4`, and `HydraulicElevationSource=0`.
