# C08 plastic HG: scope and unresolved compatibility

Read-only feasibility conclusions, recorded2026-11-14. This note authorizes no
component, build, solver, decoder, GPU run, PRE, other psi or public-source edit.
All existing elastic/spin/rank/dt guards remain. Root will decide whether a
private prototype is justified after the pressure-feedback review.

## Primary reference

S. Zhang et al., *Computer Methods in Applied Mechanics and Engineering*440
(2025)117948, DOI[10.1016/j.cma.2025.117948](https://doi.org/10.1016/j.cma.2025.117948).
Local sources are `src/papers/u-pw/non-hourglass.md`, its original page005/006
images in `non_hourglass_assets`, and `src/papers/PDF/non-hourglass.pdf`.
Pages5–6, Eqs26–34, were read with the original page6 formula image.

Eqs26–28 integrate the difference between actual and linearly predicted pair
velocity. This is force memory, not instantaneous residual viscosity. Eqs32–34
put the return scale gamma_ij=(gamma_i+gamma_j)/2 **inside** that time integral.
The paper uses J2 plasticity. Its plastic xi=.2, elastic xi=4 and Wendland
h/dp1.3 are not a calibration for current DP saturated C08/H1.8.

For the current radial DP return, q_return/q_trial is a possible plastic
extension; it must come from the actual same-stage return, not accumulated
kappa. It is not claimed to be the paper's already validated DP formula.
Elastic zero-q and active apex/tension zero-q limits need explicit policies;
no division0/0 or silent clipping is justified. All original material/apex/
tension/history branches would remain intact.

## Existing implementation and time layers

Review used the actual schema2 `full_source.zip`, including
JSphHourglassCpu/Gpu and their Single/material callers. Current CPU Rate
builds a soil-only matched-LS residual, beta=xi*G*Vi*Vj*w, and integrates its
force rate in native-ID history. GPU Gather/Moments/Rates follows the same
model. Both explicitly reject plastic states and accumulated spin>=.01rad.

The existing four phases use endpoint trapezoidal history: PredictorForce
evaluates rate_n, PredictorUpdate advances history by half dt, CorrectorForce
adds history_half, and CorrectorUpdate evaluates the completed endpoint rate
and adds another half dt. Retaining that integration would require separately
stored gamma_n/gamma_n+1 at their matching endpoints. The material predictor
produces gamma_half while retaining kappa_n; gamma_half must not overwrite the
full material history or be substituted into the wrong rate layer. The whole
old HG history must not be rescaled by the latest gamma. Cache equality would
also have to include every new gamma input.

Producer locations are FunSoilMaterial.h Result.trial_q/returned_q and the
actual half/full calls in JSphCpu.cpp and JSphGpuSimple_ker.cu. Existing
ReturnMaterial adapters return status only. Any future private gamma capture
must preserve their original six-stress/kappa commits exactly.

## Two mathematical choices, neither selected

Merely multiplying the current Rate beta by spatially varying gamma_ij is
insufficient: the existing simplified force/work identity uses LS normal
equations with matching weights, so its cross terms would not automatically
cancel under the old LS weights.

One possible extension uses gamma-weighted HG-only LS moments and matching
pair beta. A different possible extension retains the original residual
projector P and implements the full adjoint terms in P^T D_gamma P. Either
can retain a frozen-geometry mechanical work identity when derived and
implemented consistently. They are not identical models, and gamma-weighted
LS is not the only possible choice or a literal reproduction of the paper's
gradient. The physical stress/volume velocity gradient need not be changed.
No choice is made here. Zero-weight/rank-deficient cases cannot be hidden
with a ridge or by relaxing existing necessary guards.

## Remaining scope gaps

The existing native-ID History is a bare vector, not a finite-rotation
objective memory. A zero-history rigid velocity field may be residual-free
while a nonzero old history still fails a superposed-rotation test. Rotating
each particle history independently may also alter net-force cancellation.
No new rotation/history model is selected, and the spin guard must not be
deleted to enable C08. A complete large-rotation release needs a deliberate
objective transport and changing-neighbour history policy.

Variable-J handling must retain the distinction between force history Q/M0
and actual acceleration, current Vi/Vj weights and current force-stage
inertia. Integrating acceleration and then applying another mass conversion
would be a different model. Changing J/gamma/geometry means a frozen-geometry
work identity is not a whole coupled energy or conservation theorem.

HG-off PRE followed by zero HG history at release would define a new
release-only stabilisation initial condition. It is not recovery of the
missing PRE HG history or an exact HG restart; gamma cannot be inferred from
the PRE's accumulated kappa. Original material/pressure/J histories remain.

HG acceleration is currently added before the dynamic Darcy rate. Therefore
its hydraulic feedback must be reviewed too. The rejected H1.2 instantaneous
residual-viscosity experiment is not a test of a plastic memory HG model and
cannot be transferred quantitatively to current H1.8. It does demonstrate
that mechanical dissipation alone does not establish coupled stability.

## Necessary evidence before physical use

Any later private candidate needs original elastic0ULP/OFF regressions;
translation, full affine and rigid-velocity null tests; nonzero-history
superposed rotation; constant and nonuniform-gamma work/net-force/torque
checks; correct half/full/native-ID sorting ownership; variable-J force and
inertia checks; original rank/dt guards; then same-stage Darcy-feedback
checks. Gamma=1 may retain the original literal elastic path. None of these
tests has been performed by this note, and no C08 physical window is admitted.

Existing resources support a bounded CPU feasibility component at modest
cost. They do not make a finite-rotation, plastic, coupled3s C08 implementation
a safe one-line extension. Public source, formal inputs and old evidence are
unchanged; no component/source authoring follows this note automatically.
