# T4j Feedback Fidelity Implementation Plan

## Decision

Recommended next task:

```text
T4j = CPU-only paper-style pore-pressure momentum coupling prototype
```

This corresponds primarily to Option A from the T4i decision set, with a
controlled benchmark gate before returning to triaxial. It should not be a DP
or MCC task.

## Why Option A First

T4i finds that the original u-pw SPH notes use a symmetric stress-like
pore-pressure momentum term:

```text
sum_j m_j ((p_i+p_j)/(rho_i rho_j)) I . grad W_ij
```

Current operator `0` is closest to this form, but it is not paper-faithful
enough:

- it is separate from the main stress-divergence loop;
- it uses raw gradient only;
- it lacks pore-pressure boundary/dummy/MLS completion;
- it produces uniform-pressure free-surface spuriosity on the material-only
  cylinder.

Operators `1` and `2` are useful diagnostics but are not the paper-style
discretization and did not stabilize the selected-confinement gate.

## Proposed Source Scope

Add an opt-in CPU-only route, for example one of:

```xml
<parameter key="PorePressureFeedbackOperator" value="3" />
```

or a clearer coupling flag:

```xml
<parameter key="PorePressureMomentumCouplingMode" value="paper_stress_pair" />
```

Recommended implementation properties:

- evaluate the pore-pressure isotropic term as a stress-like pair contribution;
- keep the default behavior unchanged;
- use the same pressure variable rules as existing feedback modes;
- keep it CPU-only initially, with GPU hard error for non-default mode;
- print clear diagnostics;
- do not apply acceleration caps as part of the validation route;
- expose corrected-gradient choice only as an opt-in submode.

## Controlled Gates Before Triaxial

T4j should not start with selected-confinement axial loading. It should use
small controlled cases:

1. static manufactured cloud:
   - uniform pressure;
   - linear pressure;
   - boundary-truncated cloud with and without boundary completion.
2. simple closed or periodic-like support test:
   - uniform pressure should not generate net acceleration.
3. selected-confinement-only reduced cylinder:
   - full feedback scale `1`;
   - no permanent limiter;
   - no pressure reversal;
   - no DtMin burst;
   - bounded `PorePressRate`.

Only after these pass should axial loading be restored.

## Boundary Completion Requirement

The main risk of Option A is the same one already seen in operator `0`:
uniform pressure on a truncated material-only support creates a boundary force.
This is not necessarily a contradiction of the paper; it indicates that the
paper-style stress-pair route needs a boundary treatment consistent with the
u-pw notes:

- dummy/boundary pore-pressure extrapolation;
- MLS boundary pore-pressure state;
- or a closed-support manufactured benchmark where cancellation is expected.

T4j should explicitly test this instead of hiding it with a class filter.

## Relation To Option B: Total-Stress Coupling

If Option A shows that same-loop stress-like pore-pressure coupling is helpful
but the separate feedback array remains fragile, Option B should follow:

```text
sigma_total_for_momentum = sigma_effective - p_w I
```

computed only for the momentum divergence, without overwriting persistent
skeleton stress. This is larger and should not be the first patch unless the
operator-3 route proves inadequate.

## Relation To Option C: Initial Hydrostatic Confinement

Initial hydrostatic effective stress is likely needed for strict triaxial
eventually. It should be implemented after or alongside a paper-faithful
momentum route, not as another way to mask an operator mismatch.

## Regression Tests

Required:

- CPU Release build;
- GPU Release build if shared parser/source changes;
- no GPU simulation;
- no Cryer cases;
- feedback-off T4 reference still unchanged;
- T4h operator `1/2` XMLs still parse;
- new paper-style route hard-errors on GPU if unsupported.

## No-Go Criteria

Do not proceed to DP/MCC or strict triaxial axial loading if:

- uniform-pressure behavior cannot be explained under the selected boundary
  treatment;
- selected-confinement-only full feedback still reverses without a cap;
- the route requires permanent feedback scale below `1`;
- boundary support completion is still absent.

## Expected Outcome

T4j should answer whether the original u-pw stress-like pore-pressure momentum
term can be made stable and interpretable in the reduced triaxial scaffold. If
not, the next decision should be either total-stress coupling or initial
hydrostatic confinement, not DP/MCC.
