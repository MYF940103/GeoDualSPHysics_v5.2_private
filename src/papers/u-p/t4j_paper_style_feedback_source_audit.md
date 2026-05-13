# T4j Paper-Style Feedback Source Audit

## Objective

T4j adds a CPU-only paper-style pore-pressure momentum prototype for the
selected-confinement triaxial route. The target form follows the u-pw
implementation-note style isotropic pair term:

```text
a_i^pw = sum_j m_j * (p_i + p_j)/(rho_i rho_j) * I . grad W_ij
```

This is intentionally separate from the T4g/T4h pressure-gradient feedback
operators:

- operator `1`: difference-gradient `-grad(p_w)/rho`;
- operator `2`: LSQ pressure-gradient `-grad(p_w)/rho`.

## Source Insertion

The new operator is exposed as:

```xml
<parameter key="PorePressureFeedbackOperator" value="3" />
```

Source changes:

- `source/JSph.h`: extended the operator comment to include operator `3`.
- `source/JSph.cpp`: parser accepts operator `3`, prints
  `PaperStyleStressPair`, and hard-errors on GPU when operator `2` or `3` is
  requested.
- `source/JSphCpu.h`: declares `ComputePorePressureAccelPaper`.
- `source/JSphCpu.cpp`: implements `ComputePorePressureAccelPaperT`.
- `source/JSphCpuSingle.cpp`: routes operator `3` into the existing feedback
  application, class filter, gating, limiter, and diagnostics path.

## Numerical Form

The operator computes, for each material particle:

```text
p_i^* = PorePress_i                  (mode 0)
p_i^* = PorePress_i - p_hydro_i      (mode 1)

a_i^pw = sum_j MassFluid * (p_i^* + p_j^*)/(rho_i rho_j) grad W_ij
```

The sign is chosen to match the paper-style stress-pair expression and the
existing stress-divergence / flexible-confinement pair convention in
`InteractionForcesFluid`. This makes operator `3` different from the legacy
operator `0`, which uses the same symmetric pressure pair but the opposite sign
in the older feedback convention.

## Relationship To Effective-Stress Divergence

Operator `3` is not written into `Sigmac` and does not change the PR pressure
update. It remains a feedback acceleration candidate that is later filtered,
scaled, relaxed, or capped by the existing `ApplyPorePressureFeedback` path.

The implementation uses the same raw kernel-gradient form and mass/density
convention as the skeleton stress-divergence pair term, but it is still a
separate CPU pass rather than being inserted directly into the
`InteractionForcesFluid` stress-divergence inner loop. A fully paper-faithful
implementation would place pore pressure next to the skeleton stress pair, or
would move to a carefully audited total-stress route.

## Remaining Gaps

- Raw gradient only; no corrected/renormalized pressure-stress gradient.
- Separate feedback pass, not the exact same loop as `Sigmac` divergence.
- No boundary pressure completion, dummy state, or MLS pressure completion.
- Uniform pressure on a free-surface cloud can create a surface response, as
  expected for a stress-like pair term with truncated support.
- GPU support is intentionally absent.

## Interpretation

Operator `3` is the narrow CPU prototype requested for the paper-style
stress-pair idea. It is closer to the u-pw notes than operators `1/2` in
algebraic form, but it is still not the final paper-fidelity implementation
because the boundary-completion and same-loop/total-stress questions remain
open.
