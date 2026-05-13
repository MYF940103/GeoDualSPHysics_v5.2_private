# T4i Zhao Confinement Coupling Audit

## Objective

This audit checks whether the selected-confinement triaxial instability should
be treated as a feedback-gradient issue alone, or as a coupled inconsistency
between u-pw pore-pressure momentum coupling and Zhao-style flexible
confinement.

## Zhao Equation 51 Compatibility

Zhao's flexible confinement adds a stress-like pair term:

```text
a_i^conf = sum_j m_j (sigma_c,i + sigma_c,j)/(rho_i rho_j) grad W^R_ij
```

This is structurally similar to the stress-divergence pair form in the SPH
solid momentum equation. It is also structurally similar to the paper-style
u-pw pore-pressure momentum term from the implementation notes, except that
Zhao uses an imposed confining stress while the u-pw term uses pore pressure.

Therefore, the most paper-consistent combination would use compatible gradient
and pair-loop conventions for:

- skeleton effective-stress divergence;
- pore-pressure isotropic momentum contribution;
- flexible confinement isotropic stress contribution.

The current branch does not yet do this uniformly.

## Current Combination

Current T4/T4h selected-confinement tests use:

- flexible confinement as a stress-like pair term in the main CPU interaction
  loop;
- optional `f_i` and lateral selection for confinement;
- raw gradient by default, with opt-in renormalized confinement gradient from
  T4b;
- pore-pressure feedback as a separate acceleration pass;
- operator `1` or `2` rather than the paper-style symmetric stress-like
  pore-pressure pair term;
- optional class filters and limiters after the feedback candidate is computed.

This means the confinement term and pore-pressure term are not discretized as
two isotropic stress-like contributions in the same loop.

## Corrected Gradient Consistency

Zhao uses a renormalized gradient `grad W^R`. T4b showed that directly enabling
renormalized confinement in the current reduced cylinder increases lateral
acceleration and worsens the pressure feedback instability. This does not mean
renormalized gradients are wrong; it means the current reduced particle cloud,
initial state, and feedback loop are not ready for a paper-level corrected
gradient route without additional equilibration and boundary treatment.

A paper-faithful next route should decide the gradient convention once and test
it consistently across stress, confinement, and pore pressure.

## Initial Hydrostatic Confinement

Zhao's verification discussion warns that sudden confinement can launch stress
waves unless damping or equivalent initial hydrostatic stress is used. The
current selected-confinement tests start from zero skeleton stress and ramp
lateral confinement. T4d/T4e showed that the failure begins during
confinement-only equilibration, before axial loading.

This means the current full-feedback failure could be a combination of:

- non-equilibrated confinement stage;
- no initial hydrostatic effective stress;
- explicit pressure feedback responding to ramp-induced divergence;
- reduced cylinder boundary roughness and class selection;
- feedback operator mismatch.

It should not be attributed only to the sign or accuracy of operator `1/2`.

## f_i Selector And Feedback Class Filter

Zhao's `f_i` selector is designed for the confinement traction, not necessarily
for pore-pressure feedback. Applying the same near-boundary logic to feedback
is not paper-derived; it is a diagnostic stabilization idea introduced in T4g.

T4g showed that class filtering is useful because it removes cap/edge/lateral
feedback amplification. However, if the pore-pressure term is implemented as a
paper-style isotropic stress contribution, its boundary behavior should be
controlled through boundary state completion or total-stress consistency, not
through an arbitrary permanent class filter.

## Lateral-Only Selection Effect

Lateral-only confinement is correct for triaxial loading, but it changes the
mechanical response of the small cylinder cloud:

- only `112` selected lateral targets receive confinement;
- the center/interior pressure field responds through PR update and mechanical
  feedback;
- top/bottom/cap particles are excluded from confinement but still participate
  in the hydraulic and mechanical neighbor fields.

This makes the pressure feedback problem more sensitive to boundary handling
than a closed periodic or fully confined manufactured test.

## Why The Gate Fails Before Axial Loading

The T4d/T4e/T4f/T4g/T4h sequence indicates:

- confinement-only feedback-off is stable;
- full feedback reactivation destabilizes the sample;
- feedback class filtering removes exclusions and DtMin bursts but not
  pressure reversal;
- LSQ gradient accuracy does not fix the dynamic reversal;
- cap leakage remains zero and lateral confinement remains coherent.

The most plausible interpretation is that the current explicit feedback
acceleration is not discretely compatible with the staged flexible confinement
state and boundary support. Initial hydrostatic stress and a paper-style
same-loop pore-pressure stress term are both credible missing pieces.

## Audit Conclusion

Zhao compatibility argues against continuing limiter tuning. The next route
should restore fidelity in this order:

1. define whether pore pressure is a separate feedback acceleration or an
   isotropic stress-like term in the same momentum loop;
2. decide corrected-gradient handling consistently for stress, confinement,
   and pore pressure;
3. add or test initial hydrostatic confinement before axial loading;
4. only then return to selected-confinement full-feedback triaxial dynamics.
