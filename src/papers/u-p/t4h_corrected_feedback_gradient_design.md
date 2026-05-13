# T4h Corrected Feedback Gradient Design

## Objective

T4h targets only the momentum-side pore-pressure feedback acceleration used by
the reduced selected-confinement triaxial tests. It does not modify the PR
pressure update, the soil constitutive model, Cryer boundary paths, flexible
confinement selection, or the axial-loading schedule.

The T4g baseline established that `PorePressureFeedbackOperator=1` is the
physically preferred existing feedback route: it gives zero acceleration for a
uniform pressure field and gives the expected down-gradient sign for a linear
pressure field. It also showed that class filtering removes the largest
boundary-class amplification, but the interior-only confinement case still
reverses and reaches about `4.79e10 Pa/s` in `PorePressRate`.

## Candidate Operators

### Option 1: Renormalized Kernel Gradient

This route would reuse the same idea as the Zhao confinement gradient:

```text
L_i = -sum_j V_j r_ij tensor grad W_ij
grad W^R_ij = L_i^-1 grad W_ij
```

It is attractive because it improves linear-field consistency while staying
close to the existing SPH pair loop. The risk is already visible in T4b:
renormalization can amplify forces in this small cylinder cloud. A direct
renormalized feedback gradient may therefore make the explicit u-pw feedback
loop stiffer rather than smoother.

### Option 2: Local LSQ Pressure Gradient

This route reconstructs the pressure gradient directly:

```text
p_j - p_i ~= g_i dot (x_j - x_i)
A_i g_i = b_i
A_i = sum_j w_j r_ij tensor r_ij
b_i = sum_j w_j (p_j - p_i) r_ij
a_fb,i = -g_i / rho_i
```

The weights are local kernel-volume weights. Under
`HydraulicElevationSource=0`, total and excess pore pressure are identical, but
the implementation still respects `PorePressureFeedbackMode`.

Advantages:

- exact for a well-conditioned local linear pressure field;
- condition number diagnostics are natural;
- fallback can be explicit and counted;
- the operator changes only the feedback acceleration discretization.

Risks:

- an exact gradient can be more aggressive dynamically than the diff-gradient
  operator;
- class filtering reduces the active set and may expose local oscillatory
  pressure fields;
- explicit feedback can still form a velocity-divergence-pressure loop.

### Option 3: Class-Filtered Smoothed Gradient

This route would retain operator 1 but smooth the pressure field or the
gradient, and use the T4g class filter to exclude cap, edge, and confinement
target classes. It is the least invasive numerically, but it does not address
the main consistency defect seen in the manufactured linear-gradient test.

## Selected Route

T4h implements Option 2 as a new CPU-only experimental mode:

```xml
<parameter key="PorePressureFeedbackOperator" value="2" />
```

The old defaults are unchanged. Operator `0` and `1` keep their previous
behavior. Operator `2` is rejected on GPU.

Optional LSQ controls:

```xml
<parameter key="PorePressureFeedbackLSQRadiusFactor" value="1" />
<parameter key="PorePressureFeedbackLSQConditionLimit" value="1000000000000" />
<parameter key="PorePressureFeedbackLSQFallback" value="0" />
```

`PorePressureFeedbackLSQFallback=0` falls back to operator `1` when the local
LSQ system is insufficient or ill-conditioned. `1` sets feedback to zero for
that particle. Fallback is reported in diagnostics and is not silent.

## Diagnostics

Operator `2` reports:

- solved LSQ particle count;
- fallback count;
- condition proxy min, mean, and max;
- the existing feedback raw/used acceleration metrics;
- class-filtered acceleration metrics when class filtering is enabled.

The pressure update remains untouched; these diagnostics describe only the
feedback acceleration applied to the mechanical momentum equation.

## Gate Definition

The T4h gate is confinement-only, linear elastic, selected lateral confinement,
interior-only feedback, no axial loading, and CPU Release. A useful operator
must satisfy:

- `code=0`, `excluded=0`, `Kplastic=0`;
- no DtMin burst;
- no pressure reversal;
- no strong negative pressure;
- lower `PorePressRate` than the T4g operator-1 interior-only baseline;
- controlled velocity;
- coherent lateral confinement and zero cap leakage.

If this confinement-only gate fails, axial loading and DP/MCC remain deferred.
