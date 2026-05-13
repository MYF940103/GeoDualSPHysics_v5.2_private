# T4g Feedback Formulation Audit Report

## Objective

T4g checks whether the selected-confinement triaxial instability is caused by a
basic pore-pressure feedback formulation error, a pressure-variable mismatch, a
bad operator choice, or feedback applied to unsuitable particle classes.

No DP, MCC, Cryer, GPU simulation, PR pressure-rate change, or axial validation
was introduced.

## Source Changes

T4g adds a default-off CPU class filter for feedback acceleration:

```xml
<parameter key="PorePressureFeedbackUseClassFilter" value="1" />
<parameter key="PorePressureFeedbackInteriorOnly" value="1" />
```

Additional optional switches can exclude caps, edge rings, or selected lateral
confinement targets. The filter only changes whether `a_fb` is added to `Acec`;
it does not alter the PR pressure update or stored pore pressure. The default
behavior is unchanged. GPU hard-errors for non-default feedback controls.

## Manufactured Feedback Tests

The static manufactured test uses the retained T4g cylinder particle cloud.

| Test | Operator 0 | Operator 1 |
| --- | --- | --- |
| uniform pressure | nonzero boundary response, max `38.53 m/s2` | exactly `0` |
| linear `p=1000 x` | not a clean gradient estimator | correct sign, max about `0.475 m/s2` |
| radial/center-bump fields | surface-force component remains | symmetric net force with pressure-gradient response |

Conclusion: operator 1 is the more physically consistent feedback operator for
internal pore-pressure acceleration. Operator 0 behaves like a stress-style
surface term and is not suitable as the primary triaxial feedback route.

## CPU Confinement-Only Variant Results

| Case | Result |
| --- | --- |
| feedback off | `code=0`, `excluded=0`, no DtMin, max `PorePressRate=2.11e7 Pa/s`, no reversal |
| operator 1 unfiltered | `code=0`, `excluded=164`, `256` DtMin, max `PorePressRate=1.30e13 Pa/s` |
| operator 0 unfiltered | `code=0`, `excluded=0`, `43` DtMin, max `PorePressRate=2.02e12 Pa/s`, reversal |
| operator 1 interior-only | `code=0`, `excluded=0`, no DtMin, max `PorePressRate=4.79e10 Pa/s`, reversal |
| operator 0 interior-only | `code=0`, `excluded=0`, no DtMin, max `PorePressRate=8.52e10 Pa/s`, reversal |
| operator 1 total-pressure interior-only | identical to operator 1 excess-pressure interior-only |

Class filtering is a major stability improvement relative to unfiltered full
feedback because it removes exclusions and DtMin bursts. It is not sufficient:
center pressure still reverses around `0.003821 s`, local negative pressures
remain, and max pressure-rate is still several orders above the feedback-off
reference.

## Total vs Excess Mode

Under the T4g triaxial convention `HydraulicElevationSource=0`, total and excess
pressure are identical. The T4g total/excess pair confirms this exactly. There
is no variable mismatch in this no-elevation setup.

## Double Counting

The current linear-elastic skeleton path stores skeleton stress in `Sigmac`.
Pore pressure is not written into `Sigmac`; feedback is the intended
`-grad(p_w)/rho` momentum contribution. T4g therefore does not prove direct
total/effective stress double counting. The failure is dynamic coupling:
explicit feedback acceleration creates a strong velocity/divergence/pressure
loop during selected confinement.

## Feedback by Class

The unfiltered failed case shows large feedback acceleration in the lateral and
cap/edge classes. Interior-only filtering applies feedback to `63` particles and
skips `344` particles. That removes the boundary-class acceleration, but the
remaining interior feedback acceleration still grows to about `1.72e4 m/s2` in
the final short-run diagnostics.

This suggests that class filtering addresses where the first amplification
appears, but not the underlying explicit feedback-loop stiffness.

## Gate Decision

T4g does not pass the confinement-only gate:

- no class-filtered case removes pressure reversal;
- no class-filtered case reaches feedback-off pressure-rate levels;
- operator 0 is not physically preferred;
- total/excess mode is not the issue;
- axial loading was not reintroduced.

The T4f cap/relax safety guard is still useful for preventing catastrophic
exclusion, but it is not a physical closure. T5 DP and T6 MCC remain deferred.

## Recommended Next Step

Proceed to T4h as a focused feedback formulation patch, not a loading or DP/MCC
task. The most useful next source task is to replace the explicit raw
difference-gradient feedback with a physically constrained feedback coupling
candidate, for example:

1. class-filtered operator 1 as the baseline scope;
2. corrected/renormalized pressure-gradient reconstruction for feedback only;
3. optional feedback under-relaxation tied to the mechanical time step;
4. a check that global feedback work does not inject unbounded kinetic energy;
5. retained diagnostic cap only as a safety guard.

Do not proceed to axial loading, DP, MCC, or GPU parity until a full-feedback
confinement-only case is stable without relying on a purely arbitrary cap.
