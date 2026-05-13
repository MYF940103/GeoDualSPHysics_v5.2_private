# T4k Initial Hydrostatic Confinement Plan

## Motivation

T4d-T4j show that the reduced triaxial sample fails before any meaningful DP or
MCC validation:

- confinement-only with active feedback reverses pressure;
- feedback gating and acceleration limiters reduce symptoms but do not create
  a physical closure;
- LSQ feedback improves static gradient consistency but does not improve the
  dynamic gate;
- paper-style operator `3` is closer to the u-pw notes but is unstable without
  pressure-boundary completion.

Zhao's flexible confinement paper uses an initially confined/stressed sample in
the verification workflow. This may be a key missing ingredient: a lateral
confining source applied to an initially unstressed reduced cylinder creates a
dynamic stress wave and couples immediately into the explicit u-pw feedback
loop.

## Candidate Initial Stress Route

Add an opt-in CPU initialization path for the skeleton/effective stress tensor:

```text
sigma'_xx = sigma'_yy = sigma'_zz = p_conf
sigma'_xy = sigma'_xz = sigma'_yz = 0
```

The sign must follow the existing GeoDualSPHysics stress convention. A small
standalone stress-sign audit should precede implementation because the
flexible confinement term and operator `3` use the positive stress-pair
convention, while pore-pressure feedback signs have historically been mixed.

Possible XML:

```xml
<parameter key="InitialHydrostaticConfiningStress" value="1" />
<parameter key="InitialHydrostaticConfiningStressP0" value="50" />
<parameter key="InitialHydrostaticConfiningStressTargetMk" value="-1" />
```

Defaults must preserve current behavior.

## Coupling With Flexible Confinement

The initial stress should not replace `FlexibleConfiningStress`. Instead, it
should reduce the transient needed for the particle cloud to carry the target
confining state:

1. initialize skeleton stress to the confining level;
2. apply flexible lateral confinement at the same target `p0`;
3. run a short confinement-equilibration phase;
4. enable pore-pressure feedback only after the stress/velocity diagnostics are
   quiet;
5. only then restore gentle axial loading.

## Diagnostics Required

T4k should record:

- initial and first-frame stress tensor means;
- lateral selected count and cap leakage;
- velocity/DivVel decay during confinement-only equilibration;
- `PorePressRate` and pressure reversal metrics;
- feedback acceleration by class;
- net force/COM acceleration;
- whether the initial stress reduces the confinement-only feedback burst.

## Why Not Implemented In T4j

T4j was deliberately scoped to the paper-style pore-pressure momentum operator.
Initial hydrostatic stress touches stress-state initialization and sign
conventions, so it deserves a separate source audit and regression gate.

## T4k No-Go Criteria

Do not proceed to DP/MCC unless a linear-elastic selected-confinement case can
run with:

- `code=0`, `excluded=0`;
- no pressure reversal;
- no DtMin burst;
- bounded velocity and DivVel;
- cap leakage still zero;
- full feedback scale `1` or a clearly justified paper-consistent coupling;
- no reliance on a purely diagnostic acceleration cap.
