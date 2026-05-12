# LIT-B Recommendation Before Next Cryer Boundary Change

Date: 2026-05-12

## Core Finding

C5d did not fail because of a single bad quadrature constant. It failed because
the current Cryer boundary path is still not close enough to the boundary
treatment described in the original u-pw paper.

The original paper points toward:

```text
free-surface / boundary-particle identification
-> prescribed or extrapolated boundary pore-pressure state
-> MLS or corrected-kernel extrapolation for Neumann pressure boundaries
-> use boundary hydraulic states in the pore-pressure operator
```

Current mode `3` instead uses:

```text
material near-surface shell
-> local spherical virtual ghost/sample points
-> direct contribution to material LapPorePress/LapZ
```

That path is operator-level and better than a clamp, but it is still not a
faithful reproduction of the paper's boundary-particle/MLS concept.

## Answers To The C5d Questions

1. **Did C5d fail because it was not the original u-pw implementation?**
   Most likely yes in an important sense. It does not use boundary particles,
   free-surface detection, or MLS boundary pressure extrapolation as described
   in the original paper.

2. **Did the original literature use boundary-particle pressure extrapolation
   instead of our spherical ghost?**
   Yes. The original u-pw paper points to MLS extrapolation for pore-pressure
   boundary particles, while the drained/undrained paper uses Adami-style
   normalized extrapolation for dummy boundary pore pressure.

3. **Should we return to mode 2 / H1 ideas?**
   Yes, but not simply reuse H1 as-is. The next route should combine H1's
   boundary-particle hydraulic state idea with the original paper's MLS/free
   surface boundary logic and the Cryer spherical geometry.

4. **Should we continue current mode 3 quadrature?**
   Not as the primary path. It can remain a diagnostic baseline, but further
   local ghost/weight tuning risks becoming a rabbit hole.

5. **Should we implement original boundary-particle pressure extrapolation
   before Cryer?**
   Yes. A paper-faithful CPU prototype should be attempted before more C5e/C6
   Cryer runs.

6. **Is C5e spherical diffusion calibration still needed?**
   Yes, but only after a boundary-particle/MLS-style prototype exists. Running
   C5e now would mostly calibrate the current non-faithful mode 3 path.

7. **Where should dp refinement sit?**
   Later. Current results show a systematic boundary coupling issue at the
   material surface. Refining dp before changing the boundary method may only
   make a weak boundary more expensive.

8. **Should C6 quantitative comparison remain paused?**
   Yes. C5d still has center peak near `7.657 p0`, while the diagnostic clamp
   shows surface drainage can strongly alter the response. The boundary method
   is not yet credible enough for Figure 7B claims.

## Route Options

### Route 1: Faithful Original u-pw Boundary Reproduction

Goal: reproduce the paper's intended boundary logic as closely as possible.

Likely requirements:

- boundary/free-surface particle identification;
- hydraulic state arrays for boundary particles;
- MLS pressure extrapolation from material particles to boundary particles;
- Dirichlet override for drained free surfaces;
- Neumann/no-flux extrapolation where needed;
- include boundary hydraulic states in `LapPorePress` / `LapZ`.

Recommendation: high, but scope is larger than another mode-3 tweak.

### Route 2: Continue Current Mode 3 Quadrature

Goal: keep adding spherical ghost/quadrature samples and tune weights.

Advantages:

- local to current code;
- easy to test;
- no boundary-particle data model required.

Disadvantages:

- C5d shows only marginal improvement;
- does not follow the paper's boundary implementation direction;
- may overfit the coarse Cryer smoke without becoming a general boundary
  method.

Recommendation: low as primary route; keep only as a diagnostic comparator.

### Route 3: Hybrid Boundary-Particle / Spherical Cryer Route

Goal: rebuild mode `3` around boundary-particle hydraulic state and
paper-style extrapolation, while preserving the Cryer spherical drained
Dirichlet geometry.

Proposed steps:

1. Build CPU boundary-particle hydraulic state for the spherical exterior.
2. For drained samples/particles, impose `p_w=0` under
   `HydraulicElevationSource=0`.
3. For boundary-particle consistency and non-drained regions, use MLS or
   Adami-style normalized extrapolation from nearby material particles.
4. Include those boundary states in the PR operator.
5. Validate first with pressure-only spherical diffusion.
6. Then rerun the C5 compression smoke.

Recommendation: highest. It uses the original paper's boundary-state concept
without discarding the Cryer-specific spherical geometry already built.

## Recommended Next Task

Proceed with a new design task before source changes:

```text
C5e-design: CPU boundary-particle hydraulic state and MLS/Adami extrapolation
for spherical drained Cryer boundary
```

That task should define the data model, neighbor loops, boundary selection, and
diagnostics. Only after that should source be modified. C6 remains paused.
