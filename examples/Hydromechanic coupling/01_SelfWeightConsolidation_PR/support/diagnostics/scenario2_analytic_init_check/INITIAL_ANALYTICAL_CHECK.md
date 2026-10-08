# Scenario2 Analytical Initialization Check

Generated with `CaseSelfWeightConsolidation_Scenario2_Def.xml` using
`HydroMechInitMode=3` (`AnalyticalSelfWeight1D`) and `tmax=1e-6 s`.

The check reads `particles/PartFluid_0000.vtk` and compares the initialized
fields with the 1D self-weight analytical expressions used by
`support/postprocess_self_weight_consolidation.py`.

## All Fluid Particles

| quantity | SPH | theory |
| --- | ---: | ---: |
| bottom z | 0.005000 m | - |
| bottom excess pore pressure | 10.693858 kPa | 10.693858 kPa |
| bottom total pore pressure | 20.454809 kPa | 20.454808 kPa |
| bottom sigma_zz | -43.186741 Pa | -43.186735 Pa |

RMS excess pore pressure error: `5.373793 Pa`.
RMS total pore pressure error: `10.278788 Pa`.
RMS sigma_zz error: `0.000003 Pa`.

The all-particle pressure RMS is dominated by the drained top free-surface layer,
which is intentionally forced to zero pore pressure.

## Core Particles, Excluding Top Drained Layer

Using `z < 0.99 m`:

| quantity | SPH | theory |
| --- | ---: | ---: |
| bottom excess pore pressure | 10.693858 kPa | 10.693858 kPa |
| bottom total pore pressure | 20.454809 kPa | 20.454808 kPa |
| bottom sigma_zz | -43.186741 Pa | -43.186735 Pa |

RMS excess pore pressure error: `0.000539 Pa`.
RMS total pore pressure error: `0.000712 Pa`.
RMS sigma_zz error: `0.000003 Pa`.

Initial velocity and plasticity check: `max_speed=0`, `max_kplastic=0`.
