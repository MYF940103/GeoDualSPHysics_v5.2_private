# Stage 1 parameter tuning summary

Date: 2026-06-03

This note records the parameter tuning performed for the Stage 1 undrained self-weight step of the u-pw PR self-weight consolidation case.

## Verification target

Stage 1 is intended to generate the undrained self-weight excess pore pressure state before the consolidation restart:

- `WaterTableMode=None`: no hydrostatic pore-pressure initialization.
- `HydraulicConductivity=0`: undrained response during Stage 1.
- `TimeMax=0.20 s`: long enough for the kinematic oscillation to decay for this resolution.
- Material stayed elastic in all accepted comparison runs (`Kplastic=0`).

The comparison metric was the simulated layer-averaged excess pore pressure against the analytical undrained self-weight profile, with additional checks on high-frequency residuals and maximum particle speed.

## Soil damping

Without Shepard regularization, varying `SoilDampingCoef` from `0.01` to `0.05` changed the global settling speed but did not remove the odd-even pore-pressure oscillation.

At `t=0.20 s`, representative results were:

| SoilDampingCoef | Bottom residual [kPa] | RMS residual [kPa] | HF residual RMS [kPa] | Max speed [m/s] |
|---:|---:|---:|---:|---:|
| 0.01 | -1.644 | 1.677 | 0.273 | 2.19e-3 |
| 0.02 | 0.332 | 0.419 | 0.277 | 4.10e-4 |
| 0.03 | 0.681 | 0.343 | 0.278 | 7.76e-5 |
| 0.04 | 0.743 | 0.346 | 0.278 | 1.48e-5 |
| 0.05 | 0.753 | 0.347 | 0.278 | 2.68e-6 |

Conclusion: damping alone is not enough. `0.03-0.04` is the useful range, but the high-frequency pore-pressure residual requires filtering or a better pressure stabilization.

## Shepard regularization interval

With `SoilDampingCoef=0.03`, enabling Shepard regularization strongly reduced the odd-even pore-pressure mode.

At `t=0.20 s`:

| PoreShepardInterval | Bottom residual [kPa] | RMS residual [kPa] | HF residual RMS [kPa] | Max speed [m/s] |
|---:|---:|---:|---:|---:|
| off | 0.681 | 0.343 | 0.278 | 7.76e-5 |
| 20 | -0.892 | 0.142 | 0.0206 | 6.11e-5 |
| 30 | -0.694 | 0.105 | 0.0199 | 3.71e-5 |
| 40 | -0.593 | 0.088 | 0.0194 | 6.57e-5 |

Conclusion: `PoreShepardInterval=40` gave the best final profile in this interval sweep while still suppressing the high-frequency residual.

## Soil damping with Shepard

The combination `SoilDampingCoef=0.04` and `PoreShepardInterval=40` improved the earlier `t=0.10 s` state compared with `SoilDampingCoef=0.03`, while giving almost the same final profile at `t=0.20 s`.

At `t=0.20 s`:

| Case | Bottom residual [kPa] | RMS residual [kPa] | HF residual RMS [kPa] | Max speed [m/s] |
|---|---:|---:|---:|---:|
| `xi=0.03`, Shepard 40 | -0.593 | 0.088 | 0.0194 | 6.57e-5 |
| `xi=0.04`, Shepard 40 | -0.581 | 0.090 | 0.0194 | 3.33e-5 |

Conclusion: use `SoilDampingCoef=0.04` for Stage 1.

## Artificial viscosity

With `SoilDampingCoef=0.04`, `PoreShepardRegularization=1`, and `PoreShepardInterval=40`, artificial viscosity had only a small effect on the final Stage 1 state.

At `t=0.20 s`:

| Visco | Bottom residual [kPa] | RMS residual [kPa] | HF residual RMS [kPa] | Max speed [m/s] |
|---:|---:|---:|---:|---:|
| 0.2 | -0.576 | 0.0909 | 0.0194 | 3.38e-5 |
| 0.4 | -0.581 | 0.0900 | 0.0194 | 3.33e-5 |
| 0.6 | -0.585 | 0.0895 | 0.0194 | 3.32e-5 |

At `t=0.10 s`, `Visco=0.2` was closer to the analytical pore-pressure profile but retained a slightly larger maximum speed; `Visco=0.6` reduced speed slightly but increased early underestimation. By `t=0.20 s`, all three nearly overlapped.

Conclusion: retain the supporting-material value `Visco=0.4`.

## Final Stage 1 defaults

The recommended default Stage 1 parameter set is:

```xml
<WaterTableMode value="None" />
<HydraulicConductivity value="0" />
<PoreShepardRegularization value="1" />
<PoreShepardInterval value="40" />
<parameter key="Visco" value="0.4" />
<parameter key="SoilDamping" value="1" />
<parameter key="SoilDampingCoef" value="0.04" />
<parameter key="TimeMax" value="0.20" />
<parameter key="TimeOut" value="0.005" />
```

Use `TimeOut=0.001` only for temporary diagnostic runs when the early oscillation phase needs to be resolved.
