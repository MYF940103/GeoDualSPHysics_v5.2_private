# Implementation notes for Codex: Bui et al. (2011) slope stability and discontinuous slope failure by elastoplastic SPH

> Purpose: This Markdown file is written as **implementation notes for Codex**. It is intended to help Codex compare a paper against the current `GeoDualSPHysics_v5.2/src` codebase, plan CPU-first changes, and avoid unsafe direct edits.
>
> General rule for Codex: **Do not modify source files directly from these notes. First map paper variables to current code variables, identify existing implementations, then propose a minimal CPU-first plan.**

## Source paper

H. H. Bui, R. Fukagawa, K. Sako, and J. C. Wells, **"Slope stability analysis and discontinuous slope failure simulation by elasto-plastic smoothed particle hydrodynamics (SPH)"**, Geotechnique, 2011.

## 1. Core idea

This paper extends elastoplastic SPH to evaluate slope stability and simulate post-failure behavior. The important implementation ideas are:

- shear strength reduction method (SRM);
- accumulated plastic strain as a slip-surface indicator;
- pore-water pressure term written in a difference form;
- boundary conditions for free-roller and fixed boundaries;
- SPH failure criterion based on displacement evolution versus SRF.

## 2. Core equations

### 2.1 Effective-stress momentum equation

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

where:

- `sigma'`: effective stress tensor.
- `C_ij`: stabilization term, including artificial viscosity and artificial stress.
- `g`: gravity.

### 2.2 Total stress and pore pressure

```math
\sigma=\sigma' - p_w I
```

### 2.3 Saturated-soil motion equation

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

The `p_wj - p_wi` term should vanish under constant pore pressure.

## 3. Shear strength reduction method

Strength reduction factor `SRF` modifies soil strength:

```math
c_{reduced}=c/SRF
```

```math
\tan\phi_{reduced}=\tan\phi/SRF
```

```math
\phi_{reduced}=\arctan(\tan\phi/SRF)
```

The paper's SPH failure criterion is based on maximum displacement versus iteration number:

```text
convex curve -> convergent solution
concave / rapidly increasing curve -> non-convergent or failed solution
lowest failed SRF -> factor of safety
```

Implementation implication:

- SRM can first be implemented as an external case/script workflow, not necessarily as solver code.
- If implemented inside the solver, material parameters must be updated consistently before the stress update.

## 4. Slip surface and output

Critical slip surface is identified from accumulated plastic strain contours.

Codex should check whether the current code outputs:

```text
equivalent deviatoric plastic strain
accumulated plastic strain
kappa
plastic strain tensor or scalar
```

## 5. Boundary treatment

The paper uses:

- ghost particles for free-roller boundaries;
- stress boundary method / virtual particles for full-fixity boundaries.

Current GeoDualSPHysics mDBC is different and likely more advanced. Do not replace mDBC without explicit instruction.

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
SRF
cohesion c
friction angle phi
dilation angle psi
effective stress sigma'
pore pressure p_w
accumulated plastic strain / kappa
maximum displacement
stabilization C_ij
artificial viscosity
artificial stress
sound speed c_s
```

## 7. Implementation phases

### Phase 0: read-only check

Inspect whether the current code supports friction/cohesion/dilatancy, softening, equivalent plastic strain output, pore pressure, and strength-reduction factors.

### Phase 1: external SRF workflow

Create a script or manual XML workflow that modifies `phi` and `coh` for a series of SRF values.

### Phase 2: output field

Ensure accumulated plastic strain is available for slip-surface visualization.

### Phase 3: optional pore-pressure term

If a pore-pressure field exists, verify pressure-gradient difference form.

## 8. Numerical stability issues

1. Strength reduction can trigger rapid post-failure motion.
2. The displacement-convergence criterion is heuristic and case dependent.
3. Artificial stress, shifting, and stress diffusion affect failure patterns.
4. Pore pressure must not create spurious force in constant-pressure regions.
5. Boundary treatment affects toe failure and basal slip.

## 9. Codex prompt

```text
Please do not modify files. Read @papers/bui_2011_slope_stability_elastoplastic_sph_implementation_notes.md and inspect source/JSph.cpp, source/JSphCpu.cpp, source/JSphCpuSingle.cpp, and source/JCaseProperties.cpp. Determine whether the current code supports shear strength reduction, accumulated plastic strain output, and saturated-soil pore-pressure gradient terms. Produce a file/function map only.
```
