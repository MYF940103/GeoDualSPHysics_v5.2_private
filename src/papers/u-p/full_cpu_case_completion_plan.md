# Full CPU Case Completion Plan Before GPU

## 1. New GPU-Entry Gate

GPU coding is blocked until all paper reproduction cases have reached CPU smoke readiness. The earlier gate of "PR core plus 01/02 readiness" is no longer sufficient.

Before GPU G1 starts:

- 01-06 must each have a case directory with README, notes, and a concrete XML plan.
- Every case must have a paper-parameter-oriented XML where parameters are known.
- Unknown paper values must be marked `TODO` rather than invented.
- Every case must either:
  - run a short CPU smoke test with GenCase `code=0`, DualSPHysics `code=0`, `excluded=0` or a documented coarse-grid exception, no NaN/crash, key fields written, and qualitatively plausible trend; or
  - be explicitly marked feature-blocked/data-blocked with the exact missing item and a plan to resolve it before GPU.
- TODO scaffold alone is not enough to declare GPU readiness.
- No CUDA, `JSphGpu*`, `JCellDivGpu*`, or `.cu` work should start until this full CPU case gate is revisited and passed.

## 2. Current Case Status

| Case | Current state | CPU smoke status | Gate status |
| --- | --- | --- | --- |
| 01 1D consolidation / pressure-only | Runnable pressure-only baseline; SW3h result archived as diagnostic. | Short pressure-only smoke passed. | Partially complete; remains regression anchor. |
| 02 Self-weight consolidation | Formal Scenario 1 Stage A/B and Scenario 2 smoke scaffolds. | Short Stage A/B and Scenario 2 smoke passed. | Complete for current smoke scope. |
| 03 Cryer | TODO scaffold only. | Not runnable yet. | Not complete. |
| 04 Undrained triaxial | TODO scaffold only. | Not runnable yet. | Not complete. |
| 05 Retrogressive slope | TODO scaffold only. | Not runnable yet. | Not complete. |
| 06 Sainte-Monique | TODO scaffold only. | Not runnable yet; likely data-blocked. | Not complete. |

## 3. Missing Features by Case

### 01 1D Consolidation

- No blocker for pressure-only smoke.
- Strict external-load Terzaghi still needs a stable loading strategy and may need better traction/loading plate support, but this is not required for the current pressure-only anchor.

### 02 Self-Weight Consolidation

- No blocker for short CPU smoke.
- Long-time tuning and strict curves are deferred.
- Boundary ghost and corrected-gradient diagnostics remain non-production.

### 03 Cryer Problem

- Paper geometry and exact benchmark parameters must be captured.
- Need a reduced CPU smoke geometry if full 3D sphere is too heavy.
- Strict drained boundary likely needs pore-pressure boundary ghost/MLS or a documented simplified boundary for smoke.
- Analytical center-pressure postprocessing needed for later, not for first smoke.

### 04 Undrained Triaxial

- Need minimal axial loading/control route using native DualSPHysics mechanisms.
- Need confinement/lateral stress approximation for smoke.
- Strict matching may need MCC; current DP can only be an approximate smoke.
- Need stress-path postprocessing from `Sigma_kk`/`Sigma_ij` if no direct `p'`/`q` fields exist.

### 05 Retrogressive Slope

- Strict reproduction needs sensitive clay / strain-softening and material zoning.
- Reduced CPU smoke can use DP + u-pw with coarse geometry for no-crash and output verification.
- Need qualitative slope geometry, initial pore pressure, and boundary assumptions from notes.

### 06 Sainte-Monique

- Field data/topography/material zoning may be unavailable.
- If data are missing, create a reduced placeholder smoke and `data/README.md` documenting the data block.
- Strict reproduction requires calibration and checkpoint/restart workflow.

## 4. Recommended Execution Order

1. 03 Cryer: extract known paper parameters, create reduced PR smoke XML, run short smoke or record exact feature block.
2. 04 Undrained triaxial: create approximate DP u-pw smoke using native loading, add stress-path analysis script, run short smoke or record exact feature block.
3. 05 Retrogressive slope: create reduced qualitative DP/u-pw smoke, run short geometry/field-output smoke or record feature block.
4. 06 Sainte-Monique: create reduced field scaffold or data-blocked workflow, run only if reduced geometry is available.
5. Update global matrix and interface cleanup notes.
6. Reassess GPU entry.

## 5. GPU Block Statement

GPU coding is blocked until all CPU smoke cases are complete or explicitly resolved as data-blocked/feature-blocked with an accepted CPU-side plan. Passing 01/02 alone is not sufficient.

The next GPU step, when eventually allowed, remains limited to passive `PorePressg` only unless a later plan expands the scope.
