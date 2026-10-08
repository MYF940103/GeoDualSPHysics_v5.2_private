# Self-weight Scenario 2 fluid-neighbor pore-rate short-window diagnostic

Date: 2026-07-05

## Purpose

Test whether the late bottom excess-pore-pressure platform is mainly caused by
direct mDBC boundary-neighbor contributions in the u-pw pore-pressure-rate
equation. Earlier tests showed that changing only the Darcy boundary treatment
improved the late slope only slightly, while support diagnostics showed the
largest event-scale change in the boundary-neighbor compression contribution.

## Temporary code tested

In the pore-pressure-rate path, both CPU and GPU were temporarily changed so
that:

- compression and Darcy terms are accumulated only from real fluid/soil
  neighbors;
- mDBC boundary neighbors do not directly contribute a pore-rate value;
- mDBC boundary neighbors only contribute to a missing-support correction based
  on the ratio of full kernel support to real-fluid support, capped at 3.0;
- mDBC mechanics, pore-pressure feedback in momentum, free-surface drainage,
  and mDBC pore-pressure extrapolation were left unchanged.

This differs from the previous one-sided Darcy test because the compression
term is also fluid-neighbor dominated here.

## Test case

- Config: `tests/configs/CaseSWSc2_FluidRate_Tv120_130_Def.xml`
- Runner: `tests/xCaseSWSc2_FluidRate_Tv120_130_win64_GPU.bat`
- Restart: `tests/outputs/CaseSWSc2_HeadN_Tv2_from_p0056_GPU_out/data/Part_0240`
- Window: `Tv = 1.20` to `Tv = 1.30`
- Slip mode: `SlipMode = 2`
- mDBC corrector: `MDBCCorrector = 1`

## Result

| Case | SPH bottom EPWP drop | Theory drop | Slope ratio | Error at Tv=1.30 |
| --- | ---: | ---: | ---: | ---: |
| Previous head-N / pairwise reference | -0.005459 kPa | -0.098618 kPa | 0.055 | +0.176900 kPa |
| Head-space MLS Neumann | -0.005883 kPa | -0.098618 kPa | 0.060 | +0.176477 kPa |
| One-sided Darcy only | -0.012090 kPa | -0.098618 kPa | 0.123 | +0.170269 kPa |
| Fluid-neighbor full pore-rate diagnostic | -0.019298 kPa | -0.098618 kPa | 0.196 | +0.163062 kPa |

## Conclusion

Removing direct mDBC boundary-neighbor contribution from both compression and
Darcy pore-rate terms improves the late-window slope more than the hydraulic
boundary-value variants, which confirms that boundary-neighbor compression is
part of the platform mechanism. However, the recovered slope is still only about
20% of Terzaghi theory over `Tv=1.20 -> 1.30`.

This is therefore not a sufficient formal fix. It suggests that the late
platform is not solved by boundary hydraulic ghost values alone; the coupled
volumetric-strain/storage path near the bottom support remains too strong or
too cancelling. The next useful tests should avoid repeating mDBC pressure
extrapolation variants and should focus on effective storage / compression
weighting near impermeable support, or on whether the theoretical Terzaghi
storage coefficient is represented consistently by the current explicit u-pw
compression term.

The temporary source patch should be reverted after follow-up comparison or
after deciding whether to keep this diagnostic output for reference.
