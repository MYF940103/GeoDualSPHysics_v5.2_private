# Scenario2 raw pore-rate gradient test, 2026-06-28

## Purpose

Test whether the slow late-time pore-pressure dissipation is caused by using the gradient correction matrix in the pore-pressure-rate terms.

## Code change under test

The diagnostic patch changes only the pore-pressure-rate terms:

- compression term: `kwn*(-divv)`
- seepage terms: `lapw` and `lapz`

These now use raw kernel gradients instead of `corrmat * gradW`.

Files changed:

- `src/source/JSphCpu.cpp`
- `src/source/JSphGpu_ker.cu`

Other terms still use their existing paths. Momentum, stress update, mDBC, free-surface drainage, top-strip pore-pressure handling, and Shepard settings were not changed for this diagnostic.

## Build

Both builds completed successfully:

- CPU Debug: `DualSPHysics5ReCpu_vs2022.sln`, `DebugCPU|x64`
- GPU Release: `DualSPHysics5Re.sln`, `Release|x64`

## Test run

Created short-name test files to avoid GenCase path-length failure:

- `tests/configs/CaseSWSc2_rawpg_Tv010_Def.xml`
- `tests/xCaseSWSc2_rawpg_Tv010_win64_GPU.bat`

The attempted longer name failed in GenCase when writing `[CaseName]_hdp_Actual.vtk`; those failed logs and files were removed.

The raw-gradient test was started with `DtFixed=1e-6`, inherited Stage1 `Part_0060`, and used:

- `SlipMode=3`
- `-mdbc_freeslip`
- `MDBCCorrector=0`
- `HydroMechDrainage=1`
- `PoreShepardRegularization=0`

Because a full run to `Tv=0.10` would take roughly 45 minutes, the run was intentionally stopped after `Part_0010`, corresponding to `Tv=0.05`. Post-processing was run on the available `Part_0000` to `Part_0010`.

Outputs:

- `tests/outputs/CaseSWSc2_rawpg_Tv010_out`
- `tests/figures/CaseSWSc2_rawpg_Tv010_cutTv005/scenario2_pore_pressure_profiles.png`
- `tests/figures/CaseSWSc2_rawpg_Tv010_cutTv005/scenario2_bottom_dissipation.csv`
- `tests/figures/CaseSWSc2_rawpg_Tv010_cutTv005/scenario2_target_summary.csv`
- `tests/figures/CaseSWSc2_rawpg_Tv010_cutTv005/scenario2_profiles_by_tv.csv`

## Early-time comparison

Compared against the previous full `freeslip + MDBCCorrector=0` baseline.

| Tv | theory kPa | baseline kPa | raw-gradient kPa | raw - baseline kPa |
| ---: | ---: | ---: | ---: | ---: |
| 0.005 | 9.888994 | 9.948401 | 9.933225 | -0.015176 |
| 0.010 | 9.534105 | 9.540443 | 9.546525 | +0.006082 |
| 0.025 | 8.829615 | 8.883366 | 8.883282 | -0.000084 |
| 0.050 | 8.035499 | 8.102928 | 8.102968 | +0.000040 |

At `Tv=0.05`, the raw-gradient result is essentially identical to the baseline. The bottom excess pressure error remains about `+0.067 kPa` relative to theory.

## Interpretation

Removing the correction matrix from the pore-pressure-rate terms does not improve the early dissipation trend up to `Tv=0.05`.

This short run cannot fully prove the late-time behavior at `Tv=0.5-1.0`, but the current evidence suggests that the correction matrix is not the primary source of the early discrepancy. If the late-time lag remains the main target, the next stronger diagnostic should measure or output the pore-rate decomposition:

- compression contribution `kwn*(-divv)`
- seepage contribution `kwn*2*khyd*lapw/(rho_w*g)`
- gravity-head contribution `kwn*2*khyd*lapz`

That would directly show whether late-time lag comes from residual volumetric-strain coupling rather than the hydraulic diffusion operator.

## Cleanup and final state

After reviewing the result, the code was restored to the corrected-gradient form for the pore-pressure-rate terms on both CPU and GPU paths.

The temporary raw-gradient test artifacts were removed to keep `tests` focused:

- `tests/configs/CaseSWSc2_rawpg_Tv010_Def.xml`
- `tests/xCaseSWSc2_rawpg_Tv010_win64_GPU.bat`
- `tests/outputs/CaseSWSc2_rawpg_Tv010_out`
- `tests/figures/CaseSWSc2_rawpg_Tv010_cutTv005`
- `tests/run_scenario2_rawpg_Tv010_gpu.log`

Only this conclusion note is retained. The raw-gradient variant should not be used as a baseline.
