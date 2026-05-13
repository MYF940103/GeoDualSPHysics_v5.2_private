# T4h Corrected Feedback Gradient Report

## Objective

T4h implements and tests a corrected pressure-gradient feedback acceleration
for the selected-confinement triaxial workflow. The scope is deliberately
narrow: no PR pressure-rate change, no soil-model change, no Cryer boundary
change, no GPU simulation, no axial loading unless the confinement-only gate
passes, and no DP/MCC validation.

## Source Change

`PorePressureFeedbackOperator=2` was added as a CPU-only experimental LSQ
pressure-gradient feedback path.

For each active material particle, the operator solves:

```text
p_j - p_i ~= g_i dot (x_j - x_i)
A_i g_i = b_i
A_i = sum_j w_j r_ij tensor r_ij
b_i = sum_j w_j (p_j - p_i) r_ij
a_fb,i = -g_i / rho_i
```

The pressure variable follows `PorePressureFeedbackMode`. In the T4h tests,
`HydraulicElevationSource=0`, so total and excess pore pressure are equivalent.

New optional parameters:

```xml
<parameter key="PorePressureFeedbackLSQRadiusFactor" value="1" />
<parameter key="PorePressureFeedbackLSQConditionLimit" value="1000000000000" />
<parameter key="PorePressureFeedbackLSQFallback" value="0" />
```

The default feedback behavior is unchanged because the default operator remains
`0` and all LSQ controls are inert unless operator `2` is explicitly selected.
GPU hard-errors if operator `2` is requested.

## Manufactured Tests

The static manufactured check uses the retained reduced triaxial particle
cloud. The key result is the linear pressure field:

| Field | Operator | Max acceleration | Mean error | Max error |
| --- | ---: | ---: | ---: | ---: |
| uniform `p=1000 Pa` | 1 | `0` | `0` | `0` |
| uniform `p=1000 Pa` | 2 | `0` | `0` | `0` |
| `p=1000 x` | 1 | `0.475 m/s2` | `0.177 m/s2` | `0.333 m/s2` |
| `p=1000 x` | 2 | `0.476 m/s2` | `1.43e-16 m/s2` | `8.36e-16 m/s2` |

Operator `2` therefore passes the intended manufactured consistency check for
uniform and linear pressure fields. Radial and center-bump fields remain
symmetry checks rather than exact reference tests; their net force stays near
zero, but the LSQ operator produces sharper accelerations than operator `1`.

## CPU Confinement-Only Runs

All three T4h CPU Release cases completed without exclusions or plasticity:

| Case | Operator | Stabilization | Code | Excluded | DtMin | Max PorePressRate | Max velocity | Center reversal |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| op1 interior baseline | 1 | off | `0` | `0` | `0` | `4.79e10 Pa/s` | `1.63 m/s` | `0.003821 s` |
| op2 LSQ interior | 2 | off | `0` | `0` | `0` | `5.04e10 Pa/s` | `2.40 m/s` | `0.003821 s` |
| op2 LSQ stabilized | 2 | relax+cap | `0` | `0` | `0` | `4.65e8 Pa/s` | `0.0172 m/s` | `0.004022 s` |

The unstabilized LSQ operator is not dynamically better than operator `1`; it
is slightly worse in peak `PorePressRate`, velocity, and final negative-pressure
count. The stabilized LSQ case is numerically calmer but still fails the gate:
center pressure reverses, local negative pressure persists, and final mean pore
pressure is still negative.

## LSQ Conditioning

The LSQ solve is not failing numerically in these cases. Diagnostics report:

- solved particles: `407`;
- fallback count: `0`;
- late condition proxy range: about `3.0` to `4.0`.

The remaining instability is not caused by LSQ matrix ill-conditioning. It is
caused by the explicit feedback coupling acting on a dynamically evolving
pressure field in the selected-confinement setup.

## Confinement Diagnostics

The selected confinement geometry remains well behaved:

- cap axial leakage remains `0`;
- lateral acceleration remains coherent during the confinement ramp;
- `Kplastic=0` for all cases;
- no excluded particles occur in T4h.

Thus the T4h blocker is not cap leakage, lateral selector failure, or plastic
yielding.

## Gate Decision

Operator `2` improves static linear-gradient consistency, but it does not pass
the selected-confinement pressure-feedback gate.

The confinement-only gate fails because:

- unstabilized LSQ does not reduce `PorePressRate` relative to operator `1`;
- stabilized LSQ still has center reversal and local negative pressure;
- the best case still requires limiter/cap support;
- no case provides validation-quality full-feedback confinement equilibrium.

Axial loading was not run. Reintroducing axial loading before a stable
confinement-only full-feedback state would repeat the failure pattern from
T4f.

## Recommendations

1. Keep operator `2` as an experimental diagnostic operator because it proves
   the manufactured linear-gradient consistency target.
2. Do not treat operator `2` as a triaxial validation setting.
3. Do not enter T5 DP or T6 MCC yet.
4. The next useful step is output enhancement and/or a deeper coupled-feedback
   formulation review. The current explicit acceleration feedback loop remains
   the blocker, not the LSQ conditioning.
5. GPU remains deferred for non-default feedback controls and operator `2`.
