# Cryer C4 Implementation Decision

Date: 2026-05-12

## C3-B Outcome

C3-B establishes the strict route but does not claim reproduction. The clean
paper formula has been transcribed from the PDF, the strict geometry route is
defined as a true 3D sphere, and the main remaining blockers are loading and
curved drained hydraulic boundary support.

## Decision Table

| Item | Current status | C4 implication |
|---|---|---|
| Analytical reference | C4-A script implemented and self-checked; not yet validated against digitized Figure 7B. | Use generated CSVs for future postprocessing, but still collect/check Figure 7B data. |
| Geometry | True 3D sphere recommended. | Prepare strict sphere XML prototype after reference script. |
| Loading | Native spherical traction support not found. C4-B2 rejects `AccInput` patchwise surrogate and selects flexible confining stress as the strict loading route. | Implement CPU-first flexible confining stress before any strict Cryer run. |
| Drained boundary | Mode 0 not strict; mode 1 experimental; mode 2 CPU-only experimental. | CPU boundary decision needed before GPU. |
| Hydraulic gravity / elevation source | Classical Cryer has no gravity-driven elevation source, but current PR uses `HydraulicGravity` in both diffusion scaling and `LapZ`. | Audit whether a CPU-only no-elevation-source option is required. |
| Constitutive skeleton | E1 added `SoilConstitutiveModel=0` for linear elasticity. | Strict Cryer XML drafts should use model `0`; DP remains default for existing cases. |
| Center postprocessing | Design complete; no strict script yet. | Implement after reference CSV schema is fixed. |
| GPU | Not first priority. | Wait until CPU strict setup is credible. |

## Recommended C4 Path

### C4-A: Strict Reference Script First

Status: completed as
`examples/u-pw/03_Cryer_Problem/strict_reproduction_plan/cryer_reference_solution.py`.

The script now:

- solve roots of `(1 - eta xi^2 / 2) tan(xi) = xi`;
- generate reference CSV curves for all four Poisson ratios;
- run convergence checks;
- generate a Figure 7B-style reference-only plot;
- compare against digitized or manually extracted Figure 7B points if available.

The next action is not another reference-script task unless Figure 7B data is
provided. It is C4-B traction-route audit.

### C4-B: Spherical Traction Route Audit

Status: completed as a source/XML audit. No simulation was run.

C4-B found no existing native XML route that maps uniform pressure `p0` to
per-particle inward radial surface forces on a spherical exterior. `AccInput`,
floating total forces, and prescribed motion are not strict substitutes.

The recommended next loading implementation, if strict Cryer proceeds, is a
CPU-first generic radial/spherical traction block with explicit area weighting
and force-symmetry diagnostics. The strict sphere XML remains a draft until
loading and boundary are solved.

### C4-B2: Flexible Confining Stress Route

Status: completed as a design/source audit. No source was changed and no
simulation was run.

C4-B2 formally rejects the `AccInput` patchwise spherical-loading surrogate.
Even with many marker patches and external CSV files, it would remain a
patchwise shell body-force equivalent, not a continuous all-around pressure
traction.

The selected loading route is the flexible confining stress method described in
the drained/undrained SPH framework paper's triaxial section. A compressive
isotropic stress tensor is added to the mechanical momentum summation. Kernel
symmetry cancels the contribution inside the specimen, while free-surface
truncation leaves an effective confining pressure on the exterior. This avoids
explicit surface-particle detection, normal reconstruction, and area weighting
in the first implementation.

The next loading task should be C4-B3:

- CPU-first implementation;
- default off XML switch;
- no-load regression;
- static sphere sign/symmetry diagnostics;
- hard error on GPU while unsupported.

### C4-C: Boundary / Loading Source Development

Only if native routes are insufficient:

- implement and validate CPU flexible confining stress support;
- design CPU curved drained boundary support;
- if needed, add a CPU-only Cryer/no-elevation hydraulic option that preserves
  the diffusion coefficient but removes the `LapZ` source;
- avoid corrected-gradient production;
- avoid GPU until CPU behavior is clear.

### C4-D: Reduced Fallback

If strict loading or boundary support is blocked, keep the reduced baseline as
a launch workflow and record Cryer strict reproduction as blocked.

## User Input That Would Help

The next step would be faster with one of:

- clean PDF screenshot/crop of Equations (46)-(47) and Figure 7B;
- digitized Figure 7B data;
- confirmation of the intended physical sphere radius `a`;
- confirmation that `p0=10 kPa` is acceptable if no paper-specific `p0` is
  found.

## Stop/Proceed Criteria

Proceed to source changes only after:

- reference curves pass convergence and figure-level checks;
- Figure 7B digitization is available or the lack of digitized data is accepted
  as a documented limitation;
- strict sphere geometry is accepted;
- flexible confining stress CPU diagnostics pass;
- the `HydraulicGravity` / no-elevation-source representation is resolved;
- boundary strategy is selected for CPU.
