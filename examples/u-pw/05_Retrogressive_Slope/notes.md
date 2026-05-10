# Notes: Retrogressive Slope

Missing before meaningful reproduction:

- Sensitive clay / strain-softening material model or calibrated approximation.
- Large-deformation stability checks.
- Pore-pressure boundary and initial condition strategy.
- GPU implementation for meaningful run sizes.
- Postprocessing for retrogression distance, failure mechanism, pore pressure, velocity, and plasticity.

Current CPU PR prototype is useful only for tiny smoke tests, not production slope simulations.
