# T4t True Platen Reaction Patch Plan

## Motivation

T4q-T4s establish that explicit top/bottom platens can be represented with
existing fixed/moving `mkbound` XML mechanics. The remaining strict triaxial
measurement gap is true platen reaction.

The current postprocessing uses:

```text
sigma_a_proxy = -mean(Sigma_zz) over specimen particles
Fz_proxy = sigma_a_proxy * pi * R^2
```

This proxy is useful for reduced feedback-off trends, but it is not the
reaction force exerted on the moving or fixed platen.

## Current Limitation

The existing `SaveFtAce` route is tied to floating bodies. The explicit
triaxial platens are ordinary fixed/moving boundary groups:

- top platen: moving `mkbound=1`;
- bottom platen: fixed `mkbound=2`.

There is no saved per-`mkbound` accumulator for specimen-platen interaction
forces. Therefore T4s reports:

- `true_reaction_available = 0`;
- `reaction_type = specimen_stress_proxy`.

## Minimal Patch Scope

A T4t patch should be opt-in, CPU-first, and diagnostic-only.

Suggested XML controls:

```xml
<parameter key="SavePlatenReactionDiagnostics" value="0" />
<parameter key="PlatenTopMkBound" value="1" />
<parameter key="PlatenBottomMkBound" value="2" />
<parameter key="PlatenReactionArea" value="0.002827433388" />
```

Possible output:

- top platen particle count;
- bottom platen particle count;
- top reaction vector;
- bottom reaction vector;
- axial reaction force `Fz`;
- axial stress `Fz/A0`;
- top/bottom force balance residual;
- separation between contact/internal reaction and prescribed-motion
  kinematic state where the solver makes that distinction possible.

## Implementation Notes

The patch should accumulate interaction contributions during the CPU boundary
or fluid-boundary force pass, grouped by `mkbound`.

Important constraints:

- do not change prescribed motion;
- do not change PR pressure update;
- do not change `SoilConstitutiveModel`;
- do not convert the proxy into a fake true reaction;
- keep default behavior unchanged;
- hard-error on GPU if the diagnostic is requested before a GPU implementation
  exists.

If exact contact-pair reaction cannot be isolated cleanly, the diagnostic must
write `reaction_type=proxy` and explain what is being accumulated.

## Recommended Timing

The true reaction patch is not required immediately for the reduced T4s
feedback-off elastic baseline. It should be done before strict axial-stress
validation or any claim of platen reaction agreement.

Reasonable next sequence:

1. T5 reduced DP feedback-off platen baseline, if the goal is a qualitative
   constitutive smoke and the report keeps the reaction-proxy caveat.
2. T4t true reaction diagnostics before strict stress-path or paper-level
   comparison.
3. Full feedback and MCC only after the platen reaction and feedback stability
   issues are separately resolved.
