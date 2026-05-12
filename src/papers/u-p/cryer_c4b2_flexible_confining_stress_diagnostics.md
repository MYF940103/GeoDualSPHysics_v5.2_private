# Cryer C4-B2 Flexible Confining Stress Diagnostics

Date: 2026-05-12

## Objective

The flexible confining stress route must be verified before it is used for any
Cryer pressure comparison. This document defines the minimum diagnostics for
C4-B3.

## Required Diagnostics

| Diagnostic | Purpose |
|---|---|
| Net confining force vector | A spherical load should have near-zero net force by symmetry. |
| Total absolute confining force | Tracks the magnitude of applied mechanical work; useful for regression checks. |
| Center-of-mass acceleration | Should remain near zero for a symmetric sphere. |
| Confining work / power | Detects sign errors and excessive numerical work. |
| Max confining acceleration | Detects spikes near isolated particles or bad density/marker selection. |
| Symmetry residual | Norm of net force divided by total absolute force. |
| Radial acceleration projection | Surface acceleration should be inward for positive compressive `p0`. |
| Interior cancellation check | Interior bins should show much smaller confining acceleration than surface bins. |
| Surface localization check | Acceleration should concentrate near the free surface, not throughout the sphere. |
| CPU/GPU parity metrics | Required only after GPU support is implemented. |
| Pore-pressure sign check | In a coupled Cryer smoke, compression should initially raise center pore pressure. |

## Suggested CSV Output

For future implementation smoke tests:

```text
time,p0_ramp,net_fx,net_fy,net_fz,total_abs_force,com_ax,com_ay,com_az,
max_conf_accel,mean_conf_accel,symmetry_residual,mean_radial_accel_surface,
mean_radial_accel_interior,confining_power
```

## Radial Binning

For a sphere centered at `c` with radius `a`, compute:

```text
r_i = |x_i - c|
e_r = (x_i - c) / r_i
a_radial = a_conf_i dot e_r
```

For compression, the surface value should be negative if `e_r` is outward.
Interior bins should approach zero because the confining stress contribution
cancels by kernel symmetry.

## Stop Criteria for C4-B3

Stop before any Cryer physics claim if:

- net force symmetry residual is large;
- center-of-mass acceleration is not negligible;
- surface radial acceleration points outward for positive compression;
- interior acceleration is comparable to surface acceleration;
- enabling the source changes no-load regression behavior;
- pressure sign check shows center pressure decreasing under compression.

## Figure Suggestions

- radial acceleration profile by `r/a`;
- symmetry residual versus time;
- net force vector components versus time;
- confining power versus time;
- center pore-pressure sign smoke if hydromechanical coupling is enabled.

