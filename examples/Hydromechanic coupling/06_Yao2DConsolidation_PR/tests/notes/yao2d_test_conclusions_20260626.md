# Yao 2025 2D Consolidation Short-Test Conclusions

Date: 2026-06-26

## Kept Result

The only retained test output is:

- `CaseYao2DConsolidation_PR_gpu02s_dp01_damp002_geomfix_slip1_out`

This output is the accepted short GPU validation state for the current Yao 2D consolidation setup.

## Accepted Geometry And Runtime State

- Total particles: 21945
- Boundary particles: 1644
- Fluid particles: 20301
- Non-zero boundary normals: 1227 / 1644
- Boundary normal size range: 0.100000 to 0.424264
- Periodic boundary: None
- Boundary model: mDBC
- Slip mode: `SlipMode=1`
- Particle spacing: `Dp=0.1 m`
- Soil damping coefficient: `0.02`
- Test duration: `0.2 s`
- Output interval: `0.02 s`

The retained geometry uses the current formal XML boundary boxes:

- Bottom boundary: `z = -4*Dp`, thickness `3*Dp`
- Left boundary: thickness `3*Dp`
- Right boundary: starts at `xmax + Dp`, thickness `3*Dp`

This setup gives symmetric pore-pressure mapping on the left and right mDBC boundaries.

## Boundary Pore-Pressure Symmetry Check

The retained result was checked from:

- `particles/PartBound_0010.vtk`
- field: `PorePress`

Left/right mirror-pair comparison used mirrored coordinates:

- left particle: `(x, z)`
- right mirror target: `(-x, z)`

Result:

- Left effective side-boundary particles: 396
- Right effective side-boundary particles: 396
- Missing mirror pairs: 0
- Maximum left-right pore-pressure difference: `0.0015869140625 Pa`
- Mean left-right pore-pressure difference: `0.000274060952543008 Pa`

The remaining difference is at output/float precision scale and is acceptable for the short-test symmetry check.

Side-boundary pore-pressure summary at `PartBound_0010.vtk`:

- Left: min `0 Pa`, max `1510.23095703125 Pa`, mean `882.582705584439 Pa`, zero-count `99`
- Right: min `0 Pa`, max `1510.23034667969 Pa`, mean `882.582473408092 Pa`, zero-count `99`

Bottom boundary summary:

- Bottom particles checked: 796
- Bottom pore pressure: min `0 Pa`, max `2111.24829101563 Pa`, mean `1302.2280207495 Pa`, zero-count `199`

The zero pore-pressure particles are the outer boundary layers outside the local fluid-support region. They are symmetric and should not be interpreted as a drainage or mapping failure by themselves.

## Rejected Test Outputs

The following output families were removed because they were old, duplicate, or invalid diagnostics:

- Earlier `gpu2s` and `gpu02s` outputs before the accepted geometry state
- `refboundary_slip1` output, because the boundary geometry became disconnected
- `slip1` / `extrap` / `regencheck` duplicates
- The `bad2045` backup output
- Temporary figures, old logs, pid/stdout/stderr files, and Python cache files

The rejected `2045 boundary / 19900 fluid` geometry is not acceptable, even though its particle count looked plausible, because its boundary pore pressure was strongly asymmetric:

- Left mean pore pressure: approximately `73.48 Pa`
- Right mean pore pressure: approximately `734.04 Pa`
- Maximum mirror-pair difference: approximately `1334.91 Pa`

## Required Check Before Future Use

After any future Yao 2D run, the result should not be accepted until both checks pass:

1. GenCase / Run logs confirm the expected particle counts and mDBC settings.
2. `PartBound` pore pressure passes a left-right mirror check on boundary particles.

For the current accepted short-test setup, the target state is:

- `bound=1644`
- `fluid=20301`
- left/right boundary mirror `PorePress` max difference near `1e-3 Pa`

