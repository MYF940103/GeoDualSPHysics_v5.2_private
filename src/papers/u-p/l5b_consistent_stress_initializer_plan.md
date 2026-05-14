# L5b Consistent Stress Initializer Plan

## Motivation

L5 shows that feedback-on coupling can remain bounded in a 1D initial-pressure
gate, but it also shows oscillatory signed excess pressure and non-monotonic
mean pressure decay. This is expected because the route starts with pore
pressure but no compatible total/effective stress state.

L5b should address that missing initial-state consistency before any stricter
Terzaghi claim.

## Proposed Initializer

Add a CPU-first, default-off initializer capable of representing an
instantaneous one-dimensional surcharge state:

- initial excess pore pressure `p_w0=|q0|`;
- vertical total-stress increment corresponding to `q0`;
- compatible effective stress convention;
- optional isotropic reference stress if needed;
- no dynamic top force impulse;
- no `AccInput`;
- no `MechanicalTopLoad`.

The initializer must make the total/effective/pore-pressure sign convention
explicit.

## Candidate Parameters

Possible XML interface:

```xml
<parameter key="InitialStressMode" value="2" />
<parameter key="InitialStressVertical" value="-10000" />
<parameter key="InitialStressHorizontal" value="0" />
<parameter key="InitialStressTargetMk" value="all" />
<parameter key="InitialStressZMin" value="0" />
<parameter key="InitialStressZMax" value="1" />
<parameter key="InitialStressConsistentPorePressure" value="1" />
```

The actual names should follow existing source style after a source audit.

## Required Diagnostics

L5b should output:

- initial `Sigma_xx`, `Sigma_yy`, `Sigma_zz`;
- initial pore pressure and excess pressure;
- total-stress-equivalent check;
- feedback acceleration at `t=0+`;
- velocity, `DivVel`, and `PorePressRate`;
- top drained and bottom no-flux residuals;
- comparison with L3c/L5.

## CPU/GPU Plan

Implement CPU first. GPU should remain deferred unless the CPU route is
stable and physically interpretable.

## No-Go Criteria

Do not accept L5b as a strict route if:

- it creates pressure peaks like L2/L3b;
- it relies on damping/viscosity to hide the loading issue;
- it silently changes PR pressure update equations;
- it leaves sign convention ambiguous;
- it cannot preserve top drained and bottom no-flux behavior.

## Relation to Mechanical Loading

L5b is not a loading plate. It is a consistent initial-state route. If the
project later needs to reproduce mechanical load generation itself, a separate
L5c/L5d force-controlled plate or true surface traction route is still needed.
