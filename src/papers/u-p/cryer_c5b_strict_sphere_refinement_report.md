# Cryer C5b Strict-Sphere Refinement Report

Date: 2026-05-12

## Objective

C5b refines the coarse CPU strict-sphere Cryer smoke without changing source
code. The goal is to identify whether the C5 over-peak and residual pressure
mainly come from the loading ramp, time-window truncation, coarse center
averaging, near-surface drainage control, or free-sphere dynamics.

This is still not a Figure 7B quantitative reproduction. No GPU run, Poisson
sweep, long run, or corrected-gradient work was performed.

## Variants

All variants use the C5 coarse sphere (`R=0.05 m`, `dp=0.01 m`, `739` initial
material particles), `SoilConstitutiveModel=0`, `FlexibleConfiningStress=1`,
`PorePressureBoundaryOperator=3`, `PorePressureCurvedDrained=1`, and
`HydraulicElevationSource=0`.

| Variant | p0 (Pa) | Ramp end (s) | TimeMax (s) | Result |
|---|---:|---:|---:|---|
| baseline | 50 | 0.0005 | 0.006 | `code=0`, `excluded=0` |
| slow_ramp | 50 | 0.005 | 0.012 | `code=0`, `excluded=0` |
| lower_p0 | 10 | 0.0005 | 0.006 | `code=0`, `excluded=0` |
| long_slow_ramp | 50 | 0.005 | 0.05 | `code=0`, `excluded=425`; not a passing smoke |

`Kplastic` stayed zero in all retained frame metrics, as expected for
`SoilConstitutiveModel=0`.

## Main Metrics

Primary center averaging uses radius `0.01 m` (`0.2R`, 7 particles in the
initial intact sphere). The previous C5 comparison radius `0.02 m` is also
reported in the radius-sensitivity table.

| Variant | Peak center excess / p0 | Peak time (s) | Final center excess / p0 | Final velocity max (m/s) | Final near-surface excess maxAbs (Pa) |
|---|---:|---:|---:|---:|---:|
| baseline | 8.181 | 0.002011 | 2.957 | 1.063e-03 | 263.15 |
| slow_ramp | 7.662 | 0.012065 | 7.662 | 8.951e-03 | 994.76 |
| lower_p0 | 8.181 | 0.002011 | 2.956 | 2.125e-04 | 52.63 |
| long_slow_ramp | 9629.91 | 0.035009 | -6510.16 | 2.134e+01 | 6.14e+05 |

The long slow-ramp case began excluding particles at `t≈0.025 s` and ended
with `425` excluded particles. It is useful as a failure signal for the coarse
free-sphere setup, not as a valid longer-window dissipation result.

## Ramp Effect

The slower ramp strongly reduces the early pressure rise at the same early
time: at `t≈0.002 s`, the slow-ramp primary center average is about `1.57 p0`,
whereas the baseline is about `8.18 p0`.

However, the slow-ramp run does not eliminate the high normalized response. It
continues rising and reaches `7.66 p0` by `t=0.012065 s`, with larger final
velocity and much larger near-surface material excess than the baseline. The
C5 high peak therefore cannot be attributed only to an overly fast ramp.

## p0 Linearity

The lower-load case is almost exactly linearly scaled relative to the baseline:

- baseline peak at radius `0.01 m`: `409.07 Pa = 8.181 p0`;
- lower p0 peak at radius `0.01 m`: `81.81 Pa = 8.181 p0`;
- baseline final center pressure: `2.957 p0`;
- lower p0 final center pressure: `2.956 p0`.

This rules out plasticity or load-magnitude nonlinearity as the main cause of
the coarse over-peak. It is more consistent with the current coarse geometry,
operator/boundary behavior, and dynamic free-sphere response.

## Time Window

The attempted longer slow-ramp observation window did not provide a clean
dissipation trend. The run was stable only up to about `0.02 s`; particle
exclusion started at `t≈0.025 s`, followed by large velocity and pressure
oscillation. The C5 final residual cannot yet be interpreted as the physical
long-time pressure state, but this specific coarse free-sphere configuration is
not ready for longer integration.

## Center Averaging Sensitivity

The center metric is sensitive to averaging radius, but this sensitivity is not
large enough to explain the entire over-peak.

For the baseline:

| Radius | Radius/R | Final count | Peak p/p0 | Final p/p0 |
|---:|---:|---:|---:|---:|
| 0.005 | 0.10 | 1 | 8.448 | 3.038 |
| 0.0075 | 0.15 | 1 | 8.448 | 3.038 |
| 0.01 | 0.20 | 7 | 8.181 | 2.957 |
| 0.02 | 0.40 | 33 | 7.672 | 2.923 |

The `0.02 m` average reduces the peak by about 9 percent relative to the
single-nearest-particle estimate. That is a meaningful coarse-particle
postprocessing effect, but it does not turn the current response into a
quantitative Cryer curve.

## Boundary Residual

The operator-level curved drained ghost diagnostic reports zero prescribed
ghost residual for all variants, but the material near-surface excess remains
large:

- baseline final near-surface material excess maxAbs: `263 Pa` (`5.26 p0`);
- slow-ramp final near-surface material excess maxAbs: `995 Pa` (`19.9 p0`);
- lower-p0 final near-surface material excess maxAbs: `52.6 Pa` (`5.26 p0`).

This is the most important C5b signal. The ghost boundary is active, but the
coarse material surface layer is not being held close enough to the drained
condition for a strict Cryer comparison.

## Figures and Data

Retained C5b outputs:

- `c5b_case_summary.csv`
- `c5b_center_pressure_comparison.csv`
- `c5b_boundary_residual_comparison.csv`
- `c5b_loading_ramp_metrics.csv`
- `c5b_averaging_radius_sensitivity.csv`
- `c5b_center_pressure_by_radius.csv`
- `c5b_stability_metrics.csv`

Figures:

- `c5b_center_normalized_pressure_primary_radius.svg/png`
- `c5b_center_averaging_radius_sensitivity.svg/png`
- `c5b_near_surface_material_excess.svg/png`
- `c5b_operator_boundary_residual.svg/png`
- `c5b_velocity_max.svg/png`
- `c5b_surface_radial_velocity.svg/png`
- `c5b_porepress_rate_maxabs.svg/png`
- `c5b_lapz_rate_contribution.svg/png`
- `c5b_kplastic_maxabs.svg/png`

## Decision

C5b should not proceed directly to C6 quantitative Figure 7B comparison.

The best-supported interpretation is:

1. The response is linear in `p0` over the tested range.
2. The loading ramp affects peak timing and early-time magnitude, but is not
   the sole cause of the high normalized peak.
3. The longer window fails because the current coarse free sphere enters an
   oscillatory/out-check regime.
4. Center averaging matters, but only moderately.
5. The most actionable blocker is still the drained material surface behavior:
   the boundary ghost condition is active, but near-surface material excess
   remains too large.

Recommended next step: boundary refinement before C6. A geometry/resolution
refinement will also be needed, but it should follow a clearer drained-surface
control strategy; otherwise finer runs may simply make the same boundary issue
more expensive. GPU remains deferred.
