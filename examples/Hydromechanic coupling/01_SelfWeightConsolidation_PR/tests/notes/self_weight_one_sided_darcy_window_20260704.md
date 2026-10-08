# Self-weight Scenario 2 one-sided Darcy short-window diagnostic

Purpose: after the head-space MLS Neumann boundary test did not remove the late-time bottom EPWP plateau, test whether the plateau is caused by direct boundary-particle contribution in the Darcy Laplacian.

Diagnostic code tested:

- Keep mDBC pore pressure reconstructed in head space.
- Keep boundary particles participating in mDBC mechanics and in the volumetric compression term.
- For the Darcy seepage term only, use real fluid/soil neighbors as the dominant one-sided Laplacian.
- Boundary neighbors do not directly contribute a boundary pore-pressure value to the Darcy flux.
- Boundary neighbors only enter a missing-support weight correction, capped at 3.0, based on the ratio of full support weight to fluid-neighbor support weight.

Test case:

- Config: `tests/configs/CaseSWSc2_OneSided_Tv120_130_Def.xml`
- Runner: `tests/xCaseSWSc2_OneSided_Tv120_130_win64_GPU.bat`
- Restart: `tests/outputs/CaseSWSc2_HeadN_Tv2_from_p0056_GPU_out/data/Part_0240`
- Window: `Tv = 1.20` to `Tv = 1.30`
- Slip mode: `SlipMode = 2`
- mDBC corrector: `MDBCCorrector = 1`
- Shepard regularization: disabled in Scenario 2

Comparison over `Tv = 1.20 -> 1.30`:

| Case | SPH bottom EPWP drop | Theory drop | Slope ratio | Error at Tv=1.30 |
|---|---:|---:|---:|---:|
| Previous head-N / pairwise reference | -0.005459 kPa | -0.098618 kPa | 0.055 | +0.176900 kPa |
| Head-space MLS Neumann | -0.005883 kPa | -0.098618 kPa | 0.060 | +0.176477 kPa |
| One-sided Darcy missing-support diagnostic | -0.012090 kPa | -0.098618 kPa | 0.123 | +0.170269 kPa |

Conclusion:

The one-sided Darcy diagnostic slightly improves late-window dissipation, but it still leaves a severe plateau. The platform is therefore unlikely to be caused mainly by the detailed construction of the hydraulic Neumann boundary value or by direct boundary-particle pore-pressure diffusion. The stronger remaining suspect is the bottom mDBC mechanical support balance: the pore-pressure equation is being asked to dissipate while the bottom-row velocity/divergence and effective/total stress feedback are held in a small but persistent discrete equilibrium defect.

The one-sided Darcy code should remain temporary unless a later full diagnostic proves it is part of a better combined formulation. By itself it is not a sufficient fix.

Cleanup:

- Temporary source changes for the one-sided Darcy diagnostic were reverted.
- Temporary short-window config, BAT, figures, and output directory were removed after recording the numerical conclusion.
- CPU Debug and GPU Release executables were rebuilt after reverting the temporary source changes.
