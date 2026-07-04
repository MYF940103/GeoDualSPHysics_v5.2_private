# Self-weight HeadN late-platform damping check

Date: 2026-07-04

## Purpose

Check whether the late `Tv ~= 1.2` bottom excess pore-pressure platform in the current Head-Neumann/mDBC Scenario 2 run is caused by soil damping suppressing the strain-feedback part of the pore-pressure evolution.

## Test actually completed

The current HeadN Scenario 2 GPU run was stopped after producing restart data beyond `Part_0240`. A short-window damping sweep was started from:

- Restart output: `tests/outputs/CaseSWSc2_HeadN_Tv2_from_p0056_GPU_out/data`
- Restart part: `Part_0240`
- Global time factor at restart: `Tv = 1.20`

The only completed sweep member was:

- `SoilDampingCoef = 0`
- Window: `Tv = 1.20 -> 1.30`
- Excluded particles: none

Target bottom excess pore-pressure values:

| Tv | SPH bottom excess (kPa) | Theory (kPa) | Error (kPa) |
|---:|---:|---:|---:|
| 1.20 | 0.534760 | 0.451018 | +0.083742 |
| 1.25 | 0.531540 | 0.398672 | +0.132868 |
| 1.30 | 0.529929 | 0.352400 | +0.177529 |

The bottom pressure drop from `Tv=1.20` to `Tv=1.30` was only about `0.00483 kPa`, essentially the same platform behavior seen with the current `SoilDampingCoef=0.02` run.

## Conclusion

Turning soil damping off in the late platform window does not restore the missing late-time dissipation. The platform is therefore not primarily caused by `SoilDampingCoef=0.02` smoothing out pore-pressure dissipation or strain feedback.

The remaining likely source is still the late-time bottom mDBC coupling balance: pore-pressure compression/source term, Darcy term, mDBC ghost velocity/divergence, and effective stress feedback near the bottom support.

## Cleanup

The temporary damping sweep XML, bat, logs, figures, and outputs were removed after this conclusion was recorded.
