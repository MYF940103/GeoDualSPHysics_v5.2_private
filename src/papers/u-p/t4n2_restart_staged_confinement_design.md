# T4n2 Restart-Staged Confinement Design

## Objective

The goal is to test a literature-supported staging workflow without adding a
ramped selector transition:

1. equilibrate the specimen with Zhao all-surface `f_i` confinement;
2. save/restart the u-pw state;
3. switch the restarted run to lateral-only confinement;
4. check whether the restart transition is mechanically quieter than the
   single-run instant selector switch.

## Stage A - All-Surface Isotropic Equilibrium

Configuration:

- `InitialStressMode=1`;
- `InitialEffectiveStressIso=50`;
- `FlexibleConfiningStress=1`;
- `ConfiningStressUseFiSelector=1`;
- `ConfiningStressUseLateralSelector=0`;
- `PorePressureFeedback=0`;
- no cap support;
- no axial loading.

Stage A uses the T4m all-surface route because it produced the best
feedback-off hydrostatic state so far: `p'` near `46 Pa` and `q` near `16 Pa`.

## Stage B - Restart, Lateral-Only, Feedback Off

Stage B regenerates the same particle cloud, loads Stage A `Part_0023`, and
switches:

```xml
<parameter key="ConfiningStressUseLateralSelector" value="1" />
<parameter key="ConfiningStressLateralSelectorStartTime" value="0" />
<parameter key="PorePressureFeedback" value="0" />
```

This is a true restart, not a single-run scheduled selector. The Stage B gate
checks:

- exact restart continuity of saved fields;
- target count transition `208 -> 112`;
- `q`, velocity, `DivVel`, `PorePressRate`, and pore-pressure response after
  the lateral-only confinement starts.

## Stage C - Optional Delayed Feedback

Stage C uses the same restart as Stage B and then enables class-filtered
operator-1 feedback after a hold period:

```xml
<parameter key="PorePressureFeedback" value="1" />
<parameter key="PorePressureFeedbackStartTime" value="0.007" />
<parameter key="PorePressureFeedbackRampEndTime" value="0.008" />
<parameter key="PorePressureFeedbackUseClassFilter" value="1" />
<parameter key="PorePressureFeedbackInteriorOnly" value="1" />
```

This is diagnostic only. It is not a validation setting and it does not use
feedback caps or reduced feedback scale.

## Fresh Lateral Comparison

A fresh lateral-only feedback-off case is included to separate restart benefit
from simply starting the whole run with lateral-only confinement.

## No Axial Loading

Axial loading remains disabled unless Stage B and Stage C both pass. The T4n2
design intentionally stops before DP/MCC or triaxial stress-path validation.
