# Self-weight scenario 2 q-Darcy platform diagnostic

Date: 2026-07-04

## Purpose

Check whether the late-time bottom excess pore-pressure platform is mainly caused by large cancellation in the Darcy seepage term when total pore pressure and the gravity head term are evaluated separately.

## Temporary code change

The pore-pressure-rate Darcy term was temporarily changed in both CPU and GPU paths from the total-pressure/head form to an excess-pressure form:

- `q = PorePress - PorePress0`
- fluid-fluid pair: `q1 - q2`
- mDBC boundary pair: `q2 = q1` as a pairwise no-flux diagnostic

This touched the CPU interaction argument path and the GPU kernel argument path only for the diagnostic. The change is not retained as the formal implementation.

## Test window

- Case: `CaseSWSc2_QDarcy_Platform`
- Restart source: `CaseSWSc2_HeadN_Tv2_from_p0056_GPU_out/data/Part_0240`
- Global time-factor window: `Tv = 1.20 -> 1.30`
- Solver: GPU release
- Output interval: `DeltaTv = 0.005`

## Result

Bottom excess pore pressure:

| Quantity | Tv=1.20 | Tv=1.30 | Drop |
|---|---:|---:|---:|
| SPH q-Darcy diagnostic | 0.534760 kPa | 0.533091 kPa | 0.001669 kPa |
| Terzaghi theory | 0.451018 kPa | 0.352400 kPa | 0.098618 kPa |

The diagnostic slope ratio is about `0.0169`, so the bottom pore pressure is still essentially stuck on the platform. It is worse than the previous no-Eta diagnostic and does not recover the theory slope.

## Conclusion

The late-time platform is not explained by total-head large-number cancellation alone. Directly rewriting the Darcy term in `q = PorePress - PorePress0` with pairwise `q2=q1` at mDBC boundaries suppresses bottom drainage even more.

Do not retain this q-Darcy patch. The next useful direction is the near-boundary diffusion operator consistency: mDBC boundary particles should participate in the hydraulic boundary treatment, but a pairwise boundary value that independently cancels each fluid-boundary pair is too restrictive for the bottom-layer curvature that drives 1D consolidation.

## Cleanup

The temporary output, temporary XML/BAT, and temporary source patch should be removed after this note is saved.
