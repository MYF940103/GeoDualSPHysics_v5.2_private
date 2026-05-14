# L3 Initial-Pressure Terzaghi Diffusion Gate

This case separates the PR pore-pressure diffusion and hydraulic boundary
handling from the reduced L2 `AccInput` mechanical loading route.

Setup:

- `H=1.0 m`, `width=0.1 m`, `Dp=0.01 m`
- `E=2e6 Pa`, `nu=0.3`, `Kw=2e8 Pa`, `n=0.3`, `k=1e-3 m/s`
- `SoilConstitutiveModel=0`
- `PorePressureInit=3`, `PorePressureAnalyticalProfile=3`
- uniform initial excess pore pressure `10 kPa`, corresponding to `|q0|`
- top drained from initialization, bottom no-flux
- `PorePressureFeedback=0`
- no `AccInput`

This is not a mechanical surface-load reproduction.  It is an analytical
diffusion gate for the PR update and hydraulic boundary corrections.
