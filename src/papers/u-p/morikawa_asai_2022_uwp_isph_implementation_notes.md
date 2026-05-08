# Implementation notes for Codex: Morikawa & Asai (2022) strong-coupled u-w-p ISPH for saturated soil

> Purpose: This Markdown file is written as **implementation notes for Codex**. It is intended to help Codex compare a paper against the current `GeoDualSPHysics_v5.2/src` codebase, plan CPU-first changes, and avoid unsafe direct edits.
>
> General rule for Codex: **Do not modify source files directly from these notes. First map paper variables to current code variables, identify existing implementations, then propose a minimal CPU-first plan.**

## Source paper

Daniel S. Morikawa and Mitsuteru Asai, **"Soil-water strong coupled ISPH based on u-w-p formulation for large deformation problems"**, Computers and Geotechnics, 2022.

## 1. Core idea

This paper proposes a strong-coupled **one-point two-phase** SPH formulation based on `u-w-p` Biot theory and incompressible SPH (ISPH).

Key features:

- SPH particles move according to soil skeleton velocity.
- Water variables are embedded in the same particles.
- Soil grains and pore water are treated as incompressible.
- Pore pressure is obtained through a pressure Poisson equation (PPE).
- Darcy drag is updated implicitly.
- Suitable for dynamic seepage, low permeability, and strongly coupled saturated-soil problems.

## 2. Variables

```text
v       soil skeleton velocity
v_w     pore-water velocity
w       relative water velocity / Darcy-type velocity
p       pore pressure
n       porosity
rho_s   solid density
rho_w   water density
rho     mixture density
sigma'  effective stress
sigma   total stress
k       permeability / hydraulic conductivity
g       gravity
```

Particles move with skeleton velocity:

```math
dx/dt = v
```

## 3. Governing structure

### 3.1 Skeleton momentum

Representative effective-stress form:

```math
\rho\frac{dv}{dt}
=
\nabla\cdot\sigma'
-
\nabla p
+
\rho g
+
\text{coupling terms}
```

The sign of `grad p` depends on stress convention and must be checked.

### 3.2 Darcy relation

Relative fluid motion follows pressure-gradient and gravity terms, for example:

```math
w \sim -\frac{k}{\rho_w g}(\nabla p-\rho_w g)
```

### 3.3 Incompressibility constraint

The incompressibility condition leads to a divergence constraint, typically involving skeleton velocity and relative water flux:

```math
\nabla\cdot v + \nabla\cdot w = 0
```

or a porosity-weighted variant.

## 4. Projection/PPE algorithm

A typical algorithm is:

```text
1. Predict skeleton velocity without final pressure correction.
2. Assemble pressure Poisson equation from incompressibility.
3. Solve PPE for pore pressure.
4. Correct velocity with pore-pressure gradient.
5. Update water velocity / Darcy velocity.
6. Update porosity and effective stress.
```

Implementation implication:

```text
This requires global PPE assembly and a linear solver.
```

Current DualSPHysics-style explicit time integration does not provide this infrastructure by default.

## 5. SPH operators

Corrected gradient of velocity:

```math
<grad v>_i =
\frac{1}{\rho_i}\sum_j m_j \tilde{\nabla}W_{ij}\otimes(v_j-v_i)
```

Pressure gradient:

```math
<grad p>_i =
\rho_i\sum_j m_j
\left(
\frac{p_i}{\rho_i^2}\tilde{\nabla}W_{ij}
-
\frac{p_j}{\rho_j^2}\tilde{\nabla}W_{ji}
\right)
```

Velocity divergence:

```math
<div v>_i =
\frac{1}{\rho_i}\sum_j m_j (v_j-v_i)\cdot\tilde{\nabla}W_{ij}
```

Pressure Laplacian:

```math
<nabla^2 p>_i =
\frac{2}{\rho_i}
\sum_j m_j
\frac{r_{ij}\cdot\nabla W_{ij}}{|r_{ij}|^2}
(p_i-p_j)
```

## 6. Constitutive model

The paper can use Mohr-Coulomb or modified Cam-Clay, but the coupling structure is independent of the exact constitutive model.

For GeoDualSPHysics:

```text
Do not replace the current Drucker-Prager stress update while implementing hydromechanical coupling unless explicitly requested.
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

## 7. Required new infrastructure

Likely missing or required:

```text
pore-pressure scalar field
water velocity or relative velocity field
porosity field
permeability field
PPE matrix assembly
linear solver
pressure correction step
pressure boundary conditions
implicit Darcy drag update
```

## 8. Suggested implementation strategy

This is a major solver extension. Recommended steps:

1. Add passive pore-pressure and porosity fields.
2. Prototype explicit `u-p` pressure update first.
3. Implement and test SPH divergence, gradient, and Laplacian operators.
4. Add a small PPE solver prototype outside the main production path.
5. Only after CPU verification, integrate into time stepping.
6. Port to GPU last.

## 9. Numerical stability issues

1. PPE requires robust boundary conditions.
2. Low permeability makes Darcy coupling stiff.
3. Corrected gradient matrices can be singular near boundaries.
4. Pressure correction may conflict with weakly compressible pressure/EOS.
5. ISPH is not a small local force-term modification.

## 10. Codex prompt

```text
Please do not modify files. Read @papers/morikawa_asai_2022_uwp_isph_implementation_notes.md and inspect the current CPU interaction and time-integration code. Identify which components required by u-w-p ISPH already exist and which require new solver infrastructure, especially p, v_w, porosity, permeability, PPE assembly, and pressure correction.
```
