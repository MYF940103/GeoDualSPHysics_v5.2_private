# Cryer ramp/drainage timing sweep, k=1e-5

Date: 2026-06-24

Purpose: test whether a finite load ramp can improve the low center-pore-pressure peak observed in the one-stage drained Cryer validation. The analytical time origin is shifted to the end of the load ramp, so `Tv=0` is the moment when the target load `q0` is reached. Two drainage timings were compared:

- `closed`: drainage is closed during ramp; `HydroMechDrainageStartTime = HydroMechTopLoadRampTime`.
- `open`: drainage is open during ramp; `HydroMechDrainageStartTime = 0`, but plotting still uses `CRYER_TL = HydroMechTopLoadRampTime`.

Base parameters:

- `dp=0.0025 m`
- `HydraulicConductivity=1e-5 m/s`
- `nu=0.3`
- `q0=10000 Pa`
- `SoilDampingCoef=0.02`
- `HydroMechTopLoadMode=3` (`FlexibleConfinement`)
- postprocess center sample radius: `r <= 1 dp`
- comparison window: `0.001 <= Tv <= 0.065`

Main results:

| Case | Peak SPH p/p0 | Analytical peak p/p0 | SPH peak Tv | Max speed (m/s) | Early max step |
|---|---:|---:|---:|---:|---:|
| open ramp=0 | 1.215952 | 1.249008 | 0.049000 | 0.039921 | 0.108969 |
| closed ramp=0.0025s | 1.215970 | 1.249021 | 0.049256 | 0.017124 | 0.024464 |
| closed ramp=0.005s | 1.215978 | 1.249021 | 0.049511 | 0.026541 | 0.015021 |
| closed ramp=0.01s | 1.215966 | 1.249009 | 0.049022 | 0.036346 | 0.027726 |
| closed ramp=0.02s | 1.215982 | 1.249011 | 0.049044 | 0.034714 | 0.036110 |
| open ramp=0.005s | 1.215744 | 1.249021 | 0.046511 | 0.002354 | 0.008903 |
| open ramp=0.01s | 1.215087 | 1.249009 | 0.044022 | 0.001924 | 0.006755 |
| open ramp=0.02s | 1.212436 | 1.249011 | 0.039044 | 0.001420 | 0.006007 |

Conclusions:

- Finite ramp does not recover the missing center pressure peak. In the closed-drainage ramp cases, the peak stays essentially fixed at `p/p0 = 1.216`, while the analytical peak is about `1.249`.
- Closing drainage during ramp reduces velocity only for short ramp. The best closed case is `ramp=0.0025s`, which lowers max speed from about `0.0399` to `0.0171 m/s` without changing peak height.
- Opening drainage during ramp strongly suppresses early velocity and stepwise oscillation, but it slightly reduces the peak and shifts the SPH peak earlier. Long open ramp (`0.02s`) clearly smears the peak.
- Therefore the peak deficit is unlikely to be caused mainly by the instantaneous-load transient. Ramp time can be used as a numerical damping/stabilization control, but it is not the main route to improving peak accuracy.

Recommended use:

- If the priority is to keep the formal Cryer comparison closest to the existing one-stage setup, keep `ramp=0`.
- If the priority is a quieter early response for visualization or diagnostic runs, use `ramp=0.0025s` with drainage closed during ramp, or `ramp=0.005s` with drainage open during ramp. The latter is smoother but slightly lowers the peak.

Generated outputs:

- Raw sweep directory: `refinement/ramp_drain_timing_20260624`
- Main history plot: `figures/cryer_k1e5_ramp_drain_timing_tv001_0065.png`
- Metric plot: `figures/cryer_k1e5_ramp_drain_timing_metrics.png`
- Metrics table: `figures/cryer_k1e5_ramp_drain_timing_metrics.csv`
