# Self-weight Scenario 2 no-compression pore-rate diagnostic

Date: 2026-07-05

## Purpose

Test whether the late-time bottom EPWP platform is caused by cancellation between the volumetric-compression source term and the Darcy/seepage term in the pore-pressure-rate equation.

## Temporary code change

For this diagnostic only, the pore-pressure-rate compression contribution was disabled in both CPU and GPU paths:

- `source/JSphCpu.cpp`
- `source/JSphGpu_ker.cu`

The Darcy/seepage term and boundary pore-pressure participation were otherwise kept.

## Case

- Case: `CaseSWSc2_NoCompression_Tv120_130`
- Window: `Tv = 1.20 -> 1.30`
- Restart: `CaseSWSc2_HeadN_Tv2_from_p0056_GPU_out/data/Part_0240`
- Solver: GPU release
- Time step: fixed `1e-6`
- SlipMode: `2`
- MDBCCorrector: `1`

## Result

The solver finished normally with no excluded particles. Bottom EPWP changed as follows:

| Quantity | Value |
|---|---:|
| Initial Tv | 1.20 |
| Final Tv | 1.30 |
| Initial SPH bottom EPWP | 0.53476 kPa |
| Final SPH bottom EPWP | -0.01994 kPa |
| Initial Terzaghi bottom EPWP | 0.45102 kPa |
| Final Terzaghi bottom EPWP | 0.35240 kPa |
| SPH drop / theory drop | 5.62 |
| SPH drop / theory drop after first output interval | 0.29 |

The first output interval drains almost all remaining bottom EPWP, after which the curve stays near a small negative value.

## Conclusion

The late platform is strongly tied to cancellation between the compression source term and Darcy/seepage term in the complete coupled pore-rate equation. However, simply removing the compression term is not physically acceptable: it over-drains immediately and produces negative excess pore pressure.

This diagnostic should not be kept in production source. The next useful direction is not boundary exclusion or source-term removal, but a more local audit of why the compression source remains too strong relative to Darcy drainage at late time, especially near the bottom support.
