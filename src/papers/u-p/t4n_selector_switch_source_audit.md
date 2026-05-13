# T4n Selector Switch Source Audit

## Objective

T4n asks whether the triaxial confinement workflow can start with Zhao
all-surface `f_i` confinement and then switch to lateral-only selected
confinement before feedback or axial loading.

## Existing Capability

Before T4n, the relevant controls were static:

| Control | Current behavior before T4n |
| --- | --- |
| `FlexibleConfiningStress` | Enables the CPU pairwise isotropic confinement source. |
| `ConfiningStressUseFiSelector` | Applies the force only to `f_i <= threshold` target particles. |
| `ConfiningStressUseLateralSelector` | Applies the force only to cylinder lateral particles. |
| `ConfiningStressGeometry` | Enables cylinder class diagnostics. |
| `PorePressureFeedbackStartTime` / `RampEndTime` | Can delay feedback acceleration only. |
| `AccInput` | Can schedule axial loading only. |

There was no existing XML-only way to change
`ConfiningStressUseLateralSelector` during a single run. Feedback and axial
loading could already be delayed, but the confinement target set could not.

## Restart Route

A restart route could in principle run Stage A with all-surface confinement and
then Stage B with lateral-only confinement, but this branch does not yet have a
validated reduced-triaxial restart workflow that preserves and reclassifies
`PorePress`, `ExcessPorePress`, `Sigmac`, velocity, and diagnostics cleanly.
Using restart first would add state-mapping risk to a stage whose purpose is
only to test the selector transition.

## Implemented Minimal Route

T4n therefore adds one narrow CPU-only selector schedule:

```xml
<parameter key="ConfiningStressLateralSelectorStartTime" value="0.003" />
```

Semantics:

- default `0` keeps old behavior;
- when `ConfiningStressUseLateralSelector=1` and start time is `>0`, the
  lateral selector is disabled before that time;
- after the start time, the existing lateral selector is applied;
- the `f_i` selector, cylinder classification, confinement force formula, PR
  pressure update, stress update, and feedback update are unchanged;
- GPU hard-errors for non-default scheduling.

The change is intentionally limited to `FlexibleConfiningStress` target
selection.

