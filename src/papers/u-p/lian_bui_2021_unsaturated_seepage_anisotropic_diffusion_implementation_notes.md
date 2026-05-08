# Implementation notes for Codex: Lian et al. (2021) transient seepage through unsaturated porous media with anisotropic diffusion

> Purpose: This Markdown file is written as **implementation notes for Codex**. It is intended to help Codex compare a paper against the current `GeoDualSPHysics_v5.2/src` codebase, plan CPU-first changes, and avoid unsafe direct edits.
>
> General rule for Codex: **Do not modify source files directly from these notes. First map paper variables to current code variables, identify existing implementations, then propose a minimal CPU-first plan.**

## Source paper

Yanjian Lian, Ha H. Bui, Giang D. Nguyen, Hieu T. Tran, and Asadul Haque, **"A general SPH framework for transient seepage flows through unsaturated porous media considering anisotropic diffusion"**, Computer Methods in Applied Mechanics and Engineering, 2021.

## 1. Core idea

This paper develops a single-layer SPH seepage solver for unsaturated/saturated porous media.

Main contributions:

- robust second-derivative SPH formulation for anisotropic diffusion;
- transient seepage using one set of Lagrangian particles;
- van Genuchten soil-water retention curve;
- boundary treatments for seepage surfaces;
- multi-resolution particle generation using Voronoi tessellation.

This is primarily a seepage solver paper, not a full deformation-coupled solver.

## 2. Governing head equation

The water-pressure head equation is:

```math
C_l\frac{dh_l}{dt}
+
n\frac{dS_r}{dt}
=
\nabla\cdot[k\nabla(h+z)]
```

where:

- `h_l` or `h`: water pressure head.
- `z`: elevation head.
- `S_r`: degree of saturation.
- `n`: porosity.
- `C_l`: specific storage.
- `k`: hydraulic conductivity tensor.

Using the chain rule:

```math
\frac{dh_l}{dt}
=
\frac{1}{\tilde{C}_{S_r}}
\nabla\cdot[k\nabla(h+z)]
```

with:

```math
\tilde{C}_{S_r}=C_l+C_s
```

and:

```math
C_s=n\frac{dS_r}{dh}
```

## 3. van Genuchten water-retention model

```math
S_r
=
S_{res}
+
(S_{sat}-S_{res})
[1+(g_a|-h|)^{g_n}]^{g_c}
```

where:

```math
g_c=(1-g_n)/g_n
```

Variables:

```text
S_res
S_sat
g_a
g_n
g_c
h
```

Need derivative `dS_r/dh` for `C_s`.

## 4. Anisotropic diffusion

The operator is:

```math
\nabla\cdot[k\nabla(h+z)]
```

For anisotropic hydraulic conductivity:

```math
k = [[k_xx, k_xy], [k_yx, k_yy]]
```

Implementation requires individual derivatives:

```text
d2h/dx2
d2h/dy2
d2h/dxdy
```

not only scalar Laplacian.

## 5. SPH second-derivative operator

A generic second derivative form is:

```math
\frac{\partial^2 f_i}{\partial x^m\partial x^n}
=
\sum_j
(f_j-f_i)
\left[
\frac{4r_{ji}^m r_{ji}^n}{|r_{ji}|^2}
-
\delta^{mn}
\right]
\hat{F}_{ij}
```

The paper improves accuracy on disordered particles. This should be implemented first as a standalone CPU operator and tested on analytic functions.

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

## 6. Required fields

```cpp
Head
HeadRate
DegreeSat
Porosity
HydCondTensor
SpecificMoisture
Storage
ElevationHead
```

Parameters:

```text
S_res
S_sat
van Genuchten g_a, g_n, g_c
hydraulic conductivity tensor
water unit weight
```

## 7. Suggested CPU-first phases

1. Implement/test second derivative on analytic functions.
2. Implement isotropic saturated head diffusion.
3. Add `S_r(h)` and `dS_r/dh`.
4. Add anisotropic conductivity tensor and cross derivatives.
5. Add seepage boundary conditions.
6. Couple to mechanics later.

## 8. Numerical stability issues

1. Second derivatives on disordered particles are the main risk.
2. `dS_r/dh` can be stiff near saturation transition.
3. Conductivity can vary strongly with saturation.
4. Explicit time step must satisfy diffusion limit:
   ```text
   dt <= O(h^2 / hydraulic diffusivity)
   ```
5. Boundary conditions dominate seepage accuracy.
6. Avoid saturation overshoot below `S_res` or above `S_sat`.

## 9. Codex prompt

```text
Please do not modify files. Read @papers/lian_bui_2021_unsaturated_seepage_anisotropic_diffusion_implementation_notes.md and inspect current CPU kernel/operator code. Identify whether the current code has a general second-derivative operator, hydraulic head field, van Genuchten model, or seepage boundary infrastructure.
```
