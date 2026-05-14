# TINT1 Pore-Pressure Time-Integration Design

Date: 2026-05-14

## Design Goal

The goal is to identify a safer way to embed PR pore-pressure evolution in the
existing Verlet/Symplectic mechanics without changing the PR governing
equation. TINT1 preserves the current default behavior and does not implement
a new mode.

## Variant 0: Current Implementation

Current route:

```text
Interaction_Forces computes DivVel/LapP/LapZ/feedback/rate
PorePress += rate * dt
mechanical step or corrector follows
```

Strengths:

- already works for L3c/L4 diffusion gates;
- CPU/GPU broad placement is aligned;
- first-order explicit diffusion is simple and easy to reason about.

Risks:

- not time-centered with Verlet/Symplectic mechanics;
- Symplectic has no pore-pressure predictor;
- feedback uses old pressure while pressure is updated before the corrector;
- stronger boundary operators can amplify explicit boundary errors.

## Variant 1: End-of-Step Scalar Update

Route:

```text
Interaction_Forces computes rate from current stage
mechanics advances velocity/position/stress
PorePress += rate * dt at end of the step
apply drained/no-flux clamps after pressure update
```

Expected benefits:

- treats pore pressure more like an internal variable committed at step end;
- reduces the confusing state where pressure is updated before the mechanical
  corrector but not used by its acceleration.

Risks:

- the rate still comes from the old/pre-corrector state unless recomputed;
- post-update boundary clamps must be relocated consistently on CPU and GPU;
- source change touches both step functions.

Implementation complexity: moderate.

## Variant 2: Symplectic Predictor-Corrector Pressure Update

Route:

```text
p^{n+1/2} = p^n + 0.5 dt rate^n
recompute rate at predicted state
p^{n+1} = p^n + dt rate^{n+1/2 or corrected}
```

Expected benefits:

- most consistent with Symplectic mechanics;
- can reduce pressure/velocity phase lag.

Risks:

- requires new pressure predictor arrays;
- requires recomputing PR diagnostics or adding a pressure-specific
  interaction path;
- higher CPU/GPU implementation cost;
- more opportunities for boundary clamp ordering bugs.

Implementation complexity: high.

## Variant 3: Density-Like Update

Route:

Treat `PorePress` similarly to `Rhop`, using the same stage where `Arc` and
`Velrhop` are updated.

Expected benefits:

- aligns pressure with divergence-driven volumetric update;
- conceptually simple for the `-DivVel` term.

Risks:

- the diffusion term depends on `PorePress` and boundary state, which density
  does not;
- stress/feedback still need a pressure time-layer policy;
- may overfit the volumetric term and under-handle diffusion.

Implementation complexity: moderate to high.

## Variant 4: Feedback-Lagged Update

Route:

Keep the explicit pressure update, but make the lag explicit:

```text
mechanics uses p^n feedback
pressure updates to p^{n+1}
next step uses p^{n+1}
```

This is close to current behavior, but documentation and diagnostics would
make it explicit. It could also avoid applying post-update clamps before a
mechanical corrector.

Expected benefits:

- clarifies the split;
- lower risk than a full predictor-corrector pressure scheme.

Risks:

- does not fix explicit boundary overshoot by itself;
- still first-order coupled.

Implementation complexity: low to moderate.

## Variant 5: Operator-Splitting Route

Route:

```text
1. mechanics step with old pressure feedback
2. recompute or reuse hydraulic operators on corrected state
3. update pressure
4. next step uses new pressure for feedback
```

Expected benefits:

- physically clear split: mechanics then hydraulic diffusion/storage;
- avoids updating pressure before the same mechanical corrector;
- good candidate for a CPU-only opt-in diagnostic.

Risks:

- if rate is not recomputed after the mechanical step, benefits are limited;
- recomputation requires an extra neighbor pass;
- GPU parity requires additional kernels or call restructuring.

Implementation complexity: moderate if rate is reused, high if recomputed.

## Recommended Next Experiment

Do not implement a TINT1 source patch yet. The least ambiguous next source
experiment should be a TINT2 CPU-only opt-in operator-splitting mode:

```text
PorePressureTimeIntegrationMode=1
```

Proposed behavior:

- default `0` remains current behavior;
- mode `1` updates pressure at end of step/corrector using the already computed
  rate;
- mode `2` is reserved for recomputed end-of-step hydraulic operators;
- GPU hard-errors for nonzero modes until ported.

This should be tested first on:

- L3c feedback-off, operator `1`;
- L5 feedback-on, operator `1`;
- BND1 generalized mode `2` feedback-off;
- BND1 generalized mode `2` feedback-on only after the first three cases pass.

## Diagnostics Needed

Before and after any source experiment, the following diagnostics should be
available or reconstructed from existing output:

- `PorePress` min/max before and after update;
- `PorePressRate` maxAbs;
- `DivVel` maxAbs;
- velocity max;
- feedback acceleration max/mean;
- top drained residual;
- bottom/lateral no-flux proxy;
- clamp amount if available;
- Shepard correction amount if enabled;
- stage label for the update.

If existing CSV is insufficient, add an opt-in
`SavePorePressureTimeStageDiagnostics=1` in TINT2 rather than mixing
instrumentation into the current audit.

