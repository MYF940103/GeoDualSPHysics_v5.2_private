# Fixed-dt u-pw diagnostic summary

Date: 2026-06-04

Purpose: diagnose the Scenario 2 discrepancy using the same fixed time step as the
legacy result and supporting-material setting: `DtFixed = 1e-6`. The CPU code was
also changed so `FixedDt` is honored directly and is not reduced by `PoreDtSafety`.

## Diagnostic outputs

- `diag1_scenario2_analytic_fixeddt_t04`: analytical self-weight initialization,
  gravity on, fixed `dt=1e-6`, run to 0.4 s.
- `diag2_hydrostatic_constantz_fixeddt_t02`: hydrostatic `ConstantZ`
  initialization, gravity on, fixed `dt=1e-6`, run to 0.2 s.
- `diag3_legacy_part0200_restart_fixeddt_t04`: restart from the legacy
  `Part_0200` state, current CPU executable, fixed `dt=1e-6`, run to 0.4 s.

## Bottom excess pore pressure comparison

Values are bottom-layer averages in Pa. `theory` is Terzaghi 1D consolidation
using the stage-2 consolidation time. For the restart case, `Part_0200` is
treated as t = 0 of the drainage stage.

| case | time since drainage start (s) | bottom excess | theory | RMS error |
|---|---:|---:|---:|---:|
| analytical current | 0.00 | 10693.9 | 10696.3 | 5.4 |
| analytical current | 0.02 | 10384.3 | 9848.1 | 754.3 |
| analytical current | 0.10 | 7424.7 | 8738.1 | 369.6 |
| analytical current | 0.20 | 6012.3 | 7906.0 | 638.4 |
| analytical current | 0.40 | 4023.4 | 6729.3 | 1091.6 |
| legacy baseline | 0.00 | 11185.6 | 10696.4 | 262.3 |
| legacy baseline | 0.02 | 10554.9 | 9848.1 | 511.8 |
| legacy baseline | 0.10 | 8844.0 | 8738.1 | 88.4 |
| legacy baseline | 0.20 | 8008.4 | 7906.0 | 81.9 |
| current restart from legacy Part_0200 | 0.00 | 11185.6 | 10696.4 | 262.3 |
| current restart from legacy Part_0200 | 0.02 | 10554.9 | 9848.1 | 511.8 |
| current restart from legacy Part_0200 | 0.10 | 8844.0 | 8738.1 | 88.4 |
| current restart from legacy Part_0200 | 0.20 | 8008.4 | 7906.0 | 81.9 |

Conclusion: the current PR evolution reproduces the legacy restart result exactly
when started from the same `Part_0200` state. The analytical initialization has a
nearly exact fluid-particle field at t = 0, but it over-dissipates immediately.

## Hydrostatic diagnostic

The hydrostatic-only `ConstantZ` case starts with zero excess pore pressure.
Because effective stress is not also initialized, gravity drives immediate
undrained compression, so this is not a pure diffusion-only equilibrium test.

| time (s) | bottom excess | min excess | max excess | mean excess |
|---:|---:|---:|---:|---:|
| 0.00 | 0.0 | 0.0 | 0.0 | 0.0 |
| 0.02 | 10109.3 | -49.1 | 10109.3 | 5477.5 |
| 0.10 | 8793.9 | -49.1 | 8793.9 | 5109.7 |
| 0.20 | 7959.5 | -49.1 | 7959.5 | 4809.3 |

This confirms that `PorePress0` is retained, but it does not isolate boundary
diffusion because the mechanical state is not in equilibrium.

## Boundary-state comparison

All-particle VTK exports show that the analytical initialization gives bottom
boundary particles a lower `PorePress0` than the adjacent bottom fluid layer,
even though those boundary particles are geometrically deeper.

Initial analytical state:

| group | z range | mean PorePress | mean PorePress0 | mean excess |
|---|---:|---:|---:|---:|
| bottom boundary | -0.035 to -0.015 | 20043.7 | 9564.8 | 10478.9 |
| bottom fluid layer | 0.005 to 0.015 | 20352.0 | 9711.9 | 10640.1 |

Legacy restart state:

| group | z range | mean PorePress | mean PorePress0 | mean excess |
|---|---:|---:|---:|---:|
| bottom boundary | -0.035 to -0.015 | 20620.1 | 10006.2 | 10613.9 |
| bottom fluid layer | 0.005 | 20897.5 | 9711.9 | 11185.6 |

Likely source: in `InitHydroMechState()` analytical mode, boundary pressure and
stress are initialized at `Pos + BoundNormal` (ghost/interface position), while
the PR seepage term in `InteractionPorePressureRateT()` uses the actual neighbor
coordinate `pos[p2].z` in `lapz`. Therefore the hydrostatic head cancellation
`p_w/(rho_w g) + z = const` is broken for boundary neighbors.

## Next recommended fix

Make the coordinate used for boundary pore-pressure state consistent with the
coordinate used in the PR seepage interaction. The most local options are:

1. Initialize boundary `PorePress0`, total `PorePress`, and analytical effective
   stress using actual boundary coordinates for PR consistency.
2. Or, in the PR interaction with mDBC boundary neighbors, use the same ghost
   coordinate that was used to initialize/update the boundary pore state.

The second option is closer to mDBC philosophy, but the first option is a smaller
diagnostic patch. Either way, hydrostatic pressure and the `lapz` coordinate must
refer to the same physical point.
