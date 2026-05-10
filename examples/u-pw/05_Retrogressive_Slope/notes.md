# Notes: Retrogressive Slope

## Status

This directory is scaffold-only. The current CPU PR prototype is useful for
planning and very small smoke tests only, not production slope simulation.

## Missing Before Meaningful Reproduction

- Sensitive clay / strain-softening material model or calibrated approximation.
- Large-deformation stability checks.
- Pore-pressure boundary and initial condition strategy.
- Initial effective stress / pore pressure construction.
- GPU implementation for meaningful run sizes.
- Postprocessing for retrogression distance, failure mechanism, pore pressure,
  velocity, and plasticity.

## Readiness Decision

Do not block PR core GPU G1 on this case. Treat it as a post-GPU and
post-material-model reproduction target. No CPU run was executed in this
pre-GPU pass.
