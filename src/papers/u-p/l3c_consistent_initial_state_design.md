# L3c Consistent Initial State Design

Date: 2026-05-14

## Candidate Routes

### Route 1: Uniform Initial Excess Pressure Only

This is the L3a route and the L3c reference route:

```text
p_w^0 = |q0| = 10 kPa
Initial effective stress increment = 0
No mechanical load impulse
```

It is the closest match to the Terzaghi analytical initial-value problem under
the current feedback-off implementation.

Status: selected for L3c.

### Route 2: Uniform Initial Excess Plus Isotropic Effective Stress

The code supports a CPU-only isotropic effective stress initializer. This does
not represent a vertical top surcharge or a total-stress state. If set to a
nonzero value, it would add skeleton stress on top of the pore-pressure initial
condition and would no longer match the analytical `p_w^0=|q0|` diffusion gate.

Status: not used for validation.

### Route 3: Initial Total-Stress Equivalent State

This would initialize effective stress and pore pressure so that the total
stress field corresponds to the top surcharge. It is more physically complete
than Route 1, but current source support is incomplete:

- no vertical-only initial stress increment;
- no total-stress initializer;
- no coupled feedback-on validation path.

Status: future source plan only.

### Route 4: Quasi-Static Mechanical Loading

This remains a future mechanical reproduction route. L3b showed that direct
surface force on top material particles still behaves dynamically and is not a
clean Terzaghi generator.

Status: deferred until the loading route is redesigned.

## Selected L3c Setup

L3c uses:

- `H=1.0 m`, `width=0.1 m`, `Dp=0.01 m`;
- `E=2e6 Pa`, `nu=0.3`, `Kw=2e8 Pa`, `n=0.3`, `k=1e-3 m/s`;
- `SoilConstitutiveModel=0`;
- `PorePressureInit=3`;
- `PorePressureExcessAmp=10000 Pa`;
- `PorePressureAnalyticalProfile=3`;
- `PorePressureFeedback=0`;
- `InitialStressMode=0`;
- `MechanicalTopLoad=0`;
- no `AccInput`.

CPU and GPU are both expected to run because no CPU-only stress initializer is
enabled.

## Success Gates

L3c should satisfy:

- CPU/GPU `code=0`;
- `excluded=0`;
- `DtMin=0`;
- initial excess pressure near the `10 kPa` scale;
- no dynamic excess peak above the physical scale;
- top drained residual near zero;
- bottom no-flux proxy small;
- analytical comparison close to L3a and far better than L3b/L2.

## Interpretation

If L3c matches L3a, that is a positive result. It confirms that the
paper-compatible initial-state route is already the pressure initialization
gate, and that nonzero effective-stress initialization is not needed for the
feedback-off Terzaghi diffusion problem.
