# L5 Feedback-On 1D Consolidation Design

## Route 1: L3c Initial Pressure Plus Feedback On

Configuration:

```xml
PorePressureInit=3
PorePressureExcessAmp=1000 or 10000
PorePressureFeedback=1
PorePressureFeedbackMode=1
PorePressureFeedbackOperator=1
InitialStressMode=0
MechanicalTopLoad=0
```

Advantages:

- no source patch;
- CPU-first and GPU-compatible after CPU stability;
- isolates feedback coupling from mechanical load generation;
- directly compares to L3c/L4 feedback-off behavior.

Limitations:

- mechanically inconsistent as a strict Terzaghi reproduction;
- does not generate `p_w0` from `q0`;
- cannot validate the loading stage.

This is the recommended L5 diagnostic gate.

## Route 2: Initial Pressure Plus Compatible Stress State

Configuration:

- `p_w0=|q0|`;
- compatible effective/total stress state;
- no dynamic top force;
- feedback on.

Advantages:

- closer to the Terzaghi initial-value mechanics;
- could reduce spurious feedback acceleration from an inconsistent skeleton
  stress state.

Limitations:

- current source only clearly supports isotropic initial effective stress;
- a vertical surcharge or total-stress-equivalent initializer is not yet
  available;
- should be designed as L5b if Route 1 is stable but still not strict enough.

## Route 3: True Quasi-Static Mechanical Top Load

Configuration:

- force-controlled loading plate or true surface traction;
- quasi-static equilibration;
- feedback and stress coupling after a stable loading state exists.

Advantages:

- closest to strict mechanical top-surcharge generation.

Limitations:

- L3b direct force-on-material route showed strong dynamic pressure peaks;
- source/design risk is higher;
- should remain deferred in this stage.

## L5 Cases

The L5 package uses two CPU-first cases:

1. Low amplitude: `p_w0=1 kPa`.
2. Target amplitude: `p_w0=10 kPa`.

GPU target-amplitude parity is allowed only if the CPU target case is stable.

## Pass Criteria

The feedback-on gate passes only if:

- `code=0`;
- `excluded=0`;
- no DtMin burst;
- no NaN/Inf;
- pore pressure remains bounded;
- peak excess remains far below the L2/L3b `~6e5 Pa` dynamic peak;
- velocity, `DivVel`, and `PorePressRate` remain bounded;
- top drained residual stays small;
- bottom no-flux proxy stays small;
- pressure decay remains qualitatively Terzaghi-like;
- low-amplitude and target-amplitude cases scale reasonably.

## Interpretation Policy

Even if L5 is stable, report it as a feedback-on coupling gate. Do not call it
strict Terzaghi reproduction. A future strict route still needs L5b/L5d-style
consistent stress initialization or true mechanical loading.
