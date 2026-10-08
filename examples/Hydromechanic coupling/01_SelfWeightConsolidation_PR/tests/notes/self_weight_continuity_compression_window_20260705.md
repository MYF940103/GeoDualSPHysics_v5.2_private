# Self-weight Scenario 2: continuity-operator compression diagnostic

Date: 2026-07-05

## Purpose

Test whether the late bottom EPWP platform comes from using a pore-pressure-rate compression operator that is inconsistent with the solver's continuity/density derivative operator.

Temporary source change:

- Darcy/head-Neumann seepage terms were left unchanged.
- The pore-pressure-rate compression term was changed from the `porecorr` corrected-gradient divergence to the same pair contribution used by the density derivative/continuity equation.
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
| 1.30 | 0.528656 | 0.352400 |

Drop ratio over the window:

- SPH drop: 0.006103 kPa
- Theory drop: 0.098618 kPa
- SPH/theory drop ratio: 0.062

## Conclusion

Replacing the compression source with the continuity-equation pair operator does not remove the late plateau. It is essentially as slow as the head-Neumann/MLS baseline. Therefore the platform is not simply caused by the pore-rate compression term using a different gradient operator from density continuity.

The result strengthens the conclusion that the late residual is a coupled bottom-support/storage balance issue, not a single local gradient-form error.
