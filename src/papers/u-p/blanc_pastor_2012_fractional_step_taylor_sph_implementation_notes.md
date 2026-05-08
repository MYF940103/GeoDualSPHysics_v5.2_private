# Implementation notes for Codex: Blanc & Pastor (2012) Fractional Step Runge-Kutta Taylor SPH for coupled geomechanics

> Purpose: This Markdown file is written as **implementation notes for Codex**. It is intended to help Codex compare a paper against the current `GeoDualSPHysics_v5.2/src` codebase, plan CPU-first changes, and avoid unsafe direct edits.
>
> General rule for Codex: **Do not modify source files directly from these notes. First map paper variables to current code variables, identify existing implementations, then propose a minimal CPU-first plan.**

## Source paper

T. Blanc and M. Pastor, **"A stabilized Fractional Step, Runge-Kutta Taylor SPH algorithm for coupled problems in geomechanics"**, Computer Methods in Applied Mechanics and Engineering, 2012.

## 1. Core idea

This paper proposes a stabilized **Fractional Step (FS)** algorithm combined with **Runge-Kutta / Taylor SPH** for coupled stress-velocity-pore-pressure geomechanics.

Key ideas:

- mixed stress-velocity-pore pressure formulation;
- fractional-step pressure correction to avoid instability;
- Taylor-SPH time integration;
- auxiliary nodes similar to Gauss points;
- corrected SPH approximation to reduce boundary deficiency.

This is a major algorithmic framework, not a small force-term patch.

## 2. Field variables

```text
v          velocity
sigma'     effective stress
p          pore pressure
rho        density
epsilon    strain
epsilon_v  volumetric strain
k          permeability
M / K      storage or compressibility modulus
```

## 3. Fractional-step structure

Generic workflow:

```text
1. Compute intermediate velocity/stress.
2. Solve pressure correction / pore pressure equation.
3. Correct velocity.
4. Update stress and state variables.
```

This requires pressure equation infrastructure and boundary conditions.

## 4. Taylor-SPH operator

The paper describes a Taylor-SPH operator:

```math
T_{SPH}(\Delta t): \Delta\phi_{TSPH}
=
\Delta t \, div(f^{*/2})
```

where the half-step flux uses Taylor expansion:

```math
\phi^{*/2}
=
\phi^n
+
\Delta\phi_s
-
\frac{\Delta t}{2}div(f^n)
```

Interpretation:

- half-step values are stored;
- material and auxiliary nodes exchange interpolation information;
- the scheme resembles Taylor-Galerkin methods in FEM.

## 5. Corrected SPH approximation

A normalized 1D interpolation is:

```math
\phi_I =
\frac{
\sum_J (m_J/\rho_J)\phi(x_J)W_{IJ}
}{
\sum_J (m_J/\rho_J)W_{IJ}
}
```

For multidimensional correction, a local linear system is solved:

```math
A\phi = r
```

Implementation implication:

- local correction matrices are needed;
- current mDBC may have local reconstruction, but the main solver likely does not have a global auxiliary-node Taylor-SPH structure.

## 6. Material and auxiliary nodes

The method uses two sets of nodes:

```text
material SPH nodes: carry material mass
auxiliary SPH nodes: store half-step variables, similar to Gauss points
```

Total mass is on material nodes:

```math
M_{total}=\sum_I m_I
```

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

## 7. Reusable ideas versus major changes

Reusable ideas:

```text
corrected gradient operators
fractional-step pressure correction concept
half-step evaluation
pressure stabilization
```

Major new infrastructure:

```text
auxiliary-node arrays
global pressure solver
Taylor-SPH time integrator
fractional-step loop
new boundary handling for p
```

## 8. Numerical stability issues

1. Fractional step helps avoid equal-order velocity-pressure instabilities.
2. Auxiliary nodes double many field arrays.
3. Correction matrices can be ill-conditioned near boundaries.
4. PPE requires carefully defined pressure boundary conditions.
5. Replacing Verlet/Symplectic with Taylor-SPH is a large redesign.

## 9. Codex prompt

```text
Please do not modify files. Read @papers/blanc_pastor_2012_fractional_step_taylor_sph_implementation_notes.md and inspect current CPU time-integration code. Identify whether the current solver has any fractional-step pressure-correction structure, auxiliary-node infrastructure, or corrected SPH matrix operators that could support this method. Produce only a feasibility map.
```
