# L3 1D Consolidation Loading Route Audit Report

## Objective

L3 audits why the L2 paper-aligned 1D consolidation setup did not reproduce the
Terzaghi reference and tests the smallest no-source alternative: an
initial-pressure diffusion gate.

L3 is not a damping sweep and not a new mechanical top-load implementation.

## L2 Diagnosis

L2 aligned the geometry and material constants with the paper-style setup:

- `H=1.0 m`, `width=0.1 m`, `Dp=0.01 m`;
- `E=2e6 Pa`, `nu=0.3`;
- `K_w=2e8 Pa`, `n=0.3`, `k=1e-3 m/s`;
- `SoilConstitutiveModel=0`;
- target load `q0=-10 kPa`.

The blocker is the load route.  L2 applies `q0` as native `AccInput` on a
finite top `mkfluid=1` material layer.  That route is stable and GPU-supported,
but it is a body acceleration, not a quasi-static surface traction or loading
plate.  It generated a strong dynamic response:

| Run | Bottom RMSE vs q0 Terzaghi | Final profile RMSE | Peak excess |
| --- | ---: | ---: | ---: |
| L2 CPU | `2.206e5 Pa` | `4.791e4 Pa` | `6.246e5 Pa` |
| L2 GPU | `2.206e5 Pa` | `4.791e4 Pa` | `6.246e5 Pa` |

This supports the interpretation that the L2 error is dominated by loading
route dynamics rather than a simple CPU/GPU mismatch.

## L3a Initial-Pressure Gate

Created:

`examples/u-pw/01_1D_Consolidation/experiments/ExternalLoad_L3_InitialPressureGate/`

Configuration:

- same geometry and material constants as L2;
- `PorePressureInit=3`;
- `PorePressureAnalyticalProfile=3`;
- `PorePressureExcessAmp=10000 Pa`;
- top drained from initialization;
- bottom no-flux;
- `PorePressureFeedback=0`;
- no `AccInput`;
- `PorePressureBoundaryOperator=0`;
- CPU Release and GPU Release.

## Run Results

| Run | Code | Excluded | DtMin adjustments | Runtime | Steps |
| --- | ---: | ---: | ---: | ---: | ---: |
| CPU | `0` | `0` | `0` | `390.46 s` | `20975` |
| GPU | `0` | `0` | `0` | `50.02 s` | `20975` |

Boundary and dynamics:

| Run | Final top residual | Final bottom no-flux proxy | Final velocity max |
| --- | ---: | ---: | ---: |
| CPU | `0 Pa` | `0.00234 Pa` | `0 m/s` |
| GPU | `0 Pa` | `0.00232 Pa` | `0 m/s` |

Analytical comparison against the same `q0=10 kPa` Terzaghi reference:

| Run | Bottom RMSE | Final profile RMSE | Peak excess |
| --- | ---: | ---: | ---: |
| L3a CPU | `7.287e3 Pa` | `9.129e3 Pa` | `1.000e4 Pa` |
| L3a GPU | `7.287e3 Pa` | `9.129e3 Pa` | `1.000e4 Pa` |

Compared with L2:

| Run | Bottom RMSE reduction | Profile RMSE reduction |
| --- | ---: | ---: |
| CPU | `30.27x` | `5.25x` |
| GPU | `30.27x` | `5.25x` |

## Interpretation

L3a clearly removes the L2 dynamic overshoot.  The peak excess is the intended
`10 kPa`, velocities remain zero, and CPU/GPU are essentially identical.

However, L3a is still not a full paper-level Terzaghi reproduction.  With
`PorePressureFeedback=0`, the test is a PR pressure-diffusion gate.  It bypasses
the mechanical skeleton response that gives the classical Terzaghi storage
coefficient.  The L3a pressure therefore dissipates faster than the paper
Terzaghi curve even though it is far closer than L2.  This is expected for a
feedback-off diffusion gate and should not be hidden.

## Answers Required by L3

1. **Is the L2 error mainly AccInput loading route?**

   Yes.  L3a removes the acceleration route and the `~6.25e5 Pa` excess peak
   disappears.  The bottom RMSE drops by about `30x`.

2. **What is paper `q0` closest to?**

   Continuum-wise it is a top surface surcharge.  In the Terzaghi analytical
   initial-value problem it is equivalent to a uniform initial excess pore
   pressure `p_w^0 = |q0|`.

3. **Current feasible routes**

   `AccInput`, prescribed-motion plate, direct initial excess pressure,
   uniform initial effective stress, and future source-level traction/plate.
   Only the initial-pressure route is currently no-source, CPU/GPU-supported,
   and analytical-gate-friendly.

4. **Best analytical diffusion gate**

   Route 3: `PorePressureInit=3` with uniform `10 kPa` initial excess and no
   mechanical load.

5. **Was L3a run?**

   Yes.  CPU Release and GPU Release both completed with `code=0`,
   `excluded=0`, `DtMin=0`.

6. **Did L3a improve analytical comparison?**

   Yes, strongly relative to L2: bottom RMSE improved by about `30x` and final
   profile RMSE by about `5.25x`.  It still dissipates faster than the paper
   Terzaghi curve because feedback is off and the gate tests PR diffusion rather
   than full coupled storage.

7. **Is source support needed?**

   Not for L3a.  Source support is needed for a strict mechanical top-load
   route or a total-stress/effective-stress/pore-pressure consistent
   initialization route.

8. **Should damping/viscosity sweep start now?**

   No.  L3 shows the first-order issue is loading/initialization route, not
   damping magnitude.  Damping may become useful after a paper-faithful
   mechanical load route exists.

9. **Next recommendation**

   Use L3a as the PR diffusion/boundary gate.  If the 1D module remains active,
   proceed to L3b mechanical top-load design/implementation rather than a
   damping sweep.  If a strict mechanical load is not currently a priority, the
   module can move on with L3a documented as the analytical diffusion gate.

## Files Generated

- `l3a_case_summary.csv`
- `l3a_analytical_profiles.csv`
- `l3a_profile_metrics.csv`
- `l3a_bottom_pressure_metrics.csv`
- `l3a_boundary_metrics.csv`
- `l3a_vs_l2_comparison.csv`
- `figures/l3a_*`
