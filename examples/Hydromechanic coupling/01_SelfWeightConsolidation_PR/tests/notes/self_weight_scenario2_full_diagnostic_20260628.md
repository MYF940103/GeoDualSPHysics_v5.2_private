# Self-weight Scenario 2 full-run diagnostic, 2026-06-28

## Completed run

- Case: `CaseSWScenario2_restart_p0060_D_DTv0005`
- Restart: Stage 1 `Part_0060`
- Solver: GPU release
- `DtFixed=1e-6 s`
- `TimeOut=0.0182185714 s`, equivalent to `Delta Tv=0.005`
- Finished with `code=0`
- Excluded particles: `0`
- Final output: `Part_0211`, `PartTime=3.844119 s`, `Tv~1.055`

Runtime confirmed:

- `Restart soil data: Sigma inherited, Kplastic reset for restart stage.`
- `Restart hydromechanical data: PorePress and PorePress0 inherited.`
- `Boundary="mDBC"`
- `SlipMode="DBC vel=0"`
- `PeriodicActive="Axis-X"`

## Theory comparison

Target summary:

| Tv | bottom excess SPH (kPa) | theory (kPa) | RMS excess (Pa) |
| ---: | ---: | ---: | ---: |
| 0.000 | 10.4016 | 10.6964 | 98.6 |
| 0.005 | 9.9582 | 9.8890 | 125.5 |
| 0.050 | 8.1029 | 8.0355 | 65.0 |
| 0.100 | 6.9921 | 6.9124 | 61.0 |
| 0.250 | 4.8193 | 4.7048 | 69.4 |
| 0.400 | 3.3983 | 3.2469 | 88.5 |
| 0.500 | 2.6385 | 2.5369 | 69.0 |
| 0.700 | 1.7398 | 1.5488 | 120.7 |
| 1.000 | 1.0818 | 0.7388 | 224.8 |

The early trend is correct, but the late-time dissipation is too slow. The bottom excess pore pressure remains about `0.343 kPa` above theory at `Tv=1`.

## Boundary observations

The current case has no left/right mDBC wall particles in the output. `PartBound_*.vtk` contains only 40 bottom boundary particles with:

- `x = 0.005 ... 0.095 m`
- `z = -0.035 ... -0.005 m`

Because `PeriodicActive="Axis-X"`, the lateral direction is periodic. Therefore this run is effectively a laterally periodic 1D column with bottom mDBC, not a column with explicit left/right mDBC side walls.

Fluid-layer diagnostics show that center and side particles at the same elevation have nearly the same error. The late-time discrepancy is therefore not a clear localized side-wall error; it is closer to global under-dissipation / boundary-condition mismatch.

## Slip-mode implication

`SlipMode=1` is `DBC vel=0`. In this code:

- `-mdbc` -> `SlipMode=1`, `DBC vel=0`
- `-mdbc_noslip` -> `SlipMode=2`, `No-slip`
- `-mdbc_freeslip` -> `SlipMode=3`, `Free slip`

Changing only the XML is not sufficient if the bat still uses `-mdbc`, because the command line sets the mDBC slip mode.

For the paper's 1D self-weight consolidation, the text states bottom and lateral boundaries are undrained and the top free surface is drained after the initial undrained response. It does not explicitly prescribe a viscous no-slip wall. For geotechnical rigid smooth/roller support, `Free slip` is the more natural first comparison than `No-slip`; however, the current periodic lateral setup means changing slip mode mainly affects the bottom mDBC boundary.

## Recommended next tests

1. First test `-mdbc_freeslip` using the same periodic geometry and Stage 1 `Part_0060` restart, short run to `Tv=0.05`. This isolates the effect of mDBC slip mode without rebuilding Stage 1.
2. If the difference is small, the late-time error is probably not controlled by slip mode.
3. Then decide whether to build a non-periodic explicit-side-wall version. That requires removing `XPeriodicIncZ`, adding correct side mDBC walls, rerunning Stage 1 with the same boundary mode, and then rerunning Scenario 2. It cannot reuse the existing periodic Stage 1 restart as a strictly consistent initial state.
