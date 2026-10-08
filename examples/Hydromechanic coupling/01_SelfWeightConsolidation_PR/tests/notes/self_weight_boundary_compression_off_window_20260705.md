# Self-weight Scenario 2: boundary compression-off window diagnostic

Date: 2026-07-05

## Purpose

Diagnose whether the late bottom EPWP plateau is mainly caused by the mDBC boundary-neighbor contribution to the pore-pressure-rate compression term.

Temporary source change:

- Keep mDBC boundary neighbours in the Darcy/head-Neumann seepage term.
- Remove only boundary-neighbour contributions from the volumetric compression term.
- CPU/GPU were changed consistently for this diagnostic and then restored.

Window:

- Restart: `CaseSWSc2_HeadN_Tv2_from_p0056_GPU_out/data/Part_0240`
- Tv window: 1.20 to 1.30
- GPU Release
- SlipMode = 2
- MDBCCorrector = 1
- Fixed Dt = 1e-6

## Result

Bottom excess pore pressure:

| Tv | SPH bottom EPWP (kPa) | Terzaghi theory (kPa) |
|---:|---:|---:|
| 1.20 | 0.534760 | 0.451018 |
| 1.30 | 0.515574 | 0.352400 |

Drop ratio over the window:

- SPH drop: 0.019185 kPa
- Theory drop: 0.098618 kPa
- SPH/theory drop ratio: 0.195

## Conclusion

Removing boundary-neighbour compression improves the platform slope compared with the fully plateaued case, but it is still far too slow and is not a physically acceptable final treatment. The test confirms that boundary compression contributes to the cancellation, but the late plateau is not solved by this isolated switch.

The next useful direction is not to permanently exclude boundary compression, but to inspect the coupled operator consistency: boundary Darcy support, boundary compression velocity, and missing-support correction should be treated in one consistent head/velocity framework.
