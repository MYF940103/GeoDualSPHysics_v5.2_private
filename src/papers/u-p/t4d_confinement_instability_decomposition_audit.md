# T4d Confinement Instability Decomposition Audit

## Scope

T4d isolates the instability seen in T4c by removing axial `AccInput` entirely
and running confinement-only selected flexible confinement variants. No source
code, Cryer boundary code, PR governing equation, or constitutive code was
changed.

The retained variants are:

| Variant | Feedback | p0 | Ramp end | Damping xi | Axial load |
| --- | ---: | ---: | ---: | ---: | --- |
| feedback on | 1 | 50 Pa | 0.001 s | 0.05 | none |
| feedback off | 0 | 50 Pa | 0.001 s | 0.05 | none |
| low p0 | 1 | 12.5 Pa | 0.001 s | 0.05 | none |
| long ramp + damping | 1 | 50 Pa | 0.0018 s | 0.20 | none |

All four CPU Release runs finished with `code=0`, `excluded=0`, and
`Kplastic=0`.

## Timing of Reversal

The target-p0 confinement-only feedback-on case reverses without axial loading:

| Variant | Reversal time, all particles | Reversal time, center core | DtMin adjustments | Max PorePressRate |
| --- | ---: | ---: | ---: | ---: |
| feedback on | 0.001404 s | 0.001404 s | 85 | 3.12e12 Pa/s |
| feedback off | none | none | 0 | 2.11e7 Pa/s |
| low p0 | 0.001504 s | 0.001407 s | 41 | 2.66e12 Pa/s |
| long ramp + damping | 0.001588 s | 0.001405 s | 62 | 2.70e12 Pa/s |

This confirms that the T4c reversal is not caused by the delayed axial
`AccInput`: in T4d no axial load exists at any time, yet the same failure mode
appears.

## Relation to Confinement Ramp

The target-p0 feedback-on case completes the confinement ramp at 0.001 s. The
pressure reversal appears at 0.001404 s, after the ramp has reached the target
pressure. The first Shepard smoothing event occurs at step 10 near 0.001306 s,
with large pressure excursions already present in the feedback-on cases.

The long-ramp case delays the all-particle reversal to 0.001588 s, but the
center-core reversal still occurs at 0.001405 s. Longer ramp and stronger
damping reduce the initial lateral acceleration, but do not remove the core
instability.

## Relation to Pore-Pressure Feedback

Feedback off is the decisive diagnostic. With the same p0, same ramp, same
selector, same damping, and same confinement force, disabling
`PorePressureFeedback` eliminates pressure reversal over the retained window:

- max `PorePressRate` drops from 3.12e12 Pa/s to 2.11e7 Pa/s;
- velocity max drops from 215 m/s to 7.57e-4 m/s;
- max `DivVel` drops from 4682 1/s to 0.0317 1/s;
- DtMin adjustments drop from 85 to 0.

The confinement force still generates pore pressure through the PR update, but
the unstable mechanical amplification loop is strongly reduced when pore
pressure is not fed back into momentum.

## Relation to DivVel, Velocity, and DtMin

Feedback-on variants show synchronized growth of `DivVel`, velocity, and
PorePressRate. The target-p0 feedback-on case reaches:

- max `DivVel` = 4682 1/s;
- max velocity = 215 m/s;
- final mean pore pressure = -1.19e8 Pa;
- final mean `PorePressRate` = -1.07e12 Pa/s.

The low-p0 and long-ramp cases reduce lateral acceleration but still trigger
large velocity and `DivVel` growth. This indicates that the instability is a
nonlinear feedback loop, not a simple linear response to the initial confining
traction magnitude.

## Relation to Lateral Acceleration and Cap Leakage

The lateral selector remains geometrically healthy:

| Variant | Max logged lateral acceleration mean | Max cap axial leakage |
| --- | ---: | ---: |
| feedback on | 1.50592 m/s2 | 0 |
| feedback off | 1.50592 m/s2 | 0 |
| low p0 | 0.376479 m/s2 | 0 |
| long ramp + damping | 0.836621 m/s2 | 0 |

Cap leakage is not the trigger. The lateral selector applies the intended
lateral-only confinement, but the coupled mechanical-pressure feedback response
is not equilibrated.

## Current Diagnosis

The T4/T4b/T4c instability source is now localized to selected-confinement
equilibration under active u-pw feedback. Axial loading is not the first
trigger. Renormalized gradients amplify the same issue, but raw-gradient
selected confinement is already unstable when feedback is on.

The best immediate route is not DP or MCC. The next step should test a staged
equilibration strategy that decouples or gates pore-pressure feedback during
confinement settling, then reintroduces feedback and axial loading only after
velocities and `DivVel` are small.
