# Cryer C4-B2 Flexible Confining Stress XML Design

Date: 2026-05-12

## Objective

This document proposes the XML interface for a future flexible confining stress
source. The feature is not implemented yet.

## Proposed Parameters

The first implementation can use scalar parameters under `<execution>` or a
dedicated `<special>` block. The recommended readable form is:

```xml
<flexibleconfiningstress active="false">
  <mode value="0" comment="0=isotropic free-surface confining stress" />
  <p0 value="10000" units_comment="Pa, positive compression" />
  <targetmkfluid value="all" comment="all soil material particles or one mkfluid" />
  <rampstart value="0" units_comment="s" />
  <rampend value="0" units_comment="s" />
</flexibleconfiningstress>
```

If the existing parameter parser is simpler to extend with flat keys, the
equivalent keys are:

```xml
<parameter key="FlexibleConfiningStress" value="0" />
<parameter key="ConfiningStressP0" value="10000" />
<parameter key="ConfiningStressRampStart" value="0" />
<parameter key="ConfiningStressRampEnd" value="0" />
<parameter key="ConfiningStressTargetMk" value="-1" />
<parameter key="ConfiningStressMode" value="0" />
```

`ConfiningStressTargetMk=-1` means all soil/material particles.

## Semantics

| Parameter | Meaning |
|---|---|
| `FlexibleConfiningStress` / `active` | Off by default. Enables the mechanical confining stress source. |
| `ConfiningStressP0` / `p0` | Positive compression magnitude in Pa. |
| `ConfiningStressRampStart` | Time at which the ramp begins. |
| `ConfiningStressRampEnd` | Time at which full `p0` is reached. If equal to start, the load is instantaneous. |
| `ConfiningStressTargetMk` | Target soil/material marker; `-1` or `all` for all material particles. |
| `ConfiningStressMode` | `0` isotropic free-surface confining stress; other values reserved. |

## Defaults and Compatibility

- Default is off.
- Existing XML files are unchanged.
- The switch is independent of `AccInput`.
- The switch is independent of `BodyGravityStopTime`.
- The switch is independent of `HydraulicGravity`.
- The switch does not change `PorePressureBoundaryOperator`.
- The switch does not change `SoilConstitutiveModel`; strict Cryer should still
  use `SoilConstitutiveModel=0`.

## Logging

When active, the log should print:

- confining stress enabled;
- `p0`;
- ramp start/end;
- target marker;
- mode;
- CPU/GPU support status;
- warning that the source is mechanical only and does not impose drained
  hydraulic boundary conditions.

## GPU Behavior

Until a CUDA implementation exists, enabling this switch in a GPU run should be
a hard error. Silent fallback to no load or to `AccInput` is not acceptable.

## Strict Cryer Use

The strict sphere draft should include the interface only as a TODO block until
C4-B3 implements the CPU path. It must not make the draft appear runnable or
validated.

