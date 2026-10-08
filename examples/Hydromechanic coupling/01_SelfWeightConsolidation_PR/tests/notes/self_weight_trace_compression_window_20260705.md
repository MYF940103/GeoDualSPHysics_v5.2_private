# Self-weight Scenario 2 trace-compression diagnostic

Date: 2026-07-05

## Purpose

Test whether the late-time bottom EPWP platform is caused by the pore-pressure compression source using a velocity-divergence path that is inconsistent with the skeleton stress-rate velocity gradient.

## Diagnostic change

The pore-pressure-rate compression source was moved out of the pore-rate neighbor loop and recomputed from the trace of the skeleton velocity-gradient tensor after the same optional `SoilStressRateGradCorr` correction used by the stress-rate update.

Files modified temporarily:

- `source/JSphCpu.cpp`
- `source/JSphGpu_ker.cu`

The Darcy/head-Neumann part was left unchanged.

## Sign check

Using `+trace(grad v_s)` caused immediate instability and particle exclusion:

- after `Part_0001`, 998 fluid particles were excluded
- the run was stopped immediately

This confirms that the code's current stress/strain sign convention requires the compression source to use `-trace(grad v_s)` if this route is used.

## Stable short-window test

Case:

- XML: `tests/configs/CaseSWSc2_TraceComp_Tv120_130_Def.xml`
- BAT: `tests/xCaseSWSc2_TraceComp_Tv120_130_win64_GPU.bat`
- Restart: `tests/outputs/CaseSWSc2_HeadN_Tv2_from_p0056_GPU_out/data/Part_0240`
- Window: `Tv = 1.20 -> 1.30`
- Solver: GPU release
- `SlipMode = 2`
- `MDBCCorrector = 1`
- fixed `Dt = 1e-6`

Result with `-trace(grad v_s)`:

| Quantity | Value |
|---|---:|
| Initial SPH bottom EPWP | 0.53476 kPa |
| Final SPH bottom EPWP | 0.52867 kPa |
| SPH drop | 0.00609 kPa |
| Theory drop | 0.09862 kPa |
| SPH drop / theory drop | 0.0618 |
| Excluded particles | 0 |

## Conclusion

Recomputing the compression source from the stress-rate velocity-gradient trace does not remove the late-time platform. The slope is essentially the same as the retained HeadN/MLS short-window behavior.

Therefore, the platform is not primarily caused by the compression source using a different correction-matrix path than the stress-rate update. The temporary code must not be retained.
