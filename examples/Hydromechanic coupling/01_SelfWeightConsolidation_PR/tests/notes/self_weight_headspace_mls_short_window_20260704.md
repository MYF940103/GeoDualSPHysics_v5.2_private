# Self-weight Scenario 2 head-space MLS Neumann short-window test

Purpose: test whether a stricter head-space mDBC Neumann treatment removes the late bottom excess pore-pressure plateau in Scenario 2.

Code-side changes tested:

- mDBC pore-pressure extrapolation was changed from excess-pore-pressure (`q = pw - pw0`) MLS to hydraulic-head MLS when gravity is active.
- Boundary pore pressure is reconstructed as `pw_b = rho_w g (h_MLS - zeta_b)`.
- The pore-pressure-rate Darcy term uses hydraulic-head differences when gravity is active, while preserving the pressure-only fallback for no-gravity cases.
- CPU and GPU mDBC pore-pressure paths and pore-pressure-rate paths were synchronized.
- `Eta2` was intentionally left unchanged for this test.

Test case:

- Config: `tests/configs/CaseSWSc2_HeadMLS_Tv120_130_Def.xml`
- Runner: `tests/xCaseSWSc2_HeadMLS_Tv120_130_win64_GPU.bat`
- Restart: `tests/outputs/CaseSWSc2_HeadN_Tv2_from_p0056_GPU_out/data/Part_0240`
- Window: `Tv = 1.20` to `Tv = 1.30`
- Slip mode: `SlipMode = 2`
- mDBC corrector: `MDBCCorrector = 1`
- Shepard regularization: disabled in Scenario 2

Result:

| Case | Tv window | SPH bottom EPWP drop | Theory drop | Slope ratio |
|---|---:|---:|---:|---:|
| Head-space MLS Neumann | 1.20 -> 1.30 | -0.005883 kPa | -0.098618 kPa | 0.060 |
| Previous head-N / pairwise reference | 1.20 -> 1.30 | -0.005459 kPa | -0.098618 kPa | 0.055 |

Conclusion:

The head-space MLS Neumann implementation is more physically consistent as a pore-pressure boundary reconstruction, but it does not remove the late-time bottom-pressure plateau in this case. The plateau remains essentially unchanged over the platform window. The next useful test should not repeat boundary pore-pressure reconstruction variants; it should diagnose the Laplacian/operator balance itself, especially a fluid-neighbor-dominated one-sided Laplacian with mDBC/MLS used only as missing-support consistency correction.

Cleanup:

- Temporary source changes for this diagnostic were reverted after the follow-up one-sided Darcy diagnostic.
- Temporary short-window config, BAT, figures, and output directory were removed after recording the numerical conclusion.
