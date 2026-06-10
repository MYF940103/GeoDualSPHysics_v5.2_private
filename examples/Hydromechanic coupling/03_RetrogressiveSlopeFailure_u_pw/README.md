# u-pw Retrogressive Slope Failure

This case prepares the 5 m retrogressive slope benchmark from the main u-pw reference as a two-stage workflow for CPU/GPU comparison.

## Reference Setup

- Geometry: 5 m high slope, 45 degree inclination, 25 m base length, 20 m top length.
- Resolution: `dp = 0.1 m`, Wendland kernel, `h/dp = 1.5`.
- Mixture density: `rho = 2150 kg/m3`.
- Elastic parameters: `E = 25 MPa`, `nu = 0.3`.
- Pore-water parameters: `rho_w = 1000 kg/m3`, `n = 0.4`, `Kw = 0.2 GPa`, `k = 1e-8 m/s`.
- Strength: `phi = phi_r = 0`, `cp = 25 kPa` in the current stable setup, `cr = 1.5 kPa`.
- Failure trigger: `eta = 5`, `SoilTriggerFos = 1.65`.
- Time stepping: fixed `dt = 1e-6 s` in the formal XML files.

The strict reference uses a K0 stress initialization followed by gravity loading and then inherits the resulting effective stresses and pore pressures into the failure simulation. This case uses coupled u-pw gravity relaxation in the prestress stage: hydrostatic pore pressure is initialized from the tracked free surface, free-surface particles are drained, and the resulting stress and pore-pressure fields are inherited by the failure stage.

## Files

- `CaseRetroSlope_u_pw_prestress_Def.xml`
  Coupled u-pw gravity relaxation. `HydroMechInitMode=FreeSurface` initializes hydrostatic pore pressure, fixed `dt = 1e-6 s` is used, peak strength is used, softening parameters are omitted, and mDBC extra data is saved for restart.

- `CaseRetroSlope_u_pw_failure_Def.xml`
  u-pw failure stage. Restarts from the coupled prestress PART with `HydroMechInitMode=None`, directly inherits `Sigma`, `PorePress` and `PorePress0`, drains `FSType=2/3` free-surface particles, enables pore-pressure Shepard regularization every 40 steps, and enables cohesion softening.

## Run

CPU two-stage run:

```bat
xRunRetroSlope_u_pw_two_stage_win64_CPU.bat
```

GPU two-stage run:

```bat
xRunRetroSlope_u_pw_two_stage_win64_GPU.bat
```

Individual stages:

```bat
xCaseRetroSlope_u_pw_prestress_win64_CPU.bat
xCaseRetroSlope_u_pw_prestress_win64_GPU.bat
xCaseRetroSlope_u_pw_failure_win64_CPU.bat
xCaseRetroSlope_u_pw_failure_win64_GPU.bat
```

Both prestress batch files write to the same shared restart folder:

```text
CaseRetroSlope_u_pw_prestress_out\data
```

The failure batch files accept optional arguments:

```bat
xCaseRetroSlope_u_pw_failure_win64_GPU.bat [-force] [partbegin] [tmax] [tout]
```

Default restart is `Part_0050.bi4` from `CaseRetroSlope_u_pw_prestress_out\data`.

For quick smoke tests, override `tmax` and `tout`, for example:

```bat
xCaseRetroSlope_u_pw_prestress_win64_CPU.bat -force 0.02 0.01
xCaseRetroSlope_u_pw_failure_win64_GPU.bat -force 1 0.02 0.01
```

## Notes

- GPU and CPU failure runs inherit the same shared prestress restart folder.
- Running a prestress batch with `-force` deletes and recreates the shared prestress folder, so run only the CPU or GPU prestress stage you want to use as the inherited state.
- The coupled prestress default is 5 s, so the default restart file is `Part_0050.bi4` because `TimeOut=0.1 s`.
- If the coupled prestress kinetic energy has not settled, extend the prestress stage before comparing failure results.
