# Cryer Stage1 dp002/layer short-test conclusions

Date: 2026-06-18

This temporary test was removed after recording the conclusions.

Stable settings used:

- `tmax=0.006 s`
- `DtFixed=1e-6`
- `SoilDampingCoef=0.02`
- `HydroMechDrainage=0`
- `q0=10000 Pa`
- `setfrdrawmode auto="true"`

Results:

- `dp003_l1`: center `0.3144 q0`, core `r<=0.006` mean `0.4741 q0`, surface mean `1.6636 q0`, loaded particles `3630`.
- `dp002_l1`: center `0.3936 q0`, core `r<=0.006` mean `0.6202 q0`, surface mean `1.7546 q0`, loaded particles `8045`.
- `dp002_l3`: center `0.4694 q0`, core `r<=0.006` mean `0.7198 q0`, surface mean `0.5704 q0`, loaded particles `22225`.

Conclusions:

- Refining from `dp=0.003` to `dp=0.002` improved the short-time center/core pore-pressure response, but the center remained far below the ideal undrained value `p/q0=1`.
- The temporary three-layer load improved the center/core value, but it depressed the surface response and changed the near-surface load transfer. It was therefore removed and the code was restored to single-layer area-normalized `SphereNormal` loading.
- Larger trial time steps `5e-6` and `1e-5` caused more than 10% particle exclusion in `dp003_l1`; these outputs were rejected.
