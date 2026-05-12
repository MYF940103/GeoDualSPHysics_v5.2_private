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
| Loading | Native spherical traction support not confirmed. | Audit native force/pressure route; likely blocker. |
| Drained boundary | Mode 0 not strict; mode 1 experimental; mode 2 CPU-only experimental. | CPU boundary decision needed before GPU. |
| Hydraulic gravity / elevation source | Classical Cryer has no gravity-driven elevation source, but current PR uses `HydraulicGravity` in both diffusion scaling and `LapZ`. | Audit whether a CPU-only no-elevation-source option is required. |
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

### C4-B: Strict Geometry XML Prototype

After C4-A, audit native spherical traction support before attempting a runnable
strict sphere. The existing strict sphere XML remains a draft until loading and
boundary are solved.

### C4-C: Boundary / Loading Source Development

Only if native routes are insufficient:

- design minimal CPU spherical traction support;
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
- native traction route is proven unavailable or insufficient;
- the `HydraulicGravity` / no-elevation-source representation is resolved;
- boundary strategy is selected for CPU.
