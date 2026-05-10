# Notes: Undrained Triaxial

## Status

This directory remains TODO-only. The placeholder XML intentionally does not
claim to be runnable or validated.

## Missing Before Strict Reproduction

- Axial strain or axial stress control.
- Confinement / lateral stress boundary.
- Stress-path output: `p'`, `q`, pore pressure, axial strain, volumetric strain.
- MCC may be required if the paper setup uses Modified Cam Clay.
- Current Drucker-Prager model can only be an approximation unless calibrated.

## Smoke Readiness

No GenCase or DualSPHysics run was executed in this pre-GPU pass. That is
intentional: geometry, loading control, and confinement are not yet specified.

A future minimal smoke test should use a very small strain increment, confirm
`code=0`, `excluded=0`, no NaN, correct pore-pressure sign, and a basic stress
path output. It should not attempt strict paper reproduction until the material
model and boundary/loading controls are fixed.
