# T4n Staged Confinement Switch Design

## Route Comparison

### Route 1: Single-Run Selector Scheduling

Stage A uses:

```xml
ConfiningStressUseFiSelector=1
ConfiningStressUseLateralSelector=1
ConfiningStressLateralSelectorStartTime=0.003
```

Before `0.003 s`, the lateral selector is temporarily inactive, so all
low-`f_i` free-surface particles are confined. After `0.003 s`, only lateral
particles remain active.

This route was selected because it is continuous, low risk, and tests the real
target-set transition without restart machinery.

### Route 2: Restart

Stage A would run all-surface confinement to equilibrium, save state, then
restart with lateral-only confinement. This may become useful later, but it
requires a validated restart workflow for stress, pore pressure, velocity, and
classification state.

### Route 3: Manual Two-Case Diagnostic

Running all-surface and lateral-only cases separately would not test the actual
transition and therefore cannot answer the T4n stability question.

## Test Matrix

| Case | Purpose |
| --- | --- |
| all-surface reference, feedback off | T4m-style reference. |
| all-surface -> lateral, feedback off | Direct switch gate. |
| all-surface -> lateral, delayed feedback | Feedback gate after switching. |

Axial loading is allowed only if the selector switch and delayed-feedback gate
are stable.

## Gate

The switch passes only if the active target count changes as expected without
large jumps in `q`, velocity, `DivVel`, or `PorePressRate`. The delayed-feedback
case must also avoid reversal, strong negative pressure, and DtMin bursts
before any axial loading is restored.

