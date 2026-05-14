# TINT1 u-pw PR Time-Integration Mapping

Date: 2026-05-14

## PR Form Used in the Code

The implemented PR pressure-rate form is:

```text
dp_w/dt = (K_w / n) * ( - div(v_s)
                       + k/(rho_w |g|) Lap(p_w)
                       + k Lap(z_h) )
```

where `Lap(z_h)` is active when `HydraulicElevationSource` is enabled. The
comment in `ComputeHydroPorePressRatePR()` states the sign convention:

- `DivVel < 0` means skeleton compression;
- pore-pressure generation is compression-positive;
- therefore the volumetric contribution is `-DivVel`.

The scalar update is explicit Euler:

```text
p_w^{new} = p_w^{old} + dt * dp_w/dt
```

## What the u-pw PR Notes Require

The u-pw PR equation is naturally an explicit scalar evolution law once
`div(v_s)`, pressure diffusion, and elevation-head diffusion have been
discretized. The paper-level statement does not by itself define how the scalar
should be embedded into DualSPHysics' Verlet or Symplectic half-step mechanics.

Therefore a direct transplant of `p += rate * dt` is incomplete unless the
time layer of all inputs is specified:

- which velocity is used for `div(v_s)`;
- whether the pressure Laplacian uses old, predicted, or corrected pressure;
- whether feedback acceleration uses old or updated pressure;
- when drained/no-flux boundary conditions are enforced.

## Current Mapping to DualSPHysics

Current mapping:

```text
rate = R(v_stage, x_stage, rho_stage, p_old, boundary_stage)
p_new = p_old + dt * rate
mechanics uses feedback acceleration computed from p_old
```

In Verlet, `v_stage`, `x_stage`, and `rho_stage` are the pre-Verlet values.

In Symplectic, the corrector rate uses predicted mechanical variables, but
still uses `p_old`. There is no pressure predictor.

## Time-Layer Questions

### Velocity Divergence

For feedback-off diffusion-only gates such as L3c/L4, `DivVel` is small or
zero, so the velocity time layer is not a dominant issue.

For feedback-on gates such as L5 and BND1 mode `2`, `DivVel` becomes active.
Using predicted/corrector velocity divergence with old pressure is an
explicitly split coupling. It may be acceptable as a first-order scheme, but it
is not a time-centered coupled PR/mechanics update.

### Pressure Laplacian

The diffusion term currently uses `p_old`. This is the standard explicit choice
and is compatible with the existing `PorePressureDt` stability warning.

However, when boundary operator `2` adds stronger solid-wall contributions,
the explicit Laplacian can amplify high-frequency boundary error before the
mechanical state is corrected. That does not prove a governing-equation error,
but it points to a staging/stability sensitivity.

### Feedback Acceleration

Feedback acceleration currently uses `p_old` in the same interaction stage
that computes `PorePressRate`. The new pressure affects feedback only on the
next interaction.

This lag is stabilizing in one sense because it avoids using freshly updated
pressure in the same acceleration. It is also phase-lagged, especially in
Symplectic where mechanics otherwise has predictor/corrector staging.

## Possible Error Modes

The current staging can introduce:

- phase lag between pressure generation/dissipation and feedback acceleration;
- pressure-rate overshoot when boundary Laplacian contributions are strong;
- feedback-on oscillation because `DivVel` reacts to feedback from old pressure;
- boundary instability in generalized mode `2`, where ordinary solid-wall
  quadrature adds a new explicit diffusion contribution;
- CPU/GPU interpretation differences because post-update clamps are placed
  differently relative to the mechanical update.

## Interpretation for Existing Gates

L3c/L4 are mostly diffusion/boundary gates with feedback off. They are less
sensitive to the mechanics/pressure phase issue and remain valid Level-1
gates.

L5 feedback-on and BND1 mode `2` are more sensitive because pressure feedback,
velocity divergence, and boundary Laplacian terms interact in the same step.
The TINT1 audit can plausibly explain part of the BND1 mode `2` feedback-on
instability, but it cannot prove causality without an opt-in time-integration
experiment.

