# Shepard Neighbor A/B Comparison

Date: 2026-06-03

Purpose: compare Stage 1 pore-pressure Shepard regularization using:

- `with_bound_neighbors`: fluid/soil particles plus mDBC boundary particles in the Shepard support.
- `soil_only_neighbors`: fluid/soil particles only in the Shepard support.

Both runs used the same Stage 1 XML:

- `WaterTableMode=None`
- `HydraulicConductivity=0`
- `PoreShepardRegularization=1`
- `PoreShepardInterval=40`
- `SoilDampingCoef=0.04`
- `Visco=0.4`
- `TimeMax=0.20 s`

The source code was restored to the default `with_bound_neighbors` behaviour after the diagnostic run.

## Final Stage 1 Metrics

Metrics are from `PartFluid_0040.vtk` at `t=0.20 s`.

| case | bottom excess error [kPa] | bottom sigma_zz error [Pa] | bottom 0-0.1 m pore RMS [Pa] | bottom 0-0.1 m sigma RMS [Pa] | core pore RMS [Pa] | core sigma RMS [Pa] | max speed [m/s] |
|---|---:|---:|---:|---:|---:|---:|---:|
| with boundary neighbors | -0.581 | -699.26 | 246.11 | 297.34 | 50.58 | 0.583 | 3.33e-5 |
| soil-only neighbors | -0.581 | -700.66 | 246.96 | 298.65 | 50.68 | 0.599 | 3.34e-5 |

## Interpretation

Excluding boundary particles from the Shepard support did not improve the bottom boundary layer. The soil-only result is almost identical to the default case and is slightly worse for the bottom effective stress and core RMS metrics.

This suggests the bottom effective-stress artifact is not caused primarily by boundary particles entering the Shepard interpolation. The remaining likely source is the coupled fixed-bottom mDBC/effective-stress evolution path, while Shepard mainly suppresses the odd-even pore-pressure mode.

## Stored Results

- `ab_shepard_with_bound/`
- `ab_shepard_soil_only/`
- `ab_shepard_neighbor_comparison.csv`
