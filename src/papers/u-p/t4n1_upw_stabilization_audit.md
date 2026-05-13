# T4n1 u-pw Stabilization Audit

## Scope

This note audits the local u-pw implementation notes, converted u-pw paper
text, and the drained/undrained SPH framework text for stabilization practices
relevant to the current triaxial confinement route.

No source code or simulations were run.

## Pore-Pressure Momentum Coupling

The u-pw notes describe the mixture momentum equation as a split
effective-stress plus pore-pressure contribution. The pore-pressure momentum
term is closer to a symmetric stress-like pair contribution than to a purely
postprocessed pressure-difference gradient:

```text
sum_j m_j * ((p_w,i + p_w,j) / (rho_i rho_j)) * I . grad W_ij
```

The paper-style interpretation is that pore pressure is part of the momentum
equation, not an arbitrary numerical feedback force added after the mechanics
are otherwise complete. Our current operator family has been useful for
diagnostics, but T4j showed that simply switching to a stress-pair operator
does not solve the triaxial dynamic instability.

## Corrected Gradient

The u-pw notes use a first-order corrected kernel gradient for key operators:

```text
tilde(grad W_ij) = L_i . grad W_ij
```

with a local correction matrix built from neighbor positions and kernel
gradients. The notes apply corrected gradients to divergence operators and
discuss corrected kernel use in the pore-pressure operators.

This implies our current raw-gradient pressure feedback and raw-gradient
confinement paths are not fully paper faithful. However, T4b showed that simply
using a renormalized gradient in the confinement force can amplify acceleration
on the current reduced cylinder. Corrected gradients remain reference
supported, but need careful equilibrium and magnitude diagnostics.

## Artificial Viscosity And Kinematic Damping

The u-pw paper reports that stabilization is necessary in coupled u-pw
formulations. In the 1D consolidation tests it compares artificial viscosity
and kinematic damping:

- artificial viscosity alone can stabilize but can add dissipation and error;
- kinematic damping improves agreement when used moderately;
- excessive damping overdamps early response;
- the PR formulation is preferred over PPE for later large-deformation
  simulations because it has fewer stability difficulties.

This directly supports damping during confinement equilibration and cautions
against treating an undamped, abruptly loaded SPH specimen as the reference
state.

## Staged Loading And Initial Equilibrium

The drained/undrained SPH framework uses properly initialized stress states in
geotechnical simulations. For the fault examples, the initial stress is
established first and then the loading simulation begins from that initialized
state. The text emphasizes that the initial stress state is crucial because
effective stress controls the constitutive response.

For triaxial simulations, the framework applies lateral confinement and top-cap
velocity loading and reports stress paths measured in a central region. It does
not provide a time-ramped selector-switch protocol, but it does support the
principle that the specimen should start from an initialized confined state
before axial loading.

## PR Stability Restrictions

The PR formulation has a pressure diffusion stability bound and the general
time step must satisfy both solid CFL and pore-pressure limits. The paper
emphasizes that stabilization choices and time stepping matter. The PPE route
has an additional gain/amplification issue; PR is less restrictive but not
free of stability concerns.

Our T4 feedback instability is not simply a PR update stability issue, because
feedback-off cases are much cleaner. Still, the u-pw notes suggest that
pressure update, momentum feedback, damping, and time-step control form a
package; validating one component in isolation is not enough.

## Is Feedback A Separate Numerical Item?

The original formulation treats pore pressure as part of the momentum balance.
In implementation, it may be computed in a separate source loop, but
conceptually it is not a user-tuned feedback controller. This matters for T4:
caps, relaxation, feedback scale below one, and class filters are diagnostics
unless they can be tied to a reference-supported boundary or operator.

## Why T4 May Be Missing The Full Stabilization Combination

The current T4 sequence has added several components one at a time:

- initial effective stress;
- flexible confinement;
- cap support;
- all-surface `f_i` confinement;
- delayed feedback;
- multiple feedback operators.

The literature suggests the stable workflow likely needs the right combination
at once:

- smooth specimen layout;
- initialized hydrostatic stress state;
- compatible all-surface confinement during isotropic staging;
- damping during equilibration;
- corrected-gradient operators;
- only then axial loading and feedback validation.

The current reduced cylinder, abrupt selector changes, raw-gradient coupling,
and incomplete equilibration can plausibly explain why full feedback remains
unstable even when individual pieces look reasonable.

## Direct Implications

For the next triaxial work:

1. Continue to treat PR full-feedback instability as a coupled staging/operator
   problem, not a sign/unit bug.
2. Use damping and an initialized stress state as reference-supported
   equilibration tools.
3. Prefer all-surface `f_i` confinement for isotropic staging.
4. Do not promote feedback caps, feedback scale below one, or arbitrary
   selector smoothing to validation settings.
5. Consider corrected gradients and smoother cylinder generation only after a
   clean equilibrium protocol is defined.
