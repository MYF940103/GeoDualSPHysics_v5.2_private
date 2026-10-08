# Self-weight scenario 2: solid-acceleration pore-rate diagnostic

Date: 2026-07-31

## Purpose

Test whether the missing u-pw solid-acceleration divergence contribution is the main source of the late-time excess pore-pressure plateau.

The diagnostic added a temporary PR-only source term:

```text
dpw/dt += (Kw/n) * coef * (k/g) * div(a_s)
```

with `coef=1`. The code path was compiled for CPU Debug and GPU Release, then removed after the test because it did not improve the late-time behavior.

## Case

- Base restart: `CaseSWSc2_MLSDirect_Tv2_from_p0056_GPU_out/data`
- Window: `PartBegin=300`, `TimeMax=5.64775714285 s`, approximately `Tv=1.50` to `1.55`
- Diagnostic config: `CaseSWSc2_PR_Ac1w_p300_Def.xml`
- Output folder used during the run: `tests/outputs/CaseSWSc2_PR_Ac1w_p300_out`
- Comparison CSV: `tests/figures/solid_accel_term_20260731/bottom_epwp_accelcoef1_vs_baseline.csv`

## Result

Bottom excess pore-pressure history, kPa:

```text
Tv=1.500  baseline=0.574106  accel=0.574106  delta= 0.000000
Tv=1.505  baseline=0.574010  accel=0.574018  delta= 0.000008
Tv=1.510  baseline=0.573901  accel=0.573920  delta= 0.000019
Tv=1.515  baseline=0.573778  accel=0.573807  delta= 0.000029
Tv=1.520  baseline=0.573646  accel=0.573682  delta= 0.000036
Tv=1.525  baseline=0.573508  accel=0.573548  delta= 0.000040
Tv=1.530  baseline=0.573369  accel=0.573407  delta= 0.000038
Tv=1.535  baseline=0.573231  accel=0.573262  delta= 0.000031
Tv=1.540  baseline=0.573102  accel=0.573120  delta= 0.000018
Tv=1.545  baseline=0.572988  accel=0.572997  delta= 0.000009
Tv=1.550  baseline=0.572901  accel=0.572896  delta=-0.000006
```

Late-window slopes:

```text
bottom band: baseline=-0.024842685 kPa/Tv, accel=-0.025220762 kPa/Tv
domain mean: baseline=-0.012155330 kPa/Tv, accel=-0.012398748 kPa/Tv
```

## Conclusion

The solid-acceleration divergence term has a negligible effect on the late plateau. It is not the root cause of the slow dissipation.

Together with earlier tests (`PoreCompressionGradCorr=0`, `PoreCompressionSourceMode=DensityRate`, direct head Darcy, q-Darcy, no Eta2, boundary-compression removal, and full mDBC ghost velocity), the remaining consistent explanation is that the current explicit PR update relies on cancellation between a very stiff compression source and a very stiff Darcy/seepage term. In the late stage, the physical pressure is small enough that residual mechanical/particle-scale oscillations in the compression source become comparable to the true diffusive decay, creating a numerical floor.

For this case, the raw PR diffusion stiffness is controlled by `(Kw/n) k / (rho_w g) = 67.96 m^2/s`, while the elastic Terzaghi reference coefficient is `k M / (rho_w g) = 0.27445 m^2/s`, with `M=K+4G/3=2.6923 MPa`. The explicit PR update therefore asks the compression source to cancel a term about `247.6x` larger than the physical drained consolidation coefficient. The Lian flexible-strip parameters show the same pattern, but less severe: `(Kw/n) k / (rho_w g) = 254.93 m^2/s`, `k M/(rho_w g) = 3.0217 m^2/s`, ratio `84.4x`.
