# dp=0.03 bad-point diagnosis for q0 Terzaghi resolution test

Date: 2026-07-14

Case folder:

- `examples/Hydromechanic coupling/02_TerzaghiConsolidation_q0_PR`
- Figure/data folder: `tests/figures/resolution_k1em4_dp003_dp0005_dt2em6`

## Main conclusion

`dp=0.03` should be treated as an under-resolved failure/control point, not as a valid point for convergence-order fitting.

The most likely cause is that the column is too narrow relative to the kernel support at this resolution. The case has only 99 fluid particles, equivalent to about 3 lateral columns by 33 vertical layers. With `sizefx=0.1`, `Dp=0.03`, `KernelH=0.054`, and `KernelSize=0.108`, the kernel support is larger than the whole model width. There is effectively no lateral interior particle.

This makes the free-surface / drainage-boundary logic fragile for the whole domain, and it also makes the `TopVertical` loading mode fragile because top-load application depends on upward free-surface particles/normals.

## Evidence

From `resolution_k1em4_dp003_summary.csv`:

- `dp=0.03`: `fluid_particles=99`, `max_speed=0.3608985459856926`
- `dp=0.02`: `fluid_particles=250`, `max_speed=0.0016690825306256672`
- `dp=0.01`: `fluid_particles=1000`
- `dp=0.005`: `fluid_particles=4000`

From the run log:

- `CaseNbound=14`
- `CaseNfluid=99`
- `Dp=0.03`
- `KernelH=0.054`
- `KernelSize=0.108`
- `HydroMechDrainageBoundary: FreeSurface`
- `HydroMechTopLoadMode="TopVertical"`
- `Excluded particles: 0`

The pressure profile is already badly under-pressurized near the start of consolidation:

- At `Tv=0.05`, `dp=0.03` bottom normalized excess pressure is about `0.3009`, while the theory value is about `0.9968`.
- At the same target time, `dp=0.02` bottom normalized excess pressure is about `0.9970`, matching theory.
- The `dp=0.03` mean normalized excess pressure at `PartFluid_0001` is only about `0.24`, so the bad state forms during the initial load/drainage transition, not only during late diffusion.

## Relevant source paths

Drainage is tied to free-surface classification in the CPU path:

- `source/JSphCpu.cpp`: `IsHydroMechDrainageActive`
- `source/JSphCpu.cpp`: `IsFreeSurfaceParticle`
- `source/JSphCpu.cpp`: `IsHydroMechDrainedParticle`
- `source/JSphCpu.cpp`: `ApplyFreeSurfacePorePressure`

The drained pore pressure logic sets pore pressure to zero for particles classified as drained free-surface/isolated particles. Therefore, when the whole domain is only a few columns wide and every particle is affected by lateral truncation, a free-surface-based drainage boundary can contaminate the interior pressure field.

The `TopVertical` load mode also depends on free-surface/upward normal classification. With only three particles across the width, the top-load particle set and normal direction are not a robust representation of a one-dimensional Terzaghi column.

## Less likely causes

- Not particle exclusion: the log reports `Excluded particles: 0`.
- Not a post-processing-only issue: `dp=0.02` and `dp=0.01` match the same analytical/post-processing path at early time.
- Not mainly timestep instability: the early `Tv=0.05` max speed is small, but pressure is already wrong. The later velocity spike appears more like a consequence of the bad coarse-resolution state.

## Recommendation

Keep `dp=0.03` out of convergence-order fits and plots intended to show the asymptotic range. It can be shown separately as a coarse failure threshold.

If a coarser endpoint is still needed, test an intermediate resolution such as `dp=0.025`, or change the benchmark geometry/BC design so that coarse cases still have a real interior region. Possible routes include increasing model width, using a more explicit top-only drainage mask, or avoiding free-surface-based drainage classification for this 1D verification.
