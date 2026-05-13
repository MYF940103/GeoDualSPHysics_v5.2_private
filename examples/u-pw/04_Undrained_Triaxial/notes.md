# Notes: Undrained Triaxial

## Current Purpose

`CaseUndrainedTriaxial_PR_Smoke_Def.xml` is a reduced smoke case for the CPU
u-pw PR implementation. It is intended to verify that a tiny native AccInput
axial load can be applied to a top material layer while pore-pressure fields and
stress outputs are written.

It is not a validated reproduction of the paper's triaxial results.

Under the full CPU pre-GPU gate, this case remains incomplete for strict
reproduction. The existing smoke proves that native AccInput, pore-pressure
fields, and stress outputs can run briefly; it does not prove that the paper's
triaxial loading path, confinement, material response, or stress-path outputs
are reproduced.

## Current Numerical Setup

- Mechanical body gravity is disabled.
- Hydraulic gravity is `(0,0,-9.81)` to keep the hydraulic head definition
  available.
- `PorePressureInit=1` initializes a hydrostatic baseline.
- Top drainage is delayed with `PorePressureTopDrainedStartTime=999`, so the
  short smoke remains undrained.
- Feedback uses:
  - `PorePressureFeedbackMode=1` (excess pressure)
  - `PorePressureFeedbackOperator=1` (difference-gradient)
- Stabilization uses:
  - `HydromechDampingXi=0.05`
  - `PorePressureShepard=1`
  - `PorePressureShepardMode=1`

## Loading

The top material layer uses `mkfluid=1` and is driven by DualSPHysics native
`accinput`. The current CSV is intentionally tiny:

```text
0.001 s -> LinearAccZ = -0.047619 m/s2
```

This corresponds to an extremely small compressive load-equivalent acceleration
and is only meant to exercise the coupled field plumbing.

## Missing for Strict Triaxial Reproduction

- Paper geometry and loading:
  - cylinder height `0.15 m`;
  - diameter `0.05 m`;
  - particle spacing `0.002 m`;
  - top vertical velocity `0.01 m/s`;
  - bottom fixed;
  - top/bottom free-slip;
  - lateral flexible confined boundary.
- Prescribed confining pressure / lateral stress boundary.
- Calibrated constitutive law. The paper uses MCC for the triaxial tests; the
  current Drucker-Prager path is an approximation.
- Validated stress-path postprocessing for `p'`, `q`, axial strain, and
  volumetric strain.
- Higher resolution and longer runtime, preferably after GPU porting.

Known paper triaxial cases:

- TU-L: `(pc)_0 = 200 kPa`, confining pressure / initial mean effective stress
  `150 kPa`.
- TU-M: `(pc)_0 = 200 kPa`, confining pressure `30 kPa`.
- TU-N: `(pc)_0 = 200 kPa`, confining pressure `200 kPa`.
- permeability `k=1e-8 m/s` for undrained behavior.

## Smoke Interpretation

The current smoke passes the strict/minimal CPU execution health check:

- GenCase code=0.
- DualSPHysics code=0.
- Excluded particles=0.
- Pore-pressure and stress fields are written.
- The tiny compressive load gives small positive excess pore pressure.
- `analyze_triaxial_smoke.py` produces `triaxial_smoke_summary.csv` with
  framewise `p'`, `q`, pore-pressure, velocity, and axial-strain proxy metrics.

Strict triaxial validation remains feature-blocked by loading/confinement,
stress-path postprocessing, and material-model choices. It is no longer a pure
TODO scaffold, but it still blocks strict paper-case completion unless those
items are implemented or explicitly deferred.

## T1 Baseline Notes

T1 starts the post-Cryer benchmark route:

`experiments/T1_UndrainedTriaxialBaseline/`

Design choices:

- `SoilConstitutiveModel=0` for a linear elastic u-pw smoke;
- `PorePressureBoundaryOperator=0`;
- `HydraulicElevationSource=0` with `HydraulicGravity=(0,0,-9.81)` for
  scaling only;
- `PorePressureInit=0`;
- top-layer native `accinput`, final `LinearAccZ=-0.5 m/s2`;
- no true confining pressure;
- no GPU run.

T1 CPU Release completed with `code=0`, `excluded=0`, four PART frames, no
NaN/Inf in the postprocessed fields, and `Kplastic=0`. The upper-middle
measurement region below the loading layer developed positive excess pore
pressure (`42.12 Pa` at the final frame). The geometric center remains almost
unloaded over this very short window, so T2 should improve loading duration,
measurement definitions, and stress-path extraction before any paper-level
comparison.

## T2 Zhao Flexible Confinement Audit Notes

The Zhao flexible confined boundary paper has been converted and reviewed under
`src/papers/u-p/`. The method applies an isotropic confining-pressure pair term
to the SPH momentum equation. The term cancels in the interior when kernel
support is complete and becomes an inward traction near a truncated free
surface.

Current branch status:

- CPU `FlexibleConfiningStress` already adds a stress-like pair contribution,
  so it is the right starting point for triaxial lateral confinement.
- The current term uses the existing kernel gradient in the CPU force loop; it
  does not yet use Zhao's renormalized gradient form.
- It targets all selected material particles by mk and does not yet compute
  the kernel-completeness index `f_i = sum_j (m_j/rho_j) W_ij`.
- It cannot yet distinguish the cylindrical lateral membrane from top/bottom
  caps except by manual mk design.

T3 should therefore be diagnostic-first:

1. add `f_i` summary/histogram output;
2. classify lateral/cap/edge/interior particles in a cylinder;
3. report radial confining acceleration and axial leakage;
4. only then enable optional near-boundary and lateral-only selectors;
5. keep GPU and MCC deferred.
