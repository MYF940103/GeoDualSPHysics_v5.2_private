# Self-weight Scenario 2: direct hydraulic-head Darcy diagnostic

Date: 2026-07-05

## Purpose

Test whether the late bottom EPWP platform is mainly a numerical cancellation artifact from evaluating the Darcy term as two large components:

```text
lapw / (rho_w g) + lapz
```

Instead, the diagnostic evaluates the same quantity directly in hydraulic-head difference form:

```text
((p_i - p_j) / (rho_w g) + dz)
```

Temporary source change:

- Compression term unchanged.
- Boundary head-Neumann value unchanged.
- Darcy term algebraically rewritten to a direct head-difference form.
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
| 1.30 | 0.529268 | 0.352400 |

Drop ratio over the window:

- SPH drop: 0.005492 kPa
- Theory drop: 0.098618 kPa
- SPH/theory drop ratio: 0.056

## Conclusion

The direct hydraulic-head form does not remove the late-time plateau. Therefore the platform is not primarily caused by floating-point cancellation between the separately accumulated `lapw` and `lapz` terms.

This leaves the coupled storage/volumetric-strain balance as the stronger suspect: the Darcy drainage that should remain at late time is being almost completely cancelled by a persistent compression source, regardless of whether the Darcy term is written in pressure-plus-gravity form or direct head-difference form.
