# T4e Feedback Gating Source Audit

## Objective

T4d showed that selected lateral confinement destabilizes the reduced
linear-elastic triaxial specimen during confinement-only equilibration when
`PorePressureFeedback=1`. The matching `PorePressureFeedback=0` case remained
stable over the retained window. T4e therefore audits whether the existing
u-pw PR interface can delay or ramp pore-pressure feedback acceleration during
the confinement stage.

## Existing Feedback Controls

The pre-T4e interface already provided:

| Parameter | Existing role |
| --- | --- |
| `PorePressureFeedback` | Enables or disables mechanical acceleration from pore-pressure gradients. |
| `PorePressureFeedbackMode` | Selects total pressure or excess-pressure feedback. |
| `PorePressureFeedbackOperator` | Selects symmetric stress-style feedback or difference-gradient feedback. |

No existing parameter could express:

- feedback off until a physical time;
- gradual feedback activation over a time interval;
- reduced feedback acceleration scale for diagnostic staging.

`HydromechDampingStartTime` and `HydromechDampingEndTime` can time-window the
damping term, but they do not gate pore-pressure feedback. XML-only staging
was therefore insufficient for the T4e matrix.

## Minimal Source Patch

T4e adds a narrow feedback gating mechanism:

| Parameter | Default | Behavior |
| --- | ---: | --- |
| `PorePressureFeedbackStartTime` | `0` | When feedback is enabled, feedback acceleration is zero for `t < start`. |
| `PorePressureFeedbackRampEndTime` | `0` | If greater than `StartTime`, feedback factor ramps linearly from zero to `Scale`. |
| `PorePressureFeedbackScale` | `1` | Maximum feedback acceleration scale, constrained to `[0,1]`. |

The effective feedback factor is:

```text
0                                      t < start
Scale * (t-start)/(ramp_end-start)     start <= t < ramp_end
Scale                                  otherwise
```

when `PorePressureFeedback=1`. If `PorePressureFeedback=0`, the factor is
always zero.

## Scope

The patch only scales the pore-pressure feedback acceleration added to the
mechanical momentum equation. It does not change:

- the PR pore-pressure rate equation;
- the pressure update;
- Shepard smoothing;
- hydromechanical damping;
- `SoilConstitutiveModel`;
- `FlexibleConfiningStress`;
- AccInput;
- Cryer boundary operators.

Default behavior is unchanged: absent parameters give start `0`, ramp disabled,
and scale `1`, which reproduces the previous feedback path.

## CPU/GPU Status

The implementation is CPU-first. GPU Release still builds, but non-default
feedback gating/scale is explicitly rejected on GPU. This follows the current
policy for staged triaxial confinement diagnostics: no GPU run should silently
ignore feedback timing.

## Build Status

After the source patch:

- CPU Release build passed.
- GPU Release build passed.
- No GPU simulation was run.

## T4e Usage

The T4e cases use the new parameters only in:

`examples/u-pw/04_Undrained_Triaxial/experiments/T4e_FeedbackGatedConfinement/`

They are diagnostic staging controls, not a validated production triaxial
workflow.
