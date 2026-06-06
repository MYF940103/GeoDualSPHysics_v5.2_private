# u-pw Retrogressive Slope Hydrostatic Initialization Test

This case adapts `examples/Elastoplastic_basic/14_RetrogressiveSlopeFailure`
to the u-pw hydromechanical formulation for the 5 m retrogressive slope
geometry from the main u-pw reference.

## Purpose

The current setup is a short CPU diagnostic for:

- hydrostatic pore-pressure initialization with `HydroMechInitMode=FreeSurface`;
- drained free-surface enforcement during the run;
- verification that particles classified by `ComputeFreeSurfaceTracking()` as
  `FSType=2/3` are treated as drained free-surface particles.

## Variants

- `CaseRetroSlope_u_pw_init_upward_Def.xml`
  historical name from the earlier upward-normal comparison.
- `CaseRetroSlope_u_pw_init_allfs_Def.xml`
  historical name from the earlier all-free-surface comparison.

Both files now use the unified drainage rule: all particles classified by
`ComputeFreeSurfaceTracking()` as `FSType=2/3` are drained. The q0 top-load
selector in the solver remains upward-normal based because it represents a top
surcharge, not a pore-pressure drainage boundary.

## Key Parameters

- Geometry: 5 m high, 45 degree slope, 25 m base length, 20 m top length.
- `dp = 0.1 m`, Wendland kernel, `h/dp = 1.5`.
- Mixture density `rho = 2150 kg/m3`.
- `E = 25 MPa`, `nu = 0.3`.
- `rho_w = 1000 kg/m3`, `n = 0.4`, `Kw = 0.2 GPa`, `k = 1e-8 m/s`.
- `phi = phi_r = 0`, `cp = 15.1 kPa`, `cr = 1.5 kPa`.

## Run

Run one variant:

```bat
xCaseRetroSlope_u_pw_init_win64_CPU.bat upward 0.02 0.01
xCaseRetroSlope_u_pw_init_win64_CPU.bat allfs 0.02 0.01
```

Run both legacy-named variants and compare:

```bat
xRunRetroSlope_u_pw_hydrostatic_compare_win64_CPU.bat 0.02 0.01
```

The diagnostic CSV files are written to `support/`.

## Initial Diagnostic Result

For the short `tmax=0.02 s` comparison, both variants selected the same 298
free-surface particles. All selected free-surface particles kept `pw=0`, and
the initial hydrostatic residual was essentially roundoff level:

- `hydro_rmse = 1.49e-3 Pa`
- `hydro_max_abs = 4.29e-3 Pa`

The legacy upward and all-free-surface variants were identical for `FSType`,
`porepress`, and `porepress0` in this initial slope geometry.
