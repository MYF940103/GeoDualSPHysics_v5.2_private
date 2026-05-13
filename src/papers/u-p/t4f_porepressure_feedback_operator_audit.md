# T4f Pore-Pressure Feedback Operator Audit

## Scope

This audit follows T4e, where selected lateral confinement was stable with
`PorePressureFeedback=0` but became unstable when full feedback was restored.
The goal was to inspect only the feedback acceleration path, not the PR
pressure-rate equation or the constitutive model.

## Source Locations

| Item | Location | Finding |
| --- | --- | --- |
| Symmetric stress-style feedback acceleration | `source/JSphCpu.cpp`, `ComputePorePressureAccelT` | Computes a stress-like pore-pressure acceleration. Not used by T4f cases. |
| Difference-gradient feedback acceleration | `source/JSphCpu.cpp`, `ComputePorePressureAccelDiffT` | T4f uses this through `PorePressureFeedbackOperator=1`. |
| Feedback application | `source/JSphCpu.cpp`, `ApplyPorePressureFeedback` | Adds selected feedback acceleration directly into `Acec`. T4f adds diagnostics and optional relaxation/caps here. |
| Force sequence | `source/JSphCpuSingle.cpp`, `Interaction_Forces` | Mechanical/stress/confinement acceleration is computed first, then feedback acceleration is added, then hydromechanical damping is applied, then `PorePressRate` is computed. |
| GPU path | `source/JSphGpu.cpp`, `ApplyPorePressureFeedbackGpu` | GPU only supports default timing/stabilization and `PorePressureFeedbackOperator=1`; non-default T4e/T4f controls hard-error. |

## Operator Form Used In T4f

For `PorePressureFeedbackOperator=1`, the CPU difference-gradient operator uses
neighbor pressure difference:

```text
a_fb,i += -m_j (p_j - p_i) / (rho_i rho_j) grad W_ij
```

With `PorePressureFeedbackMode=1`, the pressure entering this operator is the
excess pressure under the no-elevation triaxial convention. The gradient is the
raw SPH kernel gradient, not the Zhao renormalized confinement gradient.

## Coupling Order

The T4f sequence is:

1. compute stress divergence and selected `FlexibleConfiningStress`;
2. compute `DivVel`, `LapPorePress`, `LapZ`;
3. compute `PorePressureAccel` and `PorePressureAccelDiff`;
4. add pore-pressure feedback acceleration into `Acec`;
5. apply hydromechanical damping;
6. compute PR `PorePressRate`.

This ordering means feedback acceleration can immediately change the velocity
field that drives `DivVel` and then the next-step pore-pressure rate. T4e/T4f
therefore isolates a plausible positive feedback loop: confinement generates
pore pressure, pressure gradients produce acceleration, acceleration changes
`DivVel`, and `DivVel` feeds the next `PorePressRate`.

## T4e Failure Signature

T4e delayed full feedback still produced pressure reversal, large
`PorePressRate`, DtMin bursts, and exclusions. Feedback scale `0.25` removed
exclusions over the short window but still reversed pressure. This showed that
time gating alone was insufficient and that the acceleration magnitude itself
needed direct diagnostics and opt-in stabilization.

## Missing Diagnostics Before T4f

Before T4f the code did not report:

- raw vs used feedback acceleration;
- feedback acceleration relative to non-feedback/confining acceleration;
- limiter/relaxation activation count;
- class-wise feedback acceleration maxima for lateral/cap/interior regions.

T4f adds these diagnostics without changing default behavior.
