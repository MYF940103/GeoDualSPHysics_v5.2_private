# T4t True Platen Reaction Source Audit

## Objective

T4t audits whether the explicit triaxial platen workflow can report a
top/bottom axial reaction that is more faithful than the previous
specimen-stress proxy:

```text
Fz_proxy = -mean(Sigma_zz)_specimen * pi * R^2
```

The diagnostic must not change the mechanics. It is CPU-only, opt-in, and
intended for feedback-off platen triaxial baselines before any DP/MCC or full
feedback validation.

## Current Force Availability

Ordinary fixed/moving `mkbound` platens are not floating bodies. The existing
`SaveFtAce` machinery is therefore not a reliable reaction output for these
platens; it is tied to floating body force/acceleration reporting.

The usable CPU location is the fluid-bound pair loop in
`JSphCpu::InteractionForcesFluid(..., boundp2=true, ...)`. This loop computes
the acceleration contribution on each specimen fluid/material particle from
nearby boundary particles. For a selected top or bottom platen boundary
particle, the opposite of the specimen pair force is the closest available
SPH pairwise reaction contribution.

The implementation uses the actual mkbound value from `MkInfo` rather than the
raw code type. This matters because fixed and moving boundary code types are
not equal to user-facing `mkbound=1` and `mkbound=2`.

## Implemented Diagnostic Definition

`PlatenReactionMode=0` accumulates, for each fluid-bound pair involving a
selected platen particle:

```text
F_platen += -m_i * a_i(pair from selected boundary particle)
```

where `i` is the specimen material/fluid particle. The accumulated acceleration
contribution includes the existing SPH fluid-bound stress/viscous pair
contribution computed in the CPU loop. It does not include prescribed motion
constraint forces, gravity, external body acceleration, damping, pore-pressure
feedback, or the lateral flexible confinement diagnostic term.

This is therefore a true SPH pairwise interaction accumulator for the
specimen-platen contact contribution, but not a complete actuator/constraint
reaction including the force required to prescribe the platen kinematics.

## Output and Sign Convention

The log line reports:

```text
top_force=(Fx,Fy,Fz) N
bottom_force=(Fx,Fy,Fz) N
top_axial_stress Pa
bottom_axial_stress Pa
force_balance_error
```

The axial direction uses the configured confinement cylinder axis when
available, otherwise the global `z` axis. For the current triaxial cases:

- positive top `Fz` is compression from the specimen on the moving top platen;
- negative bottom `Fz` is compression on the fixed bottom platen;
- `top_axial_stress = dot(F_top, axis) / A`;
- `bottom_axial_stress = -dot(F_bottom, axis) / A`;
- `force_balance_error = |F_top + F_bottom| / (|F_top| + |F_bottom|)`.

## CPU/GPU Status

The diagnostic is controlled by `SavePlatenReactionDiagnostics=1` and is
CPU-only. GPU execution with this diagnostic enabled hard-errors. Default
behavior is unchanged because the diagnostic is off by default and has no
mechanical side effects.

## Remaining Limitations

- The diagnostic is written to the run log and parsed into CSV by the T4t
  postprocessor; it is not yet a native standalone solver CSV.
- It is a pairwise SPH interaction reaction, not a full prescribed-motion
  constraint reaction.
- It is currently implemented for mode `0` only.
- GPU support is deferred until the CPU platen validation route is useful.

