# Corrected Cryer early-time sweep (2026-06-21)

## Objective

Repeat the early Cryer comparison using the corrected analytical solution from
the u-pw reference paper Equations (46)-(47). The sweep only targets the early
window up to about `T_v=0.1`; full-cycle runs should wait until this early
response is acceptable.

All runs used:

- resolution `Dp=0.003 m`;
- `HydroMechTopLoadMode=3` (`FlexibleConfinement`);
- `HydraulicConductivity=1e-4 m/s`;
- `SoilDampingCoef=0.02`;
- paper-style comparison axes: logarithmic `T_v`, normalized center pore
  pressure `p^w/p0`.

## Cases

| Case | Ramp (s) | Drainage start (s) | Theory origin (s) | Meaning |
| --- | ---: | ---: | ---: | --- |
| `r0000_d0` | 0 | 0 | 0 | Instant load, drainage active from start. |
| `r0010_d0` | 0.001 | 0 | 0.001 | Very short ramp, drainage active from start. |
| `r0025_d0` | 0.0025 | 0 | 0.0025 | Short ramp, drainage active from start. |
| `r0050_d0` | 0.005 | 0 | 0.005 | Longer ramp, drainage active from start. |
| `r0000_d0100` | 0 | 0.010 | 0.010 | Instant load, undrained hold, then drain. |
| `r0050_d0150` | 0.005 | 0.015 | 0.015 | Ramp load, undrained hold, then drain. |

## Main metrics to T_v about 0.1

| Case | Origin center p/p0 | Peak p/p0 | Theory peak in sampled window | RMSE | Max speed (m/s) |
| --- | ---: | ---: | ---: | ---: | ---: |
| `r0000_d0` | 1.0635 | 1.2060 | 1.2484 | 0.0411 | 0.0396 |
| `r0010_d0` | 1.0481 | 1.2054 | 1.2484 | 0.0428 | 0.0274 |
| `r0025_d0` | 1.1316 | 1.1977 | 1.2481 | 0.0644 | 0.0135 |
| `r0050_d0` | 1.1441 | 1.1815 | 1.2484 | 0.1220 | 0.0111 |
| `r0000_d0100` | 0.9976 | 1.2062 | 1.2484 | 0.0388 | 0.0398 |
| `r0050_d0150` | 0.9976 | 1.2062 | 1.2484 | 0.0388 | 0.0400 |

## Interpretation

- The corrected analytical peak near `T_v~0.04-0.05` is about `1.25 p0`.
- Instant or very short ramp loading captures the early peak best, with
  numerical peaks around `1.206 p0`.
- Increasing ramp time reduces maximum speed but also suppresses the
  Mandel-Cryer peak and worsens the early-time pressure curve.
- Delaying drainage until the center pressure is close to `p0` works for the
  initial condition: both delayed cases have origin center pressure about
  `0.9976 p0` and very small velocity at the drainage-opening time.
- However, delayed drainage does not reduce the post-opening maximum speed. The
  max speed returns to about `0.04 m/s`, similar to instant loading/drainage.
  This suggests that the dominant early velocity peak is tied to the sudden
  activation of the drained surface boundary and the resulting pore-pressure
  redistribution, not only to the mechanical load ramp.
- The best early-pressure match in this sweep is the delayed-drainage path
  (`r0000_d0100` or `r0050_d0150`), but it fails the "velocity not high" target.
- The best compromise among drainage-from-start cases is `r0010_d0`: it keeps
  early pressure accuracy close to `r0000_d0` while reducing max speed by about
  30%, but the speed is still high.

## Next parameter direction

Further increasing mechanical ramp time is unlikely to solve the issue because
it suppresses the Cryer peak. The next more promising adjustment is to smooth
the drainage activation itself, for example by introducing a drainage ramp or a
gradual pore-pressure boundary enforcement over a short interval. This would
target the observed velocity spike without artificially reducing the external
load peak.

## Output artifacts

- `figures/cryer_corrected_sweep_20260621_summary.csv`
- `figures/cryer_corrected_sweep_20260621_summary.json`
- `figures/cryer_corrected_sweep_20260621_paper_axes.png`
- `figures/cryer_corrected_sweep_20260621_error_speed.png`
