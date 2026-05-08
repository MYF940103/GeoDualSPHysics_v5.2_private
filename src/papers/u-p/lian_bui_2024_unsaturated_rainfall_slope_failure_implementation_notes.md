# Implementation notes for Codex: Lian et al. (2024) unsaturated-soil SPH for rainfall-induced slope failure

> Purpose: This Markdown file is written as **implementation notes for Codex**. It is intended to help Codex compare a paper against the current `GeoDualSPHysics_v5.2/src` codebase, plan CPU-first changes, and avoid unsafe direct edits.
>
> General rule for Codex: **Do not modify source files directly from these notes. First map paper variables to current code variables, identify existing implementations, then propose a minimal CPU-first plan.**

## Source paper

Yanjian Lian, Ha H. Bui, Giang D. Nguyen, Shaohan Zhao, and Asadul Haque, **"A computationally efficient SPH framework for unsaturated soils and its application to predicting the entire rainfall-induced slope failure process"**, Geotechnique, 2024.

## 1. Core idea

This paper presents a three-phase single-layer SPH model for coupled flow-deformation in unsaturated porous media undergoing large deformation and failure.

Key contributions:

- solid, water, and air information carried by one particle set;
- anisotropic seepage and unsaturated/saturated transition;
- suction-dependent elastoplastic constitutive model;
- adaptive two-timescale scheme;
- rainfall-induced slope failure simulation.

## 2. Phase variables

For phases:

```text
s = solid
l = liquid water
a = air
```

Partial density:

```math
\bar{\rho}^{\alpha}=n^{\alpha}\rho^{\alpha}
```

Volume fractions:

```math
n_s=1-n
```

```math
n_l=nS_r
```

```math
n_a=n(1-S_r)
```

where:

- `n`: porosity.
- `S_r`: degree of saturation.
- `rho^alpha`: intrinsic density.
- `n^alpha`: volume fraction.

## 3. Mass conservation

For phase `alpha`:

```math
\frac{d^\alpha\bar{\rho}^{\alpha}}{dt}
+
\bar{\rho}^{\alpha}\nabla\cdot v^{\alpha}=0
```

Water and air equations are rewritten in the solid skeleton frame.

## 4. Pore-water and pore-air pressure evolution

Representative pore-water pressure structure:

```math
\frac{n_l}{\hat{\beta}}\frac{d^s p_l}{dt}
+
\frac{1}{\rho_l}n_l\bar{w}_{ls}\cdot\nabla\rho_l
+
n\frac{d^s S_r}{dt}
+
S_r\nabla\cdot v_s
+
\nabla\cdot(n_l\bar{w}_{ls})
=0
```

Pore-air pressure has analogous terms involving air compressibility and `1-S_r`.

## 5. Momentum and drag

General phase momentum:

```math
\bar{\rho}^{\alpha}
\frac{d^\alpha v^{\alpha}}{dt}
=
\nabla\cdot\bar{\sigma}^{\alpha}
+
\bar{\rho}^{\alpha}b
-
\sum R^{\alpha\beta}
```

Drag force:

```math
R^{\alpha\beta}
=
\frac{\bar{\rho}^{\alpha}g}{k^{\alpha}}
n^{\alpha}\bar{w}_{\alpha\beta}
-
p^{\alpha}\nabla n^{\alpha}
```

## 6. Unsaturated mechanical coupling

Key mechanical variable:

```text
suction = p_a - p_l
```

The soil strength depends on suction and saturation. Rainfall reduces suction, causing shear strength reduction and slope failure.

Implementation caution:

```text
Do not implement this as simply hydrostatic p_w added to dry Drucker-Prager stress.
```

The constitutive model must use an unsaturated effective stress/suction-dependent strength law.

## 7. Adaptive two-timescale scheme

The paper uses:

```text
dt_s = solid/mechanics time step
dt_l = liquid/seepage time step
```

with fully coupled or loosely coupled subcycling.

Implementation implication:

- Current DualSPHysics uses one global time step.
- A two-timescale loop requires new time-loop infrastructure.
- Start with a single-time-step prototype first.

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

## 8. Required fields

```cpp
PoreWaterPressure
PoreAirPressure
DegreeSaturation
Porosity
WaterRelativeVelocity
AirRelativeVelocity
HydraulicConductivityWater
HydraulicConductivityAir
Suction
```

Possible parameters:

```text
rainfall intensity / flux
van Genuchten parameters
saturated/relative permeability
air permeability
water and air compressibility
suction-dependent strength parameters
adaptive timescale factor
```

## 9. Implementation phases

1. Do not start with the full model.
2. Implement standalone seepage using the 2021 notes.
3. Implement saturated `u-pl` coupling using the 2023 notes.
4. Add unsaturated water retention and suction.
5. Add suction-dependent strength.
6. Add rainfall boundary condition.
7. Add adaptive two-timescale loop last.

## 10. Numerical stability issues

1. Saturation and suction are stiff near transition zones.
2. Pressure/saturation overshoot creates nonphysical strength.
3. Subcycling can desynchronize stress, pressure, and saturation.
4. Rainfall flux boundary conditions are sensitive.
5. Seepage operator accuracy depends on particle disorder.
6. Porosity/permeability must be bounded during large deformation.
7. Do not mix saturated and unsaturated effective stress definitions.

## 11. Codex prompt

```text
Please do not modify files. Read @papers/lian_bui_2024_unsaturated_rainfall_slope_failure_implementation_notes.md and inspect the current code for saturation, suction, porosity, pore-water pressure, pore-air pressure, seepage operators, and adaptive time-step infrastructure. Produce a feasibility map and identify which parts should be implemented first in CPU-only mode.
```
