# T4i Current Feedback Source Mapping

## Scope

This document maps the current source implementation of
`PorePressureFeedbackOperator=0/1/2` against the paper-fidelity question raised
after T4h. It is a read-only source audit.

## Configuration And Dispatch

Relevant configuration is parsed in `source/JSph.cpp`:

- `PorePressureFeedback`;
- `PorePressureFeedbackMode`;
- `PorePressureFeedbackOperator`;
- T4e feedback timing controls;
- T4f relaxation/limiter controls;
- T4g class-filter controls;
- T4h LSQ controls.

CPU dispatch is in `source/JSphCpuSingle.cpp::Interaction_Forces`:

1. `InteractionForcesFluid` computes the ordinary skeleton stress divergence,
   flexible confinement, viscosity, and related accelerations.
2. `ComputePorePressureAccel` computes operator `0` candidate acceleration.
3. `ComputePorePressureAccelDiff` computes operator `1`, unless operator `2`
   is selected.
4. `ComputePorePressureAccelLsq` computes operator `2` into the same diagnostic
   array used by operator `1`.
5. `ApplyPorePressureFeedback` adds the selected feedback acceleration to
   `Acec`, optionally applying timing, class filters, relaxation, and caps.

## Operator 0: Symmetric Stress-Style

Source: `source/JSphCpu.cpp::ComputePorePressureAccelT`.

For particle `i`, the source computes:

```text
p_i = PorePress_i - p_hydro_i    if FeedbackMode=1
p_i = PorePress_i                if FeedbackMode=0

a_i += -m_j (p_i+p_j)/(rho_i rho_j) gradW_ij
```

Because of current kernel-gradient sign conventions, this is the branch that
matches the stress-style algebraic pattern used by the effective-stress pair
term and Zhao confinement. It is separate from the main stress-divergence loop
and uses the raw kernel gradient.

Important behavior:

- closest current operator to the paper-style symmetric pore-pressure term;
- produces nonzero free-surface acceleration under uniform pressure on the
  material-only cylinder because kernel support is truncated;
- not currently paired with boundary pore-pressure extrapolation or dummy
  boundary completion;
- can be gated/filtered/limited by `ApplyPorePressureFeedback`.

## Operator 1: Difference-Gradient

Source: `source/JSphCpu.cpp::ComputePorePressureAccelDiffT`.

For particle `i`, the source computes:

```text
a_i += -m_j (p_j-p_i)/(rho_i rho_j) gradW_ij
```

This is an internal pressure-gradient estimator. It gives exactly zero for a
uniform pore-pressure field in the retained T4g/T4h material-only cloud.

Important behavior:

- manufactured uniform pressure is clean;
- linear pressure has correct direction and reasonable magnitude, but finite
  boundary-cloud error;
- not the same discrete form as the paper's symmetric stress-like pore-pressure
  pair term;
- still fails selected-confinement confinement-only gate with reversal and
  about `4.79e10 Pa/s` max `PorePressRate` in T4g/T4h interior-only cases.

## Operator 2: LSQ Pressure Gradient

Source: `source/JSphCpu.cpp::ComputePorePressureAccelLsqT`.

For each material particle, operator `2` solves:

```text
p_j - p_i ~= g_i dot (x_j-x_i)
A_i g_i = b_i
a_i = -g_i/rho_i
```

with kernel-volume weights and a condition-number proxy. Fallback is controlled
by `PorePressureFeedbackLSQFallback`:

- `0`: fall back to operator `1`;
- `1`: zero feedback for that particle.

Important behavior:

- passes T4h manufactured uniform and linear pressure tests;
- in T4h, all `407` particles solved with `0` fallback and condition proxy
  about `3-4`;
- dynamic selected-confinement gate still fails;
- not a paper-style symmetric stress term.

## Pressure Variable

All three operators use the same pressure variable convention:

- `PorePressureFeedbackMode=0`: total `PorePress`;
- `PorePressureFeedbackMode=1`: `PorePress - GetHydrostaticPorePressure(pos)`.

Under `HydraulicElevationSource=0`, the hydrostatic reference is zero in the
triaxial tests, so total and excess pressure are identical. T4g verified this.

## Corrected Gradient Status

None of the current feedback operators uses the Zhao-style corrected gradient
implemented for `ConfiningStressGradientMode=1`. Operator `2` performs its own
LSQ pressure-gradient reconstruction, but it is not a corrected kernel-gradient
stress-pair term.

## Same Loop Status

The current feedback path is not inside the same pairwise momentum loop as
`Sigmac` stress divergence. The ordinary stress-divergence term in
`InteractionForcesFluid` uses:

```text
m_j (sigma_i + sigma_j)/(rho_i rho_j) gradW_ij
```

Flexible confinement uses a similar stress-like pair contribution. Feedback is
computed later and then added as a separate acceleration. This is a structural
difference from the paper-style momentum summation.

## Filters, Caps, And Gating

All operators can be affected by:

- T4e feedback timing: `StartTime`, `RampEndTime`, `Scale`;
- T4f feedback relaxation and acceleration caps;
- T4g class filtering;
- T4h LSQ fallback only for operator `2`.

These are useful diagnostics, but they move the route farther from direct paper
fidelity if used as validation settings.

## Effective Stress Convention

Current evidence still indicates:

- `Sigmac` stores skeleton/effective stress;
- pore pressure is not written into `Sigmac`;
- no direct total/effective stress double-counting has been proven.

The problem is not proven double counting. The problem is that the paper-like
pore-pressure contribution is not currently integrated with the same
stress-divergence and boundary treatment as the skeleton stress.

## GPU Status

GPU does not support the non-default triaxial feedback controls:

- feedback timing/stabilization/class filtering hard-errors when requested;
- operator `2` hard-errors;
- GPU should remain deferred until the CPU paper-faithful route is stable.

## Source Mapping Conclusion

Operator `0` is the closest algebraic source implementation to the original
u-pw SPH momentum term. Operator `1` and `2` are alternative pressure-gradient
estimators. The missing paper-fidelity pieces are same-loop stress-style
coupling, corrected/renormalized gradient consistency, and boundary/initial
state handling.
