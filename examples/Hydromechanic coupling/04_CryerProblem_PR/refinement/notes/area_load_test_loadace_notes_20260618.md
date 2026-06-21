# HydroMechLoadAce Stage1 diagnostic

Date: 2026-06-18

Stage2 was not continued. This diagnostic only checks the Stage1 external load acceleration written to VTK.

## Output files

- Particle VTK for ParaView:
  `out_loadace/stage1/particles/PartFluid_0001.vtk`
- Numeric check:
  `analysis_loadace/loadace_check.json`

## Result

- Total particles: 22483
- Free-surface particles (`FSType=2/3`): 3630
- Particles with non-zero `HydroMechLoadAce`: 3630
- Loaded free-surface particles: 3630
- Loaded non-surface particles: 0
- Free-surface particles not loaded: 0

The load direction is inward radial for the loaded particles:

- `dot(HydroMechLoadAce, radius) / (|HydroMechLoadAce| |radius|)` mean: -1.0
- min/max: approximately -1.0 / -1.0

The load magnitude at `PartFluid_0001` is about `305.27 m/s2`. This is expected for the short diagnostic output because the Stage1 load is still in the ramp period (`t ~= 0.001`, ramp time `0.005`), so it is about 20% of the full area-load acceleration (`1526.37 m/s2` from the solver diagnostic).

The normalized resultant load acceleration is about `2.75e-4`, computed as
`|sum(HydroMechLoadAce_i)| / (N_loaded * mean(|HydroMechLoadAce_i|))`.
This indicates that the loaded surface acceleration field is nearly balanced as a whole.

## ParaView check

Open `out_loadace/stage1/particles/PartFluid_0001.vtk`, color or glyph by `HydroMechLoadAce`.
The vector should appear only on the sphere surface and point toward the sphere center.
