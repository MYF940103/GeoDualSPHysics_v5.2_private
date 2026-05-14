# L3c Consistent Initial-State 1D Consolidation Validation Report

Date: 2026-05-14

## Setup

L3c uses the paper-aligned 1D consolidation constants from L2/L3a:

- `H=1.0 m`, `width=0.1 m`, `Dp=0.01 m`;
- `E=2e6 Pa`, `nu=0.3`;
- `Kw=2e8 Pa`, `n=0.3`, `k=1e-3 m/s`;
- `SoilConstitutiveModel=0`;
- top drained from `t=0`;
- bottom no-flux correction enabled.

The selected route is:

```text
PorePressureInit=3
PorePressureExcessAmp=10000 Pa
PorePressureAnalyticalProfile=3
InitialStressMode=0
MechanicalTopLoad=0
AccInput disabled
PorePressureFeedback=0
```

This represents the Terzaghi instantaneous-undrained initial condition as a
uniform `p_w^0=|q0|=10 kPa` excess pressure field, with zero effective-stress
increment. No dynamic top material forcing is applied.

## CPU/GPU Results

Both runs completed:

| run | code | excluded | DtMin adjustments |
| --- | ---: | ---: | ---: |
| CPU Release | 0 | 0 | 0 |
| GPU Release | 0 | 0 | 0 |

The GPU route is supported because L3c does not enable CPU-only
`InitialStressMode=1` or CPU-only `MechanicalTopLoad=1`.

## Initial State

The initial excess-pressure target is `10 kPa`. Because the top drained layer
is clamped at initialization, the specimen-wide initial mean excess pressure is
`9.8 kPa`, while the interior and bottom remain at `10 kPa`.

The effective stress fields remain zero:

```text
mean Sigma_xx = 0 Pa
mean Sigma_yy = 0 Pa
mean Sigma_zz = 0 Pa
p'_proxy = 0 Pa
q_proxy = 0 Pa
```

This is intentional for the feedback-off diffusion gate.

## Analytical Comparison

L3c reproduces L3a, as expected:

| run | bottom RMSE vs q0 | final profile RMSE vs q0 | peak excess |
| --- | ---: | ---: | ---: |
| L3c CPU | 7.287e3 Pa | 9.129e3 Pa | 1.000e4 Pa |
| L3c GPU | 7.287e3 Pa | 9.129e3 Pa | 1.000e4 Pa |
| L3a | 7.287e3 Pa | 9.129e3 Pa | 1.000e4 Pa |
| L3b | 2.724e5 Pa | 4.401e5 Pa | 5.897e5 Pa |
| L2 | 2.206e5 Pa | 4.791e4 Pa | 6.246e5 Pa |

The comparison confirms that the L3b dynamic peak is avoided. L3c stays at the
physical `q0` pressure scale and remains close to the analytical diffusion
gate.

## Boundary Checks

Final boundary diagnostics:

| run | top drained residual | bottom no-flux proxy | final bottom excess |
| --- | ---: | ---: | ---: |
| CPU | 0 Pa | 2.34e-3 Pa | 3.53e2 Pa |
| GPU | 0 Pa | 2.32e-3 Pa | 3.53e2 Pa |

The top drained and bottom no-flux conditions remain reasonable.

## Interpretation

L3c is a paper-compatible diffusion plus initial-state validation route. It is
not a mechanical load-generation reproduction because:

- `PorePressureFeedback=0`;
- the skeleton is not dynamically driven by pore pressure;
- no total-stress initializer is present;
- no force-controlled loading plate is used.

Within that scope, L3c is the best current Terzaghi analytical gate and is much
closer than L2 or L3b.

## Source Patch Status

No source patch was needed. The existing source can express the selected route
with `PorePressureInit=3` and default `InitialStressMode=0`.

The current `InitialStressMode=1` is CPU-only isotropic effective compression,
so it is not suitable as a strict vertical surcharge or total-stress
initializer for this L3c validation.

## Next Step

Do not start a broad damping or viscosity sweep from L2/L3b. The next strict
mechanical route would be one of:

1. L3d: quasi-static loading plate / surface traction with controlled staging;
2. L3e: reporting package that uses L3c as the diffusion/boundary validation
   and documents L3b as a failed mechanical-load prototype;
3. move to the next u-p module if mechanical load generation is not the
   priority.
