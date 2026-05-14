# TINT1 Pore-Pressure Time-Integration Audit

TINT1 is a source-audit and design-only package. It does not contain new
GenCase, CPU, GPU, or PartVTK runs.

The audit found that `PorePressRate` is computed inside the interaction stage
and `PorePress` is updated explicitly before the mechanical Verlet update or
Symplectic corrector. Feedback acceleration uses the pressure available during
interaction, not the pressure just produced by the scalar update.

No `PorePressureTimeIntegrationMode` source patch was implemented in TINT1.
The recommended next step is a separate CPU-only TINT2 experiment with an
opt-in end-of-step or operator-split pore-pressure update mode.

