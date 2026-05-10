# Production Pore-Pressure Boundary Treatment Design

Date: 2026-05-11

Milestone: BND-1 from `full_cpu_implementation_backlog.md`

This document selects the next design direction for pore-pressure boundary
treatment. It does not authorize production source changes by itself.

## Why This Is the Next CPU Milestone

The full paper audit shows that boundary treatment blocks several strict
reproduction cases:

- 1D Terzaghi coupled loading needs drained top and no-flux bottom/lateral
  boundaries beyond layer correction.
- Self-weight Scenario 1/2 can run as 1D smokes, but strict comparison still
  relies on boundary consistency.
- Cryer needs a drained curved/spherical boundary and center-pressure response.
- Triaxial and slope cases need undrained/no-flux sides and eventually complex
  non-horizontal boundaries.

CPU-BG3 already tested a very simple ghost Laplacian diagnostic. It did not
improve hydrostatic consistency near the bottom boundary and therefore must
remain diagnostic-only.

## Current Production Boundary State

Production PR operators currently use:

- material-material interactions for `DivVel`, `LapPorePress`, `LapZ`, and
  `PorePressureAccelDiff`;
- top drained layer correction after pore-pressure update;
- bottom no-flux layer correction after pore-pressure update;
- no production boundary `PorePress`;
- no pore-pressure ghost particles;
- no MLS pressure extrapolation;
- no strict lateral no-flux operator.

This is sufficient for reduced 1D health checks, but not for strict reproduction
of paper boundaries.

## Boundary Requirements by Case

| Case | Boundary requirement |
|---|---|
| 01 Terzaghi | top Dirichlet `p_excess=0`, bottom/lateral no-flux, stable external loading route. |
| 02 Self-weight | same top/bottom requirements; Scenario 1 restart or gravity switch. |
| 03 Cryer | drained curved outer boundary and center-pressure postprocessing. |
| 04 Triaxial | undrained sides/top/bottom except imposed loading surfaces; confinement boundary. |
| 05/06 Slopes | non-horizontal seepage/no-flux boundaries and possible water table/free surface. |

## Candidate Production Strategies

### Strategy A: Keep Layer Corrections as Production Baseline

Description:

- Continue using top drained and bottom no-flux layer corrections.
- Add lateral layer corrections for simple columns.
- Do not include boundary particles in Laplacian sums.

Pros:

- Minimal source changes.
- Already stable for 1D reduced smokes.
- Easy to port to GPU.

Cons:

- Not particle-consistent.
- Weak for curved boundaries.
- Not sufficient for strict Cryer.
- Lateral and corner behavior remains ad hoc.

Recommendation: acceptable only as a near-term production baseline for reduced
smokes, not strict reproduction.

### Strategy B: Boundary Particles Carry Pore Pressure

Description:

- Allocate pore-pressure fields for boundary particles as well as material
  particles.
- Set boundary values according to boundary mode:
  - drained: `p_excess=0`;
  - no-flux: mirror/extrapolate from nearby material;
  - hydrostatic baseline through `HydraulicGravity`.
- Include boundary values in PR Laplacian sums.

Pros:

- Closer to SPH boundary treatment.
- Maps naturally to boundary normals and mDBC/cDBC concepts.

Cons:

- Requires robust boundary classification.
- Requires ghost/extrapolation values that are not yet reliable.
- Needs careful corner handling.
- A naive version was already worse in CPU-BG3.

Recommendation: do not implement as simple direct boundary-particle summation
without a better extrapolation operator.

### Strategy C: Mirror Ghost for No-Flux and Dirichlet Ghost for Drained

Description:

- Do not store permanent ghost particles.
- During a boundary interaction, construct a virtual pressure value:
  - drained: mirrored ghost satisfying `p_excess=0` at boundary;
  - no-flux: mirrored ghost satisfying zero normal gradient;
  - lateral no-flux: mirror across side normal.
- Use boundary normals to reflect material pressure/elevation states.

Pros:

- Conceptually correct for planar boundaries.
- Can be implemented first for 1D/2D planar cases.
- Avoids persistent ghost arrays.

Cons:

- Requires reliable boundary normals and distance-to-boundary geometry.
- Curved Cryer requires local normal and reference point.
- More complex interaction code.

Recommendation: best candidate for a minimal planar prototype after more
diagnostics.

### Strategy D: MLS / mDBC-Compatible Pressure Extrapolation

Description:

- Use an MLS fit from material neighbors to reconstruct pore pressure at
  boundary/ghost locations.
- Enforce Dirichlet or Neumann constraints in the reconstruction.
- Align with existing mDBC/cDBC correction infrastructure where possible.

Pros:

- Closest to the paper notes.
- Can support curved boundaries and complex domains.
- Potentially improves consistency for Cryer and slope cases.

Cons:

- Larger source change.
- Needs matrix assembly, fallbacks, and boundary mode metadata.
- GPU implementation will be nontrivial.
- Requires significant smoke testing.

Recommendation: likely strict-reproduction path, but too large to implement
without a separate focused design and staged prototype.

## Recommended Near-Term Decision

Do not promote CPU-BG3 simple ghost Laplacians to production.

For CPU strict-case preparation, use the following staged path:

1. **BND-2a: planar boundary diagnostic prototype**
   - Construct mirror/Dirichlet diagnostic values for top/bottom/lateral planar
     boundaries.
   - Compare hydrostatic residual, uniform excess field, and pressure-only
     diffusion.
   - Do not replace production PR operators.

2. **BND-2b: pressure-only production switch for planar 1D/2D**
   - Only if BND-2a improves residuals.
   - Add a guarded parameter such as `PorePressureBoundaryOperator=1`.
   - Test pressure-only first.

3. **BND-3: MLS design for curved/Cryer**
   - Use boundary normals and local material neighbors.
   - Implement diagnostic first.
   - Decide whether strict Cryer CPU smoke must wait for this.

## Required Metadata and Arrays

Potential persistent data:

- boundary mode per particle or per mk / geometry region;
- optional boundary `PorePress` if Strategy B/D is selected;
- optional ghost diagnostic fields for development;
- fallback flags/counts for diagnostics.

Prefer not to add production persistent arrays until the operator is selected.

## Minimal Tests Before Any Production Switch

1. Hydrostatic-only column:
   - `LapPorePress/(rho_w*g) + LapZ` should be closer to zero than the current
     operator near boundaries.
2. Uniform excess, no drained boundary:
   - no artificial boundary Laplacian or feedback.
3. Uniform excess with top drained:
   - response localized near top boundary.
4. Pressure-only 1D diffusion:
   - trend unchanged or improved compared with current baseline.
5. Cryer coarse geometry diagnostic:
   - center pressure remains bounded and symmetric.

## GPU Implications

Any production boundary operator affects GPU design:

- boundary-mode storage;
- boundary/material interaction kernels;
- possible MLS matrix reductions;
- sorting/duplicate handling for boundary diagnostic arrays;
- output/restart fields if boundary pore pressure is persistent.

Therefore GPU G1 should not assume production boundary ghost arrays. The current
GPU port plan may still use the existing material-only PR production baseline
only if strict boundary work is explicitly deferred.

## Current Recommendation

Boundary treatment remains a strict reproduction blocker. The next safe action
is not production integration, but a **planar mirror/Dirichlet diagnostic
prototype design** or an MLS-specific design. Until that work is completed, the
current reduced smokes remain reduced smokes only.

