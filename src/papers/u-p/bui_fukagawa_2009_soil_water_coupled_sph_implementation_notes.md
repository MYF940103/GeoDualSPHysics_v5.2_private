# Implementation notes for Codex: Bui & Fukagawa (2009) first soil-water coupled SPH attempt

> Purpose: This Markdown file is written as **implementation notes for Codex**. It is intended to help Codex compare a paper against the current `GeoDualSPHysics_v5.2/src` codebase, plan CPU-first changes, and avoid unsafe direct edits.
>
> General rule for Codex: **Do not modify source files directly from these notes. First map paper variables to current code variables, identify existing implementations, then propose a minimal CPU-first plan.**

## Source paper

Ha H. Bui and R. Fukagawa, **"A first attempt to solve soil-water coupled problem by SPH"**, Terramechanics, 2009.

Note: the uploaded PDF is scanned. The formulas below are transcribed from the page images and should be checked against the original PDF before coding.

## 1. Core idea

This paper presents an early **single-layer / one-point soil-water coupled SPH** framework. The skeleton is represented by SPH particles, while pore-water pressure is carried on the same particles. It is a precursor to later `u-p`, `u-pl`, and `u-w-p` SPH formulations.

The main implementation value is the explicit pore-pressure-rate equation and the Laplacian-like pressure diffusion operator based on first kernel derivatives.

## 2. Core equations

The general saturated-soil equations are written as a mixture momentum equation, Darcy-type pore-fluid momentum equation, and pore-fluid mass balance:

```math
\nabla\cdot\sigma + \rho g - \rho\dot{v} - \rho_f\dot{w}=0
```

```math
\nabla p + \rho_f g - \rho_f(\dot{v}+\dot{w}/n)+\gamma_f w/k=0
```

```math
Q\nabla\cdot(v+w)-\dot{p}=0
```

where:

- `sigma`: total stress tensor.
- `sigma'`: effective stress tensor.
- `p`: pore-water pressure.
- `v`: solid skeleton velocity.
- `w`: average pore-fluid velocity relative to the skeleton.
- `rho`: saturated mixture density.
- `rho_s`, `rho_f`: solid and fluid densities.
- `n`: porosity.
- `k`: permeability or hydraulic conductivity depending on convention.
- `gamma_f`: unit weight of pore fluid.
- `Q`: average bulk modulus of saturated soil.

The storage modulus is:

```math
Q = \left[(1-n)/K_s+n/K_f\right]^{-1}
```

After simplification, the pressure-rate equation has the form:

```math
\dot{p}=Q\{\nabla\cdot v+\nabla\cdot w\}
```

with Darcy-type velocity:

```math
w = k\gamma_f^{-1}(\nabla p+\rho_f g-\rho_f\dot{v})
```

## 3. SPH formulas and algorithmic content

### 3.1 First-derivative SPH operator

```math
\nabla f(x_i)=\sum_j \omega_j f(x_j)\nabla W_{ij}
```

where `omega_j` is particle volume.

### 3.2 Laplacian-like pressure diffusion

The paper avoids direct second derivatives of the kernel. The derived operator is:

```math
\nabla^2 f(x_i)
=
-2\sum_j
\frac{f(x_j)-f(x_i)}{|x_{ij}|^2}
x_{ij}\cdot\nabla W_{ij}\omega_j
```

Implementation implication:

- Do not use direct `nabla^2 W`.
- Use a first-gradient-based pairwise operator similar to a Morris/Cleary-Monaghan diffusion operator.

### 3.3 Soil acceleration

A representative SPH momentum equation is:

```math
\frac{dv_i^\alpha}{dt}
=
\sum_j m_j
\left(
\frac{\sigma_i^{\prime\alpha\beta}}{\rho_i^2}
+
\frac{\sigma_j^{\prime\alpha\beta}}{\rho_j^2}
+
C_{ij}^{\alpha\beta}
\right)
\nabla^\beta W_{ij}
+
\sum_j m_j
\left(
\frac{p_j-p_i}{\rho_i\rho_j}
\right)
\nabla^\alpha W_{ij}
+
g^\alpha
```

The pressure term uses a pressure difference `(p_j - p_i)`. This is important because a constant pressure field should not create spurious acceleration.

### 3.4 Pore-pressure-rate SPH equation

The pressure equation contains:

```text
pressure diffusion term
velocity-divergence term
Darcy/seepage-related acceleration term
```

A representative implementation form is:

```math
\frac{dp_i}{dt}
=
\frac{Q_i}{\gamma_f}
\sum_j
\frac{m_j}{\rho_j}
\frac{4k_i k_j}{k_i+k_j}
(p_j-p_i)
\frac{x_{ij}\cdot\nabla W_{ij}}{|x_{ij}|^2}
+
Q_i \sum_j\frac{m_j}{\rho_j}(v_j-v_i)\cdot\nabla W_{ij}
+\cdots
```

The harmonic-type permeability average `4 k_i k_j/(k_i+k_j)` is important for discontinuous permeability.

## 4. Constitutive model

The skeleton is modeled with a linear elastic / elastoplastic Drucker-Prager model.

Yield function:

```math
f(I_1,J_2)=\sqrt{J_2}+\alpha_\phi I_1-k_c=0
```

Plane-strain constants:

```math
\alpha_\phi=\frac{\tan\phi}{\sqrt{9+12\tan^2\phi}}
```

```math
k_c=\frac{3c}{\sqrt{9+12\tan^2\phi}}
```

Non-associated plastic potential:

```math
g_p=3I_1\sin\psi+\sqrt{J_2}
```

The stress update includes Jaumann-rate terms, elastic response, and non-associated plastic flow.

## 5. Variables to map in current code

```text
pore pressure p
pressure rate dp/dt
skeleton velocity v
relative water velocity w
density rho
porosity n
permeability k
unit weight gamma_f
storage modulus Q
effective stress sigma'
strain rate epsilon_dot
spin rate omega_dot
Drucker-Prager parameters c, phi, psi, K, G
```

Likely missing fields in current GeoDualSPHysics if no pore-pressure module exists:

```text
PorePress
PorePressRate
Porosity
HydCond / permeability
StorageModulus Q
Darcy velocity or relative velocity
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

## 6. Suggested CPU-first implementation phases

### Phase 0: read-only mapping

Check whether the current code already has any single-layer pore-pressure field or coupled `u-p` update.

### Phase 1: passive pore-pressure scalar

Add `p` as a particle scalar but do not couple it to momentum.

### Phase 2: explicit pressure-rate update

Implement pressure diffusion and skeleton-divergence terms in CPU path only.

### Phase 3: pore-pressure feedback

Add the pressure-gradient contribution to acceleration after confirming stress sign conventions and avoiding pressure double counting.

### Phase 4: boundary conditions

Add drained, undrained, and free-surface pressure conditions. Do not assume current mDBC automatically supplies `p`.

## 7. Numerical stability issues

1. Direct second kernel derivatives are sensitive to particle disorder.
2. Permeability discontinuity should use harmonic averaging.
3. Explicit pressure updates may require very small time steps for low permeability or high bulk modulus.
4. Boundary pressure treatment is critical.
5. Do not combine pore-pressure diffusion, stress diffusion, shifting, and damping without isolated tests.
6. Check units of `k`: hydraulic conductivity and intrinsic permeability are not interchangeable.

## 8. Codex prompt

```text
Please do not modify files. Read @papers/bui_fukagawa_2009_soil_water_coupled_sph_implementation_notes.md and inspect source/JSphCpu.cpp, source/JSphCpuSingle.cpp, source/JSph.cpp, and source/JArraysCpu.cpp. Determine whether the current code already has a single-layer pore-pressure field, pore-pressure-rate update, Darcy/permeability parameters, and pore-pressure gradient force. Produce a variable mapping table and CPU-only implementation plan. Do not edit code.
```
