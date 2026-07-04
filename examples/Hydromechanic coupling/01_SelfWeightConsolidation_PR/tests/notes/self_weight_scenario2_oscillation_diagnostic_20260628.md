# Self-weight Scenario 2 oscillation diagnostic, 2026-06-28

## Trigger

The Scenario 2 bottom dissipation curve does not look uniformly slow. It follows the Terzaghi trend reasonably well at early time, then develops low-frequency deviations and finally stalls near the end of the run.

## Data inspected

- Baseline output: `tests/outputs/CaseSWScenario2_restart_p0060_D_DTv0005_out`
- Baseline figures/data: `tests/figures/CaseSWScenario2_restart_p0060_D_DTv0005`
- Pure-diffusion comparison: `tests/figures/CaseSWScenario2_restart_p0060_D_DTv0005_pure_diffusion`

The baseline case used:

- `StepAlgorithm=2` (`Symplectic`)
- `DtFixed=1e-6 s`
- `HydroMechDrainage=1`
- `PoreShepardRegularization=0`
- `SlipMode=1`
- `mDBC-Corrector=True`
- `SoilDampingCoef=4e-05` in the actual Run.csv

## Main observations

The early dissipation is not globally slow. The full coupled run and the pure-diffusion diagnostic are close at early time:

| Tv | full SPH bottom kPa | pure from SPH init kPa | full - pure kPa |
| ---: | ---: | ---: | ---: |
| 0.100 | 6.992 | 6.991 | +0.001 |
| 0.250 | 4.819 | 4.762 | +0.057 |
| 0.400 | 3.398 | 3.287 | +0.112 |
| 0.500 | 2.639 | 2.568 | +0.071 |
| 0.700 | 1.740 | 1.568 | +0.172 |
| 0.850 | 1.164 | 1.081 | +0.082 |
| 0.900 | 1.091 | 0.957 | +0.134 |
| 1.000 | 1.082 | 0.748 | +0.334 |

The strongest qualitative issue is after about `Tv=0.88-0.90`: the full coupled bottom excess pore pressure nearly stalls near `1.08 kPa`, while the pure-diffusion diagnostic and Terzaghi solution continue to dissipate.

The profile error is not only a bottom-layer artifact. From `Tv=0.9` onward the full coupled excess-pressure profile changes very little through most of the column.

## Checks that did not indicate the cause

- Particle state is stable: all 1000 fluid particles remain `Type=3`, `Mk=1`, and `Rhop=2100`.
- Free-surface detection is stable: the output keeps `FSType` counts at `{0: 990, 2: 10}`.
- No particle exclusion occurred.
- The maximum velocity magnitude decreases monotonically; there is no obvious high-frequency velocity blow-up.

## Current interpretation

The evidence points to a low-frequency coupled skeleton/compression effect rather than a pure hydraulic diffusion error.

Layer-averaged velocities show that the upper column keeps moving downward faster than the lower column. With the current `u-pw` equation, even small `vz` gradients are multiplied by `Kw/n`, so the volumetric compression term can remain large enough to oppose the Darcy dissipation term. This can explain why the pore pressure appears to stall: the diffusion term may still be dissipating pore pressure, but it is being canceled by residual compression-induced pore pressure generation.

This matches the earlier pure-diffusion diagnostic: when displacement, strain, stress, and velocity coupling are removed, the same initial profile dissipates close to theory.

## Recommended next diagnostic

Do not restart with a full parameter sweep yet. Use the available restart data near the problem window:

- `Part_0170` / `PartExtra_0170` (`Tv approx 0.85`)
- `Part_0180` / `PartExtra_0180` (`Tv approx 0.90`)

Run short continuation tests to isolate the cause:

1. High-damping continuation from `Part_0170` or `Part_0180`, for example `SoilDampingCoef=0.02`, keeping all other settings unchanged. If the platform disappears, the cause is residual coupled skeleton/compression motion.
2. Temporary pore-rate decomposition output:
   - compression contribution `kwn*(-divv)`
   - seepage contribution `kwn*2*khyd*lapw/(rho_w*g)`
   - gravity-head contribution `kwn*2*khyd*lapz`
   - total pore-pressure rate
3. Only if the compression term is not responsible, return to mDBC pore-pressure correction or diffusion-operator tests.

The most informative next test is item 2, but item 1 is cheaper if we can tolerate a short restart continuation.

## Targeted tests completed

Two focused restart diagnostics were run from the retained baseline `Part_0180`, i.e. global `Tv approx 0.90`.

### Test 1: high-damping continuation

- Configuration: `tests/configs/CaseSWScenario2_restart_p0180_D_DTv0005_damp002_short_Def.xml`
- Run script: `tests/xCaseSWScenario2_restart_p0180_D_DTv0005_damp002_short_win64_GPU.bat`
- Output: `tests/outputs/CaseSWScenario2_restart_p0180_D_DTv0005_damp002_short_out`
- Figures/data: `tests/figures/CaseSWScenario2_restart_p0180_D_DTv0005_damp002_short`
- Change relative to baseline: only `SoilDampingCoef=0.02`, run for one output interval `Tv=0.900 -> 0.905`.

Bottom excess pore-pressure comparison:

| case | Tv=0.900 kPa | Tv=0.905 kPa | delta kPa |
| --- | ---: | ---: | ---: |
| baseline | 1.09133 | 1.08968 | -0.00164 |
| high damping 0.02 | 1.09133 | 1.08122 | -0.01011 |
| Terzaghi theory | 0.94551 | 0.93392 | -0.01159 |

The high-damping continuation nearly restores the theoretical local dissipation slope over this interval. This strongly supports the interpretation that the plateau is caused by residual coupled skeleton motion / volumetric compression cancelling the Darcy dissipation, rather than a globally slow pore-pressure diffusion coefficient.

### Test 2: temporary pore-rate decomposition

Temporary GPU code was added only to write the pore-rate decomposition into `HydroMechLoadAce`:

- `x`: compression term `Kw/n*(-divv)`
- `y`: Darcy pressure-Laplacian term
- `z`: gravity-head term

The temporary source patch was removed after the diagnostic runs, and the GPU Release executable was rebuilt without the diagnostic write.

Diagnostic outputs:

- One-step diagnostic: `tests/outputs/CaseSWScenario2_restart_p0180_D_ratediag_1step_out`
- One-step figures/data: `tests/figures/CaseSWScenario2_restart_p0180_D_ratediag_1step`
- One-output-interval diagnostic: `tests/outputs/CaseSWScenario2_restart_p0180_D_ratediag_DTv0005_out`
- One-output-interval figures/data: `tests/figures/CaseSWScenario2_restart_p0180_D_ratediag_DTv0005`

At the end of the `Tv=0.900 -> 0.905` interval, the bottom-layer instantaneous pore-rate decomposition was:

| component | kPa/s |
| --- | ---: |
| compression | +249.945 |
| Darcy pressure Laplacian | -269.488 |
| gravity head | +18.883 |
| total | -0.661 |

The final instantaneous total pore-pressure rate is close to the expected theoretical dissipation order, but the integrated pressure change over the whole interval remains slow in the low-damping baseline. Therefore the problem is not that the end-of-interval diffusion operator is too slow. The likely mechanism is an oscillatory coupled response inside the interval: compression and diffusion alternate/cancel over time, and the final instantaneous rate alone does not represent the interval average.

## Current conclusion

The mid-to-late Scenario 2 error should be treated as a coupled dynamic damping/stabilization problem, not as a pure hydraulic diffusion-speed error.

Recommended next step:

1. Keep the baseline data and high-damping one-interval diagnostic.
2. Run a short damping sweep from `Part_0180` over several output intervals, for example `SoilDampingCoef=0.005, 0.01, 0.02`, to find the smallest damping that removes the `Tv approx 0.90` plateau without visibly over-damping the profile.
3. If source-level diagnostics are needed again, accumulate time-averaged pore-rate components over the interval rather than outputting only the final instantaneous rate.
