# 06 Sainte-Monique

TODO scaffold for the Sainte-Monique landslide case.

This is a final-application target. It is not ready for validated runs in the
current CPU-only PR prototype and should remain scaffold-only during the pre-GPU
pass.

## Current Status

- Status: TODO scaffold only.
- `CaseSainteMonique_PR_TODO_Def.xml` is a placeholder.
- No GenCase or DualSPHysics run should be attempted in the current pass.
- Requires field geometry, material zoning, calibration, restart workflow, and
  GPU execution before meaningful smoke tests.

## Missing Features

- Field geometry / topography preparation.
- Material zoning and sensitive-clay calibration.
- Initial stress and pore pressure state construction.
- Boundary and drainage assumptions for field scale.
- GPU implementation and performance workflow.
- Checkpoint/restart workflow for long runs.
- Field-scale postprocessing and validation metrics.

## Minimum Future Smoke Standard

A first future smoke should be a reduced geometry sanity check:

- `code=0`;
- no NaN;
- checkpoint/restart workflow exercised;
- pressure, velocity, and plasticity fields written;
- runtime acceptable on GPU.
