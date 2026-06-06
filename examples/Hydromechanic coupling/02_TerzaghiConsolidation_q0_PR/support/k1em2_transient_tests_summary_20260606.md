# k=1e-2 short transient tests summary

Date: 2026-06-06

Purpose: diagnose the early unloading / drainage transient in the q0 Terzaghi consolidation case for `k=1e-2`, using `DtFixed=1e-7`, `TimeMax=0.03 s`, and `TimeOut=0.0005 s`.

## Tests

### Damping sweep with tL=0.01

| SoilDampingCoef | max speed | max |U error| | U RMSE post tL | U RMSE Tv>=0.01 | first post-tL mean excess p (kPa) |
|---:|---:|---:|---:|---:|---:|
| 0.02 | 0.201370 | 0.669069 | 0.205528 | 0.039437 | 3.9037 |
| 0.04 | 0.198219 | 0.671420 | 0.216960 | 0.076459 | 3.8906 |
| 0.06 | 0.195142 | 0.673592 | 0.232841 | 0.114169 | 3.8789 |
| 0.08 | 0.192124 | 0.675645 | 0.250844 | 0.148947 | 3.8686 |
| 0.10 | 0.189199 | 0.677567 | 0.269529 | 0.180611 | 3.8593 |

Conclusion: increasing damping only slightly reduced the velocity peak, but clearly worsened U(t) and profile accuracy. `SoilDampingCoef=0.02` remained the best value in this group.

### Ramp-time comparison

| case | max speed | max |U error| | U RMSE post tL | U RMSE Tv>=0.01 | first post-tL mean excess p (kPa) |
|---|---:|---:|---:|---:|---:|
| tL=0.01 | 0.201370 | 0.669069 | 0.205528 | 0.039437 | 3.9037 |
| tL=0.001 | 0.232022 | 0.647364 | 0.162478 | 0.028852 | 3.1084 |

Conclusion: reducing `tL` from `0.01 s` to `0.001 s` improved early consolidation accuracy, although the mechanical velocity peak became larger.

### Damping sweep with tL=0.001

| SoilDampingCoef | max speed | max |U error| | U RMSE post tL | U RMSE Tv>=0.01 | first post-tL mean excess p (kPa) |
|---:|---:|---:|---:|---:|---:|
| 0.02 | 0.232022 | 0.647364 | 0.162478 | 0.028852 | 3.1084 |
| 0.04 | 0.228142 | 0.649207 | 0.175428 | 0.068052 | 3.0899 |
| 0.06 | 0.224356 | 0.651017 | 0.193474 | 0.105081 | 3.0718 |
| 0.08 | 0.220653 | 0.652793 | 0.213620 | 0.138646 | 3.0541 |
| 0.10 | 0.217070 | 0.654538 | 0.234211 | 0.169045 | 3.0366 |

Conclusion: with `tL=0.001 s`, increasing damping again reduced the velocity peak only mildly and degraded U(t) accuracy. The best tested combination remains `tL=0.001 s`, `SoilDampingCoef=0.02`.

## Recommended default for the k=1e-2 case

- `HydroMechTopLoadRampTime = 0.001 s`
- `HydroMechFreeSurfaceDrainageStartTime = 0.001 s`
- `SoilDampingCoef = 0.02`
- `DtFixed = 1e-7 s`

The early transient is not fully eliminated. The tests suggest that simply increasing damping is not a good correction path; improvements should focus on the load/drainage transition, output alignment, or a more controlled initial excess-pore-pressure state.
