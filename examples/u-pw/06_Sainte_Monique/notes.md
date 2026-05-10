# Notes: Sainte-Monique

## Status

This directory should remain scaffold-only until the retrogressive slope
benchmark is stable and the GPU PR path is available.

## Missing Before Reproduction

- Field geometry / topography preparation.
- Material zoning.
- Sensitive clay calibration.
- Initial stress and pore pressure state construction.
- GPU implementation and performance workflow.
- Checkpoint/restart workflow for long runs.
- Field-scale postprocessing and validation metrics.

## Readiness Decision

Do not block PR core GPU G1 on this case. It is a final application target for a
later branch or later project stage. No CPU run was executed in this pre-GPU
pass.
