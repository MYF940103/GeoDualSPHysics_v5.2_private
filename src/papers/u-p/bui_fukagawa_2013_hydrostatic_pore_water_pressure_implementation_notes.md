# Implementation notes for Codex: Bui & Fukagawa (2013) improved SPH method for saturated soils with hydrostatic pore-water pressure

> Purpose: This Markdown file is written as **implementation notes for Codex**. It is intended to help Codex compare a paper against the current `GeoDualSPHysics_v5.2/src` codebase, plan CPU-first changes, and avoid unsafe direct edits.
>
> General rule for Codex: **Do not modify source files directly from these notes. First map paper variables to current code variables, identify existing implementations, then propose a minimal CPU-first plan.**

## Source paper

Ha H. Bui and Ryoichi Fukagawa, **"An improved SPH method for saturated soils and its application to investigate the mechanisms of embankment failure: Case of hydrostatic pore-water pressure"**, International Journal for Numerical and Analytical Methods in Geomechanics, 2013.

## 1. Core idea

This paper improves SPH for submerged/saturated soils under **hydrostatic pore-water pressure**. It shows that a standard SPH gradient of pore pressure can generate significant error and instability near submerged soil surfaces. The paper proposes a pressure-difference formulation that:

- removes spurious force under constant pore-water pressure;
- automatically satisfies submerged-surface dynamic boundary conditions;
- is directly applicable to dry and saturated soils.

## 2. Core equations

Continuum motion:

```math
\rho\ddot{u} = \nabla\cdot\sigma+\rho g
```

Total stress:

```math
\sigma = \sigma' - p_w I
```

Effective-stress form:

```math
\rho\ddot{u} = \nabla\cdot\sigma' - \nabla p_w + \rho g
```

SPH effective-stress term:

```math
\ddot{u}_i^\alpha
=
\sum_j m_j
\left(
\frac{\sigma_i^{\prime\alpha\beta}+\sigma_j^{\prime\alpha\beta}}
{\rho_i\rho_j}
+
C_{ij}^{\alpha\beta}
\right)
\frac{\partial W_{ij}}{\partial x_i^\beta}
+
g_i^\alpha
```

Improved pore-pressure term:

```math
\sum_j
m_j
\frac{p_{wj}-p_{wi}}{\rho_i\rho_j}
\frac{\partial W_{ij}}{\partial x_i^\alpha}
```

Full saturated-soil acceleration:

```math
\ddot{u}_i^\alpha
=
\sum_j m_j
\left(
\frac{\sigma_i^{\prime\alpha\beta}+\sigma_j^{\prime\alpha\beta}}
{\rho_i\rho_j}
+
C_{ij}^{\alpha\beta}
\right)
\frac{\partial W_{ij}}{\partial x_i^\beta}
+
\sum_j
m_j
\frac{p_{wj}-p_{wi}}{\rho_i\rho_j}
\frac{\partial W_{ij}}{\partial x_i^\alpha}
+
g_i^\alpha
```

## 3. Hydrostatic pore-water pressure

For simplicity, the paper assumes hydrostatic pore pressure:

```math
p_w = \gamma_w(z_{water}-z)
```

for particles below groundwater table/reservoir level, and `p_w = 0` above.

Implementation variables:

```text
WaterLevel
WaterUnitWeight
PorePress
z-coordinate
```

## 4. Damping for initial stress

The paper proposes damping during initial stress generation:

```text
apply gravity
use damping force to remove stress waves
obtain initial in-situ stresses
then run failure/deformation analysis
```

In current code, check `JDsDamping.cpp` or existing damping options.

## 5. Boundary treatment

The paper assigns effective stress and pore pressure to boundary particles from adjacent soil particles.

Current GeoDualSPHysics likely uses mDBC with ghost-node reconstruction. For `p_w`, either:

- reconstruct ghost/boundary pore pressure consistently; or
- compute hydrostatic `p_w` from boundary particle coordinates.

## Possible mapping to GeoDualSPHysics / DualSPHysics v5.2

Current project root:

```text
D:\MYF\SPH\GeoDualSPHysics_v5.2\src
```

Primary CPU files to inspect first:

```text
source/main.cpp
source/JSph.cpp
source/JSph.h
source/JSphCpu.cpp
source/JSphCpu.h
source/JSphCpuSingle.cpp
source/JSphCpuSingle.h
source/JSphShifting.cpp
source/JArraysCpu.cpp
source/JArraysCpu.h
source/JCaseProperties.cpp
source/JCaseProperties.h
source/JXml.cpp
source/JSphCfgRun.cpp
```

Primary GPU files to inspect only after CPU behavior is understood:

```text
source/JSphGpu.cpp
source/JSphGpu.h
source/JSphGpuSingle.cpp
source/JSphGpuSingle.h
source/JSphGpu_ker.cu
source/JSphGpu_ker.h
source/JSphGpuSimple_ker.cu
source/JSphShifting_ker.cu
source/JArraysGpu.cpp
source/JArraysGpu.h
```

Likely current CPU call chain:

```text
main.cpp
  -> JSphCpuSingle::Run()
    -> ComputeStep()
      -> ComputeStep_Ver() or ComputeStep_Sym()
        -> Interaction_Forces()
          -> PreInteraction_Forces()
          -> JSphCpu::Interaction_Forces_ct()
             -> JSphCpu::InteractionForcesFluid()
             -> JSphCpu::InteractionForcesBound()
        -> DtVariable()
        -> RunShifting()
        -> ComputeVerlet() or ComputeSymplectic...
```

## 6. Variables to map

```text
effective stress sigma'
pore water pressure p_w
hydrostatic water level
water unit weight gamma_w
gravity direction
density rho
stabilization term C_ij
damping coefficient
boundary stress / boundary pore pressure
```

## 7. Suggested CPU-first implementation phases

1. Check whether current code already has hydrostatic pore pressure.
2. Add passive `PorePress` field from water level.
3. Add pressure-difference force in `InteractionForcesFluid()`.
4. Define boundary/ghost pressure behavior.
5. Validate with constant pressure and submerged patch tests.
6. Then test embankment/high-water-table case.

## 8. Numerical stability issues

1. Standard pore-pressure gradient can be unstable near submerged free surfaces.
2. Difference-form pressure term must vanish for constant pressure.
3. Hydrostatic assumption excludes seepage and pressure dissipation.
4. Boundary `p_w` must be consistent.
5. Damping should not contaminate final dynamic failure.

## 9. Codex prompt

```text
Please do not modify files. Read @papers/bui_fukagawa_2013_hydrostatic_pore_water_pressure_implementation_notes.md and inspect source/JSphCpu.cpp, source/JSphCpuSingle.cpp, source/JSph.cpp, and mDBC-related functions. Determine whether a hydrostatic pore-water-pressure field and pressure-difference force can be added CPU-first without changing the constitutive stress update.
```
