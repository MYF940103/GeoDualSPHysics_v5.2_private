# L3c Terzaghi Initial Condition Audit

Date: 2026-05-14

## Objective

L3c audits the initial condition behind the one-dimensional Terzaghi
consolidation comparison after L2 and L3b showed that force or acceleration
generation on top material particles excites a dynamic pore-pressure peak.

## Terzaghi Initial Condition

For the paper-style one-dimensional setup, the surcharge is

```text
q0 = -10 kPa
```

In the classical instantaneous-undrained loading idealization, the applied
compressive load is initially carried by the pore water. The excess pore
pressure initial condition is therefore

```text
p_w^0 = |q0| = 10 kPa
```

The Terzaghi diffusion solution then starts from a nearly uniform excess
pressure field and dissipates it through the drained top boundary. In this
idealized initial-value problem, the mechanical load generation stage is not
resolved dynamically.

## Stress Correspondence

The total stress increment from the surcharge can be written conceptually as

```text
Delta sigma_total = Delta sigma_effective + Delta p_w
```

For the instantaneous undrained idealization used by the analytical diffusion
solution:

- `Delta p_w = |q0|`;
- `Delta sigma_effective` is approximately zero at `t=0+`;
- drainage then dissipates the excess pressure and transfers load to the
  skeleton in the continuum theory.

Because the current L3 route keeps `PorePressureFeedback=0`, the solver is not
using pore pressure to drive skeleton stress transfer. The clean analytical
gate is therefore to initialize the excess pressure and avoid imposing a
dynamic mechanical impulse.

## Boundary Conditions

The paper-aligned hydraulic conditions are:

- top drained: excess pressure is clamped to zero at the drainage layer from
  initialization onward;
- bottom no-flux: bottom layer correction holds the bottom excess pressure
  equal to a nearby interior reference;
- lateral no-flow in the 1D column is represented by the side boundaries and
  the one-dimensional profile analysis.

The top drained clamp acts immediately at `t=0`, so the initial profile is
uniform in the column interior but already zeroed in the top drained layer.
This is the same convention used in L3a and L3c postprocessing.

## L3a Agreement And Limitation

L3a already matched the analytical initial-value route most closely:

- `PorePressureInit=3`;
- `PorePressureExcessAmp=10000 Pa`;
- no `AccInput`;
- no `MechanicalTopLoad`;
- top drained from `t=0`;
- bottom no-flux correction active.

Its limitation is not the initial condition. Its limitation is that
`PorePressureFeedback=0`, so L3a/L3c validate the PR diffusion and boundary
operators, not the full coupled mechanical consolidation process.

## Initial Effective Stress

A nonzero effective-stress increment is not required for the analytical
Terzaghi initial condition. Adding one in the current solver would not improve
consistency unless the code also represents a matching total-stress state and
coupled pore-pressure-to-skeleton feedback.

The current `InitialStressMode=1` is an isotropic effective compression helper,
not a vertical surcharge or total-stress initializer. For this L3c gate, the
consistent choice is:

```text
InitialStressMode=0
InitialEffectiveStressIso=0
```

## L3c Interpretation

L3c formalizes the consistent initial-state route:

- initialize `p_w^0=10 kPa`;
- keep effective stress increment zero;
- avoid mechanical impulse routes;
- run CPU/GPU PR diffusion with the paper hydraulic boundaries.

This is paper-compatible as an analytical diffusion and initial-state gate. It
is still not a full mechanical load-generation reproduction.
