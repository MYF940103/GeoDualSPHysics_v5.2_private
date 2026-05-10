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
