# T4m Zhao All-Surface Confinement Design

## Objective

T4m tests whether isotropic confinement should be established using Zhao's
all-surface kernel-truncation mechanism before switching to lateral-only
triaxial loading. This is a workflow diagnostic, not a DP/MCC or paper
reproduction stage.

## Route 1: T4l Lateral + Cap Support

T4l uses selected lateral `FlexibleConfiningStress` plus explicit
`CapConfiningStress`:

- lateral surface: pairwise stress-like confinement;
- top/bottom caps: integrated cap-normal force;
- edge ring: skipped by cap support.

This improves center pressure but leaves a large cap/edge mismatch and a
significant `q` proxy.

## Route 2: Zhao All-Surface f_i Confinement

T4m's main route is:

```xml
<parameter key="InitialStressMode" value="1" />
<parameter key="InitialEffectiveStressIso" value="50" />
<parameter key="FlexibleConfiningStress" value="1" />
<parameter key="ConfiningStressUseFiSelector" value="1" />
<parameter key="ConfiningStressUseLateralSelector" value="0" />
<parameter key="CapConfiningStress" value="0" />
```

The goal is to let the same isotropic pair term act wherever the free-surface
kernel support is incomplete. With the T3 geometry this selects both lateral
and cap/edge surface regions through the `f_i <= 0.70` criterion.

Expected benefit:

- one confinement discretization across all surfaces;
- no explicit cap/lateral edge discontinuity;
- lower residual `q` before feedback is enabled.

Main risk:

- all-surface confinement is not the final triaxial stage, because axial
  loading later needs caps/platen treatment and lateral-only confinement.

## Route 3: All-Surface Stage Then Selector Switch

If Route 2 improves hydrostatic equilibrium, the next route should be staged:

1. Stage A: all-surface isotropic confinement equilibrium;
2. Stage B: switch to lateral-only confinement and introduce top axial loading.

This likely needs either restart workflow or selector scheduling. T4m does not
implement that switch; it only determines whether the all-surface equilibrium
gate is worth pursuing.

## T4m Case Matrix

| Case | Purpose |
| --- | --- |
| T4l reference, feedback off | Current lateral+cap baseline. |
| All-surface `f_i`, feedback off | Hydrostatic equilibrium test. |
| All-surface `f_i`, delayed feedback | Full-feedback confinement gate. |

No axial loading is allowed unless the all-surface feedback-on gate passes.
