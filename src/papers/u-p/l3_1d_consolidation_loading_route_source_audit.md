# L3 1D Consolidation Loading Route Source Audit

## Scope

This audit checks current GeoDualSPHysics capabilities for representing the
1D Terzaghi top load `q0=-10 kPa` without changing the PR governing equation or
reviving deprecated Cryer/TopLoad paths.

## Available Routes

| Route | Current support | CPU/GPU | Paper-faithful? | Dynamic risk | Notes |
| --- | --- | --- | --- | --- | --- |
| `AccInput` body acceleration | Native `JDsAccInput`; selects mk range and adds `acclin` to particle acceleration | CPU/GPU | Reduced only | High | Adds body acceleration to a finite particle layer, not a surface traction. |
| Moving/fixed `mkbound` plate | Existing DualSPHysics motion/fixed boundary machinery | CPU/GPU for motion basics | Displacement/velocity controlled, not stress controlled | Medium | Useful for platen kinematics, not constant `q0` traction. |
| Force/traction boundary | No locked top surface traction interface for 1D soil load in current branch | Not available as production route | Would be faithful | Low if quasi-static | Requires source design. Do not resurrect deprecated `TopLoad*` blindly. |
| FlexibleConfiningStress | CPU-only free-boundary stress-like term | CPU only | No for 1D top load | Medium | Designed for lateral/free-surface confinement, not top surcharge. |
| `InitialStressMode=1` | Uniform isotropic effective compression | CPU only | Partial | Low | Can seed effective stress but not a top surcharge plus drainage by itself. |
| Direct pore-pressure initialization | `PorePressureInit=3`, profiles 1/2/3; CPU/GPU implemented | CPU/GPU | Faithful as diffusion gate, not mechanical loading | Low | Best immediate route to test PR diffusion against analytical initial condition. |
| Top material clamp / hydraulic top drain | `PorePressureTopDrained=1`; clamps excess in top layer | CPU/GPU | Hydraulic part only | Low | Needed with either load route. |
| Platen reaction diagnostics | Pairwise reaction for mkbound platens | CPU only | Diagnostics only | Low | Helpful for future mechanical route, not required for L3a pressure gate. |

## Source Observations

### AccInput

`JDsAccInput::RunCpu` and the GPU equivalent add linear acceleration to selected
particles based on their encoded mk.  The route is robust and GPU-supported,
but it is a body-acceleration route.  It does not know the loaded surface area,
does not accumulate a plate reaction, and does not enforce a constant surface
traction.

### Pore Pressure Initialization

`PorePressureInit=3` is parsed in `JSph.cpp` and initialized in both CPU and GPU
paths.  It supports a uniform analytical excess profile with
`PorePressureAnalyticalProfile=3`.  CPU and GPU then apply top drained and
bottom no-flux corrections during initialization and after updates.

### Boundary Operators

`PorePressureBoundaryOperator=0` is the legacy layer correction and is
CPU/GPU-supported.  Operator `1` is also GPU-supported.  Operators `2` and `3`
are CPU-only experimental paths.  L3 uses mode `0` to stay consistent with L2
and avoid CPU-only boundary changes.

### Deprecated TopLoad

The active source no longer contains the old source-side `TopLoad*` path.  Some
historical XML files still carry disabled `TopLoad*` keys, but the formal
external-load route was moved to native `AccInput`.  L3 should not reintroduce
the old interface without a new design.

## Route Assessment

1. `AccInput` is acceptable for reduced smoke and CPU/GPU plumbing, but not for
   paper-level Terzaghi loading.
2. A prescribed-motion top plate is not equivalent to constant `q0`.
3. A true force/traction plate would be the strict mechanical route, but needs
   source design.
4. `PorePressureInit=3` is the lowest-risk no-source route for an analytical
   diffusion gate.

## Recommended Next Step

Use `PorePressureInit=3` with a uniform `10 kPa` initial excess field as L3a.
This tests PR diffusion, top drained, bottom no-flux, CPU/GPU parity, and
postprocessing against the analytical initial condition without the L2 dynamic
loading artifact.  Then design L3b as a separate mechanical top-load route.
