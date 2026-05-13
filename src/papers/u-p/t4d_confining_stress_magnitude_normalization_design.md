# T4d Confining-Stress Magnitude Normalization Design

## Motivation

T4b showed that Zhao-style renormalized gradients roughly doubled the selected
lateral acceleration on the reduced coarse triaxial cylinder. T4d therefore
tested whether raw selected confinement is simply too strong for the current
u-pw response.

The T4d evidence is mixed:

- the confinement force scales linearly with p0 in the diagnostic logs;
- reducing p0 from 50 Pa to 12.5 Pa reduces logged lateral acceleration from
  1.50592 m/s2 to 0.376479 m/s2;
- however, the low-p0 feedback-on case still produces pressure reversal and a
  2.66e12 Pa/s pressure-rate excursion.

Thus magnitude is part of the stress imposed on the reduced specimen, but it is
not the only failure mechanism. The dominant instability is the active
pore-pressure feedback loop during confinement-only equilibration.

## Current Effective Magnitude

At the fourth diagnostic force print:

| Variant | p0_eff | Lateral acceleration mean |
| --- | ---: | ---: |
| target p0 | 40.217 Pa | 1.50592 m/s2 |
| low p0 | 10.0543 Pa | 0.376479 m/s2 |
| long ramp | 22.3428 Pa | 0.836621 m/s2 |

The acceleration is nearly proportional to `p0_eff`, which suggests the raw
force term is internally consistent in scale. The reduced coarse cylinder may
still be too lightly damped and too short to absorb that traction without
feedback oscillation.

## Zhao Magnitude Expectation

Zhao's flexible confinement term is intended to impose an isotropic confining
stress that cancels in the interior and remains as an inward traction near a
kernel-truncated surface. In a strict triaxial route, the effective lateral
stress should be checked against:

1. a target confining pressure;
2. a surface-only target set selected by kernel completeness;
3. a stable equilibrium state before axial loading;
4. a clear stress output convention.

The current T4d reduced case lacks an equilibrium stage and explicit initial
hydrostatic stress, so direct acceleration magnitude matching is not yet a
complete validation criterion.

## Candidate Opt-In Normalization

If a source-level normalization is introduced later, it should be opt-in and
CPU-only at first:

```text
ConfiningStressMagnitudeNormalize=0/1
ConfiningStressNormalizationMode
ConfiningStressReferenceAcceleration
ConfiningStressDiagnosticOnly=1
```

Candidate modes:

| Mode | Concept | Risk |
| --- | --- | --- |
| mean lateral acceleration match | rescale selected force so mean inward lateral acceleration matches a target diagnostic value | may become case-calibrated rather than Zhao-derived |
| f_i-dependent scaling | scale by local kernel completeness to avoid over-weighting severe truncation | could distort the Zhao cancellation mechanism |
| confinement-only calibration | determine a scale from a short elastic confinement-only diagnostic | useful for smoke stability, not a paper-valid boundary law |
| l0/ln-inspired scaling | follow Zhao's large-deformation rescaling idea | requires tracking deformation and validating stress convention |

## Why No Source Normalization Was Implemented in T4d

T4d did not implement normalization because the cleanest diagnostic was
feedback on/off:

- feedback off stabilizes the same selected force at the same p0;
- lower p0 does not remove the feedback-on instability;
- longer ramp and damping do not remove the center-core reversal.

Adding force normalization now would risk masking the real blocker: selected
confinement needs an equilibration protocol for the coupled u-pw feedback loop.
The next source change should only be made after deciding whether to stage or
gate feedback during confinement equilibration.

## Recommended Next Source Gate

Before implementing force normalization, test a T4e staged equilibration route:

1. confinement ramp with pore-pressure feedback disabled or delayed;
2. damping until velocity and `DivVel` are small;
3. enable feedback and verify no immediate pressure-rate burst;
4. only then add axial loading.

If this still fails, then an opt-in magnitude normalization can be justified as
a separate source task with diagnostics showing pre/post scaling of lateral
acceleration and net force.
