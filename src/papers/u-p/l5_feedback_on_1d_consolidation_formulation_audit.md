# L5 Feedback-On 1D Consolidation Formulation Audit

## Objective

L5 is a coupling gate before moving toward landslide work. It asks whether the
existing pore-pressure feedback acceleration can be enabled in the 1D
consolidation initial-state route without producing the dynamic pressure
amplification seen in L2/L3b.

This is not a strict Terzaghi mechanical loading reproduction. It does not
generate the surcharge `q0` through a loading plate or surface traction.

## Pore Pressure in Momentum

The u-p formulation couples pore pressure back into momentum through a
pressure-gradient acceleration. In the current implementation this coupling is
separate from the PR pore-pressure-rate update:

- the soil stress update is computed first;
- the pore-pressure feedback acceleration is added to particle acceleration;
- the resulting velocity/divergence affects the later PR pressure-rate update.

Therefore feedback-on tests must monitor velocity, `DivVel`, and
`PorePressRate`, not only pressure magnitudes.

## Current Code Route

The CPU path computes feedback in `source/JSphCpuSingle.cpp` before
`ApplyPorePressureFeedback`. The relevant operators are:

- operator `0`: legacy symmetric pressure form;
- operator `1`: difference-gradient form;
- operator `2`: LSQ gradient, CPU-only;
- operator `3`: paper-gradient diagnostic, CPU-only.

For GPU, `source/JSphGpu.cpp` supports feedback only with operator `1`.
Operators `2` and `3` hard-error on GPU.

The operator recommended for 1D feedback-on diagnostics is:

```xml
<parameter key="PorePressureFeedback" value="1" />
<parameter key="PorePressureFeedbackMode" value="1" />
<parameter key="PorePressureFeedbackOperator" value="1" />
```

Mode `1` uses excess pore pressure. Operator `1` approximates
`-grad(p_w_excess)/rho` through pairwise pressure differences and is more
constant-pressure consistent near boundaries than the symmetric operator.

## Feedback-Off Versus Feedback-On

L3c/L4 are feedback-off Level-1 gates:

- initial excess pressure `p_w0=|q0|`;
- top drained boundary;
- bottom/lateral no-flux correction;
- PR pressure diffusion only;
- no momentum coupling from pore pressure.

L5 turns on the momentum coupling. That changes the validation question from
"does pressure diffuse through the hydraulic boundary model?" to "does this
pressure gradient create stable, bounded particle motion and a still-readable
pressure decay path?"

## Why L5 Is Not Strict Terzaghi Reproduction

Directly turning on feedback in the L3c initial-state route is mechanically
incomplete because:

- no top surcharge is applied through a plate or traction;
- no vertical total-stress-equivalent initializer exists in the current route;
- `InitialStressMode=0` leaves the skeleton without a compatible initial
  stress increment;
- the test starts from a pressure field that represents the instantaneous
  undrained analytical condition, not a generated mechanical load state.

This makes L5 a hydromechanical coupling stability gate. It can support a
reduced landslide entry decision, but it cannot replace a future strict
mechanical loading route.

## Mechanical State Requirements for Strict Validation

A stricter 1D consolidation reproduction needs at least one of:

- true surface traction or a force-controlled loading plate;
- a consistent total/effective stress and pore-pressure initializer;
- quasi-static mechanical equilibration before drainage;
- full feedback/stress coupling that does not create dynamic pressure waves.

The current `InitialStressMode=1` is isotropic and CPU-only. It is not a
vertical surcharge initializer, so it is not sufficient for strict L5.

## What L5 Can Validate

L5 can validate:

- feedback operator `1` stability in a 1D pressure-gradient setting;
- bounded velocity, `DivVel`, and `PorePressRate`;
- preservation of top drained and bottom no-flux behavior;
- qualitative pressure dissipation under feedback-on coupling;
- low-amplitude versus target-amplitude scaling.

L5 cannot validate:

- mechanical top-load generation;
- true surcharge-to-pore-pressure conversion;
- full Terzaghi storage response;
- damping or viscosity sensitivity;
- landslide readiness beyond a reduced coupling gate.
