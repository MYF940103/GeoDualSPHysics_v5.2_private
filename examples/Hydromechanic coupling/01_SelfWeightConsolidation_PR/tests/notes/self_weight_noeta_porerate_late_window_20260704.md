# Self-weight pore-rate Eta2 late-window diagnostic, 2026-07-04

## Purpose

Check whether the late bottom excess-pore-pressure platform is caused by the
`+Eta2` regularization in the pore-pressure-rate Darcy/Laplacian operator:

```text
lapw, lapz denominator: rr2 + Eta2
```

The temporary test removed `Eta2` only from the pore-pressure-rate `lapw/lapz`
denominator in the CPU and GPU pore-rate paths. Artificial viscosity, stress
diffusion, density diffusion, and other operators still used their original
`Eta2` regularization.

## Test window

- Restart source: `tests/outputs/CaseSWSc2_HeadN_Tv2_from_p0056_GPU_out/data/Part_0240`
- Global window: `Tv = 1.20 -> 1.30`
- XML: temporary `CaseSWSc2_HeadN_NoEta_Platform_Def.xml`
- Solver: GPU release
- Time step and all physical parameters unchanged.

## Result

| Tv | bottom EPWP SPH kPa | Terzaghi kPa | error kPa |
| --- | ---: | ---: | ---: |
| 1.20 | 0.534760 | 0.451018 | +0.083742 |
| 1.25 | 0.524702 | 0.398672 | +0.126030 |
| 1.30 | 0.523172 | 0.352400 | +0.170772 |

The no-`Eta2` run dissipated slightly more than the retained HeadN late-window
platform check, but it still remained on a clear late-time platform. The
bottom pressure drop from `Tv=1.20` to `Tv=1.30` was only about `0.0116 kPa`,
whereas the Terzaghi bottom pressure should drop about `0.0986 kPa`.

## Conclusion

The `+Eta2` regularization in the pore-rate Laplacian denominator is not the
primary cause of the late platform. It may slightly affect the residual
magnitude, but deleting it does not restore the missing late-time dissipation.

The temporary code patch, XML, BAT, figures, and output folders should be
removed after recording this conclusion. The next diagnosis should continue
with the bottom mDBC support residual / force-balance path rather than another
global damping or pore-rate denominator sweep.
