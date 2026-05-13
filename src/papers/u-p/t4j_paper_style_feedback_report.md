# T4j Paper-Style Pore-Pressure Momentum Coupling Report

## Scope

T4j tests a CPU-only paper-style pore-pressure momentum prototype for the
reduced selected-confinement triaxial sample. It does not modify the PR
pressure update, does not implement MCC/DP validation, does not run GPU, and
does not add initial hydrostatic confinement stress.

## Operator 3

`PorePressureFeedbackOperator=3` was added as a CPU-only experimental mode:

```text
a_i^pw = sum_j MassFluid * (p_i + p_j)/(rho_i rho_j) grad W_ij
```

where `p` is either total pore pressure or excess pressure according to
`PorePressureFeedbackMode`. The T4j cases use excess pressure with
`HydraulicElevationSource=0`, so total and excess are effectively identical.

The operator is closer to the u-pw notes than operators `1/2` because it uses a
symmetric stress-pair pressure form. It is still not fully paper-faithful
because it remains a separate CPU feedback pass and does not provide boundary
pressure completion.

## Manufactured Tests

The manufactured tests distinguish internal-gradient consistency from
free-surface stress-pair behavior.

| Field | Operator | Result |
| --- | ---: | --- |
| uniform pressure | `1/2` | zero acceleration |
| uniform pressure | `0/3` | nonzero free-surface response, max `38.53 m/s2` |
| linear `p=1000x` | `2` | machine-precision gradient result |
| linear `p=1000x` | `1` | reasonable direction, finite cloud error |
| linear `p=1000x` | `3` | stress-pair behavior, not a clean internal-gradient operator |

The uniform-pressure free-surface response is not treated as a manufactured
failure for operator `3`. It is a direct consequence of applying an isotropic
stress-like pair term on a truncated support cloud without dummy/boundary
pressure completion. This is exactly why a paper-faithful stress-pair route
cannot stop at the raw material-only pair term.

## CPU Selected-Confinement Cases

All cases were CPU Release, linear elastic skeleton, no axial loading, selected
lateral flexible confinement, `PorePressureFeedbackScale=1`, and
`HydraulicElevationSource=0`.

| Case | Result | Max `PorePressRate` | Notes |
| --- | --- | ---: | --- |
| operator `1`, interior-only | `code=0`, `excluded=0`, `DtMin=0` | `4.79e10 Pa/s` | T4g/T4h baseline; still reverses |
| operator `3`, unfiltered | `code=0`, `excluded=407`, `DtMin=82` | `1.86e12 Pa/s` | severe free-surface/cap/edge artifact |
| operator `3`, interior-only | `code=0`, `excluded=55`, `DtMin=243` | `2.27e12 Pa/s` | class filtering insufficient |

The operator `3` confinement-only gate fails. It is not better than operator
`1` or operator `2` in the dynamic selected-confinement test. Because the gate
failed, no operator-`3` axial-loading smoke was run.

## Interpretation

T4j supports the T4i-B audit: the paper-style stress-pair form is probably the
right algebraic family to understand, but the raw material-only separate-pass
prototype is not stable. The failure is consistent with missing pressure
completion and missing initial stress/equilibrium treatment rather than a mere
choice between difference-gradient and LSQ gradient estimators.

## Decision

- Operator `3` is implemented and retained as an experimental CPU diagnostic.
- It is closer to the u-pw notes than operators `1/2` in pairwise form.
- It does not pass the selected-confinement gate.
- It is not a validation setting.
- Axial loading remains blocked.
- DP/MCC remain deferred.
- GPU remains deferred.

## Recommended Next Step

Proceed to T4k initial hydrostatic confinement design/implementation rather
than continuing to tune feedback operators. Zhao's verification strategy
suggests that starting from an unloaded skeleton and ramping confinement can
launch stress waves before axial loading. The T4d-T4j failures all occur in
confinement-only or feedback reactivation stages, so initial stress/equilibrium
is now the highest-value next test.

Total-stress coupling remains a later candidate, but it should not be started
until the initial confinement state and pressure-stress consistency are
audited.
