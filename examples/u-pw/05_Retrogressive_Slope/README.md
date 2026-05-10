# 05 Retrogressive Slope

TODO scaffold for the retrogressive slope / landslide benchmark in the u-pw PR formulation.

This case remains scaffold-only during the CPU pre-GPU pass. It should not be
used for production runs with the current CPU prototype.

## Current Status

- Status: TODO scaffold only.
- `CaseRetrogressiveSlope_PR_TODO_Def.xml` is a placeholder.
- No GenCase or DualSPHysics run should be attempted in the current pass.
- Meaningful runs require GPU implementation and a material-model decision.

## Missing Features

- Sensitive clay / strain-softening material model or calibrated approximation.
- Large-deformation stability checks.
- Pore-pressure boundary and initial-condition strategy.
- Initial stress and pore pressure construction for the slope.
- GPU implementation for useful run sizes.
- Postprocessing for retrogression distance, failure mechanism, pore pressure,
  velocity, and plasticity.

## Minimum Future Smoke Standard

A future coarse smoke should verify only basic execution health:

- `code=0`;
- `excluded=0` initially;
- no NaN;
- pressure, velocity, and plasticity fields written;
- qualitative deformation direction plausible.

Strict retrogression behavior is deferred until GPU and material-model work are
available.
