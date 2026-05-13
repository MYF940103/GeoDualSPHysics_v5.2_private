# T4i Initial Confinement Before Feedback Plan

## Objective

This plan asks whether the selected-confinement full-feedback failure may be
caused by missing initial confinement equilibrium rather than only by the
feedback operator.

## Zhao Motivation

Zhao's flexible confinement method can be applied as a boundary traction through
kernel truncation, but the verification discussion distinguishes two practical
states:

- a specimen that already carries the equivalent hydrostatic confining stress;
- a specimen that starts unloaded and receives a ramped confining traction.

The second route can launch stress waves and requires damping. The current
T4d/T4e/T4h triaxial route is the second route: it starts from zero skeleton
stress, ramps selected lateral confinement, and asks pore pressure feedback to
remain stable during that transient.

## Current Evidence

T4d showed:

- pressure reversal appears in confinement-only runs before axial loading;
- feedback off is stable;
- feedback on creates `PorePressRate` spikes and reversal;
- lower p0 and longer ramp only delay or reduce the artifact.

T4e showed:

- feedback-off confinement equilibration remains stable;
- full feedback reactivation destabilizes the sample even after delay/ramp.

T4f/T4g/T4h showed:

- limiters and class filtering reduce symptoms;
- corrected LSQ gradient consistency does not solve the dynamic gate.

This sequence leaves initial confinement equilibrium as a serious missing
component.

## Route 1: Initial Hydrostatic Effective Stress

Add an opt-in initialization route for the skeleton stress tensor:

```text
sigma'_xx = sigma'_yy = sigma'_zz = sigma_conf
sigma'_xy = sigma'_yz = sigma'_xz = 0
```

The sign must match the current `Sigmac` convention. This stress state should
be stored as skeleton/effective stress, not pore pressure. Flexible confinement
then maintains the lateral membrane traction rather than creating the entire
initial stress wave dynamically.

Risks:

- requires source/XML support;
- must be compatible with `SoilConstitutiveModel=0`;
- must be clearly separated from pore pressure and total stress output.

## Route 2: Staged Isotropic Confinement Equilibration

Continue using ramped confinement, but make it a formal stage:

1. confinement ramp with feedback off;
2. damping until velocity/DivVel/PorePressRate fall below thresholds;
3. activate paper-style feedback;
4. only then start axial loading.

T4e suggests that time gating alone is insufficient with the current feedback
operator, but this staged route may still be useful once the paper-style
coupling is implemented.

## Route 3: Combined Route

For strict triaxial reproduction, the most robust future route is likely:

1. initialize hydrostatic skeleton stress;
2. enable selected Zhao confinement to maintain lateral pressure;
3. use paper-faithful pore-pressure momentum coupling;
4. equilibrate briefly with damping;
5. begin axial loading.

This is more source work, but it is closer to the physical laboratory initial
condition than repeatedly tuning a transient from an unloaded state.

## Answer To The Key Question

Yes. The current full-feedback failure may plausibly be caused by the missing
initial hydrostatic confinement state, or by its interaction with the feedback
operator, rather than by a simple sign/unit bug in operator `1/2`.

The evidence does not prove that initial stress alone will fix the issue. It
does show that continuing to tune feedback caps is not a paper-faithful path.

## Recommendation

T4j should not jump directly to DP/MCC. It should first implement or gate a
paper-style pore-pressure momentum route under controlled conditions. If that
still fails under selected confinement, the next source feature should be an
initial hydrostatic effective-stress initialization for triaxial confinement.
