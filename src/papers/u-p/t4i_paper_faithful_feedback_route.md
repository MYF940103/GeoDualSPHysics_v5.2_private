# T4i Paper-Faithful Feedback Route

## Objective

This document compares candidate next routes for restoring paper fidelity in
the u-pw pore-pressure momentum coupling. It deliberately does not choose DP,
MCC, or limiter tuning.

## Route 1: Paper-Style Stress-Like Pore-Pressure Momentum Term

Concept:

```text
a_pw,i = sum_j m_j ((p_i+p_j)/(rho_i rho_j)) I . grad W_ij
```

This is closest to the u-pw implementation notes and structurally matches the
ordinary effective-stress divergence and Zhao confinement pair terms.

Relation to current source:

- current operator `0` is algebraically closest;
- current operator `0` is not enough because it is raw-gradient, separate from
  the main stress loop, and has no boundary pressure completion;
- T4g showed uniform-pressure free-surface spuriosity for operator `0`.

Needed to make this route meaningful:

- implement an opt-in paper-style operator that can use the same pair-loop and
  gradient convention as skeleton stress;
- test corrected/renormalized gradient as part of the route;
- add boundary or ghost/extrapolated pore-pressure states if free-surface
  uniform pressure should cancel;
- keep it CPU-only until it passes controlled gates.

## Route 2: Difference-Gradient Operator 1

Concept:

```text
a_pw,i ~= -grad(p_w)_i/rho_i
```

Strengths:

- exactly zero for uniform pressure in material-only clouds;
- sign and unit checks passed in T4g;
- avoids operator-0 free-surface spuriosity.

Weaknesses:

- not the SPH form written in the u-pw notes;
- still unstable in selected confinement;
- class filtering helps but is diagnostic, not a paper-derived final setting.

Route 2 is useful as a diagnostic baseline but should not be the paper-fidelity
mainline.

## Route 3: LSQ Operator 2

Concept:

```text
p_j - p_i ~= grad(p)_i dot (x_j-x_i)
a_pw,i = -grad(p)_i/rho_i
```

Strengths:

- best manufactured linear-gradient behavior;
- condition diagnostics are clean in T4h.

Weaknesses:

- not the paper-style symmetric pair form;
- dynamic selected-confinement behavior is not improved without limiter;
- confirms that pressure-gradient accuracy alone is not the main missing
  element.

Route 3 should remain an experimental diagnostic, not the next validation
route.

## Route 4: Total-Stress Coupling Redesign

Concept:

```text
sigma_total = sigma_effective - alpha p_w I
```

Then momentum uses only one stress-divergence path:

```text
div(sigma_total)
```

Strengths:

- closest to continuum total-stress mechanics;
- avoids a separate feedback acceleration pass;
- automatically puts pore pressure and skeleton stress in the same pair loop.

Risks:

- larger source change;
- must avoid writing pore pressure into persistent skeleton stress;
- requires careful sign convention and output labeling;
- still needs boundary-state treatment for truncated supports;
- may complicate constitutive updates if not implemented as a temporary
  momentum-only total stress.

## Recommendation

The recommended next route is a narrow CPU-only paper-style stress-like
coupling prototype, not another limiter:

```text
T4j = paper-style pore-pressure momentum coupling gate
```

The prototype should start as an opt-in route equivalent to a new operator or
momentum-coupling mode:

- use the symmetric `(p_i+p_j)` stress-like form;
- place it as close as possible to the existing stress-divergence pair term;
- document and test the sign convention against operator `0`;
- optionally support corrected/renormalized gradient in the same way as
  confinement;
- initially run controlled manufactured and small closed-support benchmarks,
  not a DP/MCC triaxial run.

Total-stress coupling should remain the next design candidate if the narrower
operator shows that same-loop stress-like coupling helps but the separate array
path is still too fragile.

## No-Go Criteria

Do not return to selected triaxial axial loading, DP, or MCC unless the next
paper-style route passes:

- uniform pressure no unintended acceleration under the intended boundary
  treatment;
- linear pressure sign/magnitude check;
- controlled confinement-only full-feedback gate without reversal;
- no DtMin burst or exclusions;
- no reliance on permanent acceleration caps.
