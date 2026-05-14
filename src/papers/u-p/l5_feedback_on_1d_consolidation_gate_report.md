# L5 Feedback-On 1D Consolidation Gate Report

## Objective

L5 checks whether pore-pressure feedback can be enabled in the 1D
consolidation initial-state route before moving toward a reduced landslide
baseline. It is a coupling stability gate, not a strict Terzaghi mechanical
loading reproduction.

The route keeps the L3c/L4 initial-state setup and turns on feedback:

```xml
PorePressureInit=3
PorePressureFeedback=1
PorePressureFeedbackMode=1
PorePressureFeedbackOperator=1
InitialStressMode=0
MechanicalTopLoad=0
```

No `AccInput` and no `MechanicalTopLoad` are used.

## Cases

The L5 package is in:

`examples/u-pw/01_1D_Consolidation/experiments/ExternalLoad_L5_FeedbackOnGate/`

Cases:

- low-amplitude CPU diagnostic: `p_w0=1 kPa`;
- target-amplitude CPU diagnostic: `p_w0=10 kPa`;
- target-amplitude GPU parity run after CPU stability was confirmed.

All cases use the L3c hydraulic boundaries:

- top drained;
- bottom no-flux;
- lateral no-flux through the 1D boundary geometry;
- `PorePressureBoundaryOperator=0`;
- `HydraulicElevationSource=1`.

## Run Status

| case | code | excluded | DtMin adjustments | p_w0 |
|---|---:|---:|---:|---:|
| low CPU | 0 | 0 | 0 | 1 kPa |
| target CPU | 0 | 0 | 0 | 10 kPa |
| target GPU | 0 | 0 | 0 | 10 kPa |

The CPU target case was rerun immediately before GPU parity. The GPU run used
the same XML and operator `1`, which is the GPU-supported feedback operator.

## Pressure and Stability Metrics

| case | peak excess | min excess | bottom RMSE | final profile RMSE |
|---|---:|---:|---:|---:|
| low CPU | 1.0e3 Pa | -8.19e2 Pa | 1.08e3 Pa | 9.49e2 Pa |
| target CPU | 1.0e4 Pa | -8.19e3 Pa | 1.08e4 Pa | 9.49e3 Pa |
| target GPU | 1.0e4 Pa | -8.19e3 Pa | 1.08e4 Pa | 9.49e3 Pa |

The pressure scale remains bounded and far below the L2/L3b dynamic peaks
near `6e5 Pa`. The low-amplitude and target-amplitude CPU cases scale almost
linearly by a factor of ten.

However, feedback-on produces oscillatory signed excess pressure. The volume
mean excess pressure is not monotonic, and the target case reaches negative
excess values of about `-8.2 kPa`. This is why L5 remains a coupling gate
rather than a clean Terzaghi validation curve.

## Kinematics and Feedback Diagnostics

| case | velocity max | DivVel maxAbs | PorePressRate maxAbs | feedback accel max |
|---|---:|---:|---:|---:|
| low CPU | 1.12e-3 m/s | 1.04e-2 1/s | 1.54e7 Pa/s | 9.35e-1 m/s2 |
| target CPU | 1.12e-2 m/s | 1.04e-1 1/s | 1.54e8 Pa/s | 9.34e0 m/s2 |
| target GPU | 1.12e-2 m/s | 1.04e-1 1/s | 4.19e9 Pa/s | 1.76e2 m/s2 |

The target CPU kinematics scale consistently from the low-amplitude case.
GPU pressure and velocity metrics match CPU closely, but GPU `PorePressRate`
and feedback-acceleration maxima show much larger diagnostic spikes. These do
not produce particle exclusion or pressure blow-up in this short gate, but
they should be treated as a warning for any GPU landslide feedback route.

## Boundary Checks

| case | final top drained residual | final bottom no-flux proxy |
|---|---:|---:|
| low CPU | 0 Pa | -5.10e-3 Pa |
| target CPU | 0 Pa | -5.10e-2 Pa |
| target GPU | 7.51e-6 Pa | -5.10e-2 Pa |

The hydraulic boundary conditions remain active and well behaved under
feedback-on coupling.

## Comparison With L3c Feedback-Off

L3c feedback-off remains the clean PR diffusion and boundary validation gate.
Compared with L3c:

- L5 introduces finite velocity, `DivVel`, and feedback acceleration;
- L5 keeps the pressure scale bounded;
- L5 does not preserve the clean monotonic Terzaghi-like decay;
- L5 target RMSE is comparable in order to L3c, but the signed pressure field
  oscillates and crosses below zero.

Therefore L5 should not replace L3c/L4 as the paper-compatible diffusion
figure.

## Interpretation

L5 validates that feedback-on 1D coupling can run stably in a short CPU and
GPU gate:

- no excluded particles;
- no DtMin burst;
- no pressure peak comparable to L2/L3b;
- top drained and bottom no-flux remain intact;
- low and target amplitudes scale reasonably.

L5 does not validate:

- strict top surcharge generation;
- full Terzaghi mechanical consolidation;
- a consistent total/effective stress initial state;
- long-run feedback-on behavior;
- GPU feedback diagnostics beyond this short parity check.

## Landslide Entry Decision

The result is sufficient to enter a CPU-first reduced landslide baseline with
clear feedback diagnostics and conservative interpretation. It is not enough
to claim a strict fully coupled validation. GPU landslide feedback should stay
secondary until the `PorePressRate` and feedback-acceleration diagnostic spikes
are understood in a problem closer to the target landslide setup.

## Next Step

Recommended:

1. Enter a CPU-first reduced landslide baseline using the same feedback
   operator policy and detailed pressure/velocity/divergence diagnostics.
2. Keep L5b consistent stress initialization as the next 1D improvement if
   stricter consolidation validation is needed.
3. Do not start damping or viscosity sweeps before a consistent stress or
   mechanical loading route is designed.
