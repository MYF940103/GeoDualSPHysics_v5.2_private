# Cryer C4-B2 Flexible Confining Stress Source Audit

Date: 2026-05-12

## Objective

This audit identifies where a flexible confining stress term could be inserted
into the existing GeoDualSPHysics u-pw mechanical momentum path. It is a design
audit only: no source was changed.

## CPU Momentum Path

The CPU force path currently has a clear separation between acceleration
initialization, external acceleration input, pairwise stress divergence, and the
later addition of body gravity.

Relevant locations:

- [JSphCpu.cpp](../../source/JSphCpu.cpp): `PreInteractionVars_Forces` zeroes
  `Acec` and `Rsigmac`, then calls `AccInput->RunCpu(...)` when external
  acceleration input is enabled.
- [JSphCpuSingle.cpp](../../source/JSphCpuSingle.cpp): the CPU step delegates
  force computation through `Interaction_Forces`.
- [JSphCpu.cpp](../../source/JSphCpu.cpp): `Interaction_ForcesCpuT` calls
  `InteractionForcesFluid` for material-material and material-boundary
  interactions.
- [JSphCpu.cpp](../../source/JSphCpu.cpp): `InteractionForcesFluid` contains
  the pairwise stress-divergence contribution:

```cpp
prsxx = massp2*(sigmap1.xx+sigmap2.xx)/(rhopp1*velrhop2.w);
...
acep1.x += (prsxx*frx+prsxy*fry+prsxz*frz);
```

This stress-divergence block is the natural CPU insertion point. A flexible
confining stress can be added as an extra isotropic stress tensor in the same
pairwise summation, without using `AccInput` and without altering the body
gravity or pore-pressure equations.

## GPU Momentum Path

The GPU path has the same conceptual stages:

- [JSphGpu.cpp](../../source/JSphGpu.cpp) zeroes `Aceg` and calls
  `AccInput->RunGpu(...)` when external acceleration is active.
- [JSphGpuSingle.cpp](../../source/JSphGpuSingle.cpp) packages the force
  parameters and calls `cusph::Interaction_Forces(...)`.
- [JSphGpu_ker.cu](../../source/JSphGpu_ker.cu) contains the stress-divergence
  pair terms in `KerInteractionForcesFluidBox` and the soil-specific
  `KerInteractionForcesSoilsBox`.

GPU implementation is intentionally not part of C4-B2. If C4-B3 adds a CPU-only
flexible confining stress switch, the GPU path must hard error when the switch
is enabled until the CUDA pair term and diagnostics are implemented.

## Existing Loading Hooks

Existing hooks are not sufficient for strict Cryer:

- `AccInput` is an acceleration input, not a surface traction.
- Body gravity is a bulk body force and must remain independent of Cryer
  traction.
- Artificial viscosity and damping are already accumulated in the mechanical
  force/integration path, but they are stabilizers rather than boundary loads.
  They should not be reused as confining pressure hooks.
- mDBC/cDBC boundary routines provide mechanical boundary infrastructure but do
  not currently expose a native spherical pressure-traction input.
- The stress tensor pair term is the closest existing production mechanism to
  the Zhao-style flexible confining stress route.

## Target Selection

The confining stress should apply only to selected soil/material particles:

- default target should be all material particles in the Cryer sphere;
- optional target by `mkfluid` should be supported for diagnostics;
- boundary particles, floating bodies, and non-soil water/fluid markers should
  not receive the term unless a later design explicitly needs them;
- the term should not be applied through `CODE_IsFixed` or generic boundary
  particles.

## Momentum Consistency

The preferred implementation is pairwise and stress-like. For a constant
isotropic confining stress, interior pair contributions should cancel by kernel
symmetry, while free-surface particles retain an inward residual because their
kernel support is truncated. This is why the term should be inserted into the
stress divergence summation rather than as a per-particle body acceleration.

Diagnostics must check:

- net force vector;
- center-of-mass acceleration;
- symmetry residual;
- radial acceleration projection;
- interior cancellation;
- surface localization.

## Recommended CPU Insertion Point

C4-B3 should start CPU-first in `InteractionForcesFluid`, close to the existing
stress-divergence contribution. The first version should:

- be off by default;
- add only an isotropic confining tensor;
- be active only for selected material particles;
- avoid material-boundary pair contributions in the first pass so the free
  surface truncation remains the loading mechanism;
- produce diagnostics before any strict Cryer run is attempted.
