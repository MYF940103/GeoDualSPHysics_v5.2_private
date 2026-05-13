# T4i Original u-pw Feedback Operator Audit

## Objective

T4i-B reopens the pore-pressure momentum coupling question from a paper-fidelity
angle. T4g/T4h showed that the current difference-gradient and LSQ feedback
routes are mathematically reasonable gradient estimators, but they do not pass
the selected-confinement triaxial gate. This audit asks a narrower question:
which current operator is closest to the original u-pw formulation and what is
missing before strict triaxial work can continue?

No source code, simulations, Cryer paths, DP, MCC, or GPU work are introduced in
this stage.

## Continuous Momentum Term

The local implementation notes for the u-pw paper write the momentum balance as:

```text
dv_s/dt = (1/rho) div(sigma') + (1/rho) grad(p_w) + g
```

The sign depends on the stress convention. In the notes, the effective-stress
term is written separately from the pore-pressure term. In the current branch,
`Sigmac` is treated as skeleton/effective stress; pore pressure is not stored in
`Sigmac`.

The important fidelity point is that the original formulation does not present
the pore-pressure momentum contribution as a later ad hoc limiter, gate, or
class-filtered add-on. It is part of the solid momentum equation.

## SPH Discrete Form In The Notes

The implementation notes give the effective-stress and pore-pressure
contributions as a pairwise stress-divergence-like expression:

```text
<dv_s/dt>_i =
  sum_j m_j (sigma'_i/rho_i^2 + sigma'_j/rho_j^2) . grad W_ij
  +
  sum_j m_j ((p_w,i + p_w,j)/(rho_i rho_j)) I . grad W_ij
  + g
```

This is a symmetric stress-like pore-pressure term. It is closer to treating
pore pressure as the isotropic part of a stress divergence than to fitting a
standalone local pressure gradient.

## Corrected Gradient Requirement

The same notes emphasize corrected or renormalized gradients for velocity
divergence and Laplacian operators. Zhao also uses a renormalized gradient
`grad W^R` in the confinement term. The paper-fidelity route therefore should
not be judged only by raw-kernel operator behavior.

Current branch status:

- stress divergence uses the existing raw pair gradient in the main CPU
  interaction loop;
- corrected-gradient PR diagnostics exist, but are not the default strict
  triaxial route;
- confinement has an opt-in Zhao-style corrected-gradient mode;
- feedback operator `0` uses a raw symmetric stress-like form in a separate pass;
- feedback operators `1` and `2` do not use the paper's symmetric
  pore-pressure stress form.

## Same Pairwise Momentum Loop

In the u-pw notes, the pore-pressure isotropic term appears next to the
effective-stress pair term. That suggests the paper-faithful implementation
should use the same neighbor pair, mass/density convention, gradient convention,
and boundary state treatment as the effective-stress divergence.

The current implementation separates pore pressure into a later feedback
acceleration pass:

1. main stress/confinement acceleration is computed in `InteractionForcesFluid`;
2. `ComputePorePressureAccel*` computes a candidate feedback acceleration;
3. `ApplyPorePressureFeedback` gates, filters, limits, and adds it to `Acec`;
4. damping is applied;
5. PR `PorePressRate` is computed.

This separation is useful diagnostically, but it is not the closest translation
of the paper's pairwise momentum equation.

## Current Operator Match

| Current operator | Form | Paper fidelity |
| --- | --- | --- |
| `0` symmetric stress-style | `-sum_j m_j (p_i+p_j)/(rho_i rho_j) grad W_ij` in current sign convention | Closest algebraic form to the notes |
| `1` difference-gradient | `-sum_j m_j (p_j-p_i)/(rho_i rho_j) grad W_ij` | Cleaner internal gradient estimator, but not the notes' symmetric stress-like term |
| `2` LSQ gradient | local least-squares `grad(p)` then `-grad(p)/rho` | Best manufactured linear-gradient behavior, but not the notes' pairwise stress-like discretization |

Operator `0` is therefore the closest current operator to the original u-pw
SPH discrete form. However, the current operator `0` is not a faithful final
implementation because it is raw-gradient, separate from the stress-divergence
loop, and lacks the boundary/MLS support needed to cancel uniform pore pressure
near a truncated free surface.

## Why Operator 1/2 May Change Stability

Operators `1` and `2` intentionally remove the uniform-pressure free-surface
response. That is attractive for a material-only free cylinder, but it also
changes the discrete momentum coupling relative to the paper. In the selected
triaxial cloud, this did not solve the dynamic problem:

- operator `1` interior-only still reverses with max `PorePressRate` about
  `4.79e10 Pa/s`;
- operator `2` improves manufactured linear-gradient consistency but still
  reaches about `5.04e10 Pa/s` without limiter.

This suggests that gradient accuracy alone is not the missing piece. The
coupling route, boundary completion, and initial-stress/staging assumptions
matter.

## Audit Answer

1. Pore pressure enters the original u-pw momentum equation as the isotropic
   pore-pressure part of the momentum balance, alongside effective stress.
2. The continuous term is written as `+(1/rho) grad(p_w)` in the notes, with
   sign interpreted through the stress convention.
3. The notes' SPH form is symmetric stress-like:
   `(p_i+p_j)/(rho_i rho_j) I . grad W_ij`.
4. The broader paper/Zhao context expects corrected or renormalized gradients,
   not only raw kernel gradients.
5. The term should be evaluated consistently with effective-stress divergence.
6. The original notes do not frame it as a separately limited feedback
   acceleration.
7. Current operator `0` is algebraically closest.
8. Operators `1` and `2` are cleaner gradient estimators but less faithful to
   the paper's pairwise stress-like form.
9. Replacing the paper-style term with difference-gradient or LSQ feedback may
   alter stability and boundary behavior; T4g/T4h show that doing so is not
   enough to stabilize selected confinement.
