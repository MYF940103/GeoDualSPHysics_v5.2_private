# Implementation notes for Codex: Feng et al. (2026) GeoDualSPHysics

> Source paper: Ruofeng Feng, Jidong Zhao, Georgios Fourtakas, Benedict D. Rogers, **“GeoDualSPHysics: a high-performance SPH solver for large deformation modelling of geomaterials with two-way coupling to multi-body systems”**, *Computer Physics Communications*, 2026.
>
> Purpose: These notes are written for Codex to understand how the GeoDualSPHysics paper maps elastoplastic geomechanics algorithms onto the DualSPHysics v5.2 code architecture.
>
> Codex rule: **Treat the current Visual Studio project and existing source files as authoritative. Use this note for code navigation, implementation mapping, and safe CPU/GPU modification planning.**

---

## 1. What this paper contributes

GeoDualSPHysics extends DualSPHysics v5.2 to simulate large-deformation geomaterials and their coupling with rigid/multibody systems.

Main contributions:

1. A GeoDualSPHysics branch based on DualSPHysics v5.2.
2. C++/CUDA/OpenMP implementation for geomaterial SPH.
3. Drucker–Prager elastoplastic material model.
4. Semi-implicit stress update algorithm.
5. Stress tensor, stress-rate tensor, and equivalent deviatoric plastic strain fields.
6. Stress diffusion / noise-free stress treatment.
7. Particle shifting retained and adapted for geomaterials.
8. Extended modified Dynamic Boundary Condition (mDBC) for geomaterial boundaries.
9. Two-way coupling to Project Chrono through DSPHChronoLib.
10. GPU performance profiling and CUDA kernel mapping.

---

## 2. SPH fundamentals

### 2.1 Kernel interpolation

Integral approximation:

```math
\langle f(\mathbf{x})\rangle
=
\int_{\Omega}
f(\mathbf{x}')
W(\mathbf{x}-\mathbf{x}',h)
d\mathbf{x}'
```

Discrete approximation:

```math
\langle f(\mathbf{x})\rangle_i
=
\sum_{j=1}^{N}
f_j W(\mathbf{x}_i-\mathbf{x}_j,h)V_j
```

where:

- `W`: smoothing kernel.
- `h`: smoothing length.
- `V_j`: particle volume.
- `N`: number of neighbors.

### 2.2 Kernel

The paper uses the Wendland C2 kernel:

```math
W(q,h)
=
\alpha_d
\left(1-\frac{q}{2}\right)^4(2q+1),
\qquad
0\le q\le 2
```

and

```math
W(q,h)=0,\qquad q>2.
```

where:

```math
q=\frac{|\mathbf{x}-\mathbf{x}'|}{h}.
```

Normalization constants:

```text
1D: alpha_d = 3/(4h)
2D: alpha_d = 7/(4*pi*h^2)
3D: alpha_d = 21/(16*pi*h^3)
```

---

## 3. Governing equations

### 3.1 Continuum equations

Mass conservation:

```math
\frac{d\rho}{dt}
=
-\rho\nabla\cdot\mathbf{v}
```

Momentum balance:

```math
\frac{d\mathbf{v}}{dt}
=
\frac{1}{\rho}\nabla\cdot\boldsymbol{\sigma}
+
\mathbf{b}
```

where:

- `rho`: density.
- `v`: velocity.
- `sigma`: Cauchy stress tensor.
- `b`: body force per unit volume or acceleration term depending on implementation convention.

### 3.2 SPH-discretized equations

Density evolution:

```math
\left\langle
\frac{d\rho}{dt}
\right\rangle_i
=
\rho_i
\sum_{j=1}^{N}
\frac{m_j}{\rho_j}
(v_i^\alpha-v_j^\alpha)
\frac{\partial W_{ij}}{\partial x_i^\alpha}
```

Momentum:

```math
\left\langle
\frac{dv^\alpha}{dt}
\right\rangle_i
=
\frac{1}{\rho_i}
\sum_{j=1}^{N}
\frac{m_j}{\rho_j}
(\sigma_i^{\alpha\beta}+\sigma_j^{\alpha\beta})
\frac{\partial W_{ij}}{\partial x_i^\beta}
+
g^\alpha
```

Strain rate:

```math
\left\langle
\dot{\varepsilon}^{\alpha\beta}
\right\rangle_i
=
\frac{1}{2}
\left[
\sum_j
\frac{m_j}{\rho_j}
(v_j^\alpha-v_i^\alpha)
\frac{\partial W_{ij}}{\partial x_i^\beta}
+
\sum_j
\frac{m_j}{\rho_j}
(v_j^\beta-v_i^\beta)
\frac{\partial W_{ij}}{\partial x_i^\alpha}
\right]
```

Spin rate:

```math
\left\langle
\dot{\omega}^{\alpha\beta}
\right\rangle_i
=
\frac{1}{2}
\left[
\sum_j
\frac{m_j}{\rho_j}
(v_j^\alpha-v_i^\alpha)
\frac{\partial W_{ij}}{\partial x_i^\beta}
-
\sum_j
\frac{m_j}{\rho_j}
(v_j^\beta-v_i^\beta)
\frac{\partial W_{ij}}{\partial x_i^\alpha}
\right]
```

Position update:

```math
\frac{dx_i^\alpha}{dt}
=
v_i^\alpha
```

---

## 4. Constitutive model

### 4.1 Jaumann stress-rate equation

GeoDualSPHysics uses a Jaumann-rate-based elastoplastic stress update:

```math
\dot{\boldsymbol{\sigma}}
=
\mathbf{D}^{e}:\dot{\boldsymbol{\varepsilon}}
-
\dot{\boldsymbol{\omega}}\cdot\boldsymbol{\sigma}
+
\boldsymbol{\sigma}\cdot\dot{\boldsymbol{\omega}}
```

where:

- `D^e`: elastic stiffness tensor.
- `epsilon_dot`: strain-rate tensor.
- `omega_dot`: spin-rate tensor.
- `sigma`: stress tensor.

### 4.2 Drucker–Prager yield function

Yield function:

```math
f
=
\alpha_\phi I_1
+
\sqrt{J_2}
-
k_c
```

Plastic potential:

```math
g
=
\alpha_\psi I_1
+
\sqrt{J_2}
```

where:

- `I1`: first stress invariant.
- `J2`: second deviatoric stress invariant.
- `alpha_phi`: friction coefficient in Drucker–Prager model.
- `alpha_psi`: dilation coefficient.
- `kc`: cohesion parameter.
- `phi`: friction angle.
- `psi`: dilation angle.
- `c`: cohesion.

### 4.3 Plane-strain constants

```math
\alpha_\phi
=
\frac{\tan\phi}
{\sqrt{9+12\tan^2\phi}}
```

```math
k_c
=
\frac{3c}
{\sqrt{9+12\tan^2\phi}}
```

### 4.4 3D circumscribed Mohr–Coulomb mapping

```math
\alpha_\phi
=
\frac{2\sin\phi}
{\sqrt{3}(3-\sin\phi)}
```

```math
k_c
=
\frac{6c\cos\phi}
{\sqrt{3}(3-\sin\phi)}
```

### 4.5 3D middle circumscribed mapping

```math
\alpha_\phi
=
\frac{2\sin\phi}
{\sqrt{3}(3+\sin\phi)}
```

```math
k_c
=
\frac{6c\cos\phi}
{\sqrt{3}(3+\sin\phi)}
```

---

## 5. Semi-implicit stress update algorithm

The paper describes a semi-implicit stress update following Bui and Nguyen.

### 5.1 Interaction force stage

For each particle:

```text
1. Compute strain-rate tensor.
2. Compute spin-rate tensor.
3. Compute elastic stress rate:
   sigma_dot = De : epsilon_dot - omega_dot · sigma + sigma · omega_dot.
```

### 5.2 Time integration stage

For each particle:

```text
1. Compute trial stress:
   sigma_trial(t+dt) = sigma(t) + sigma_dot * dt.

2. Keep previous equivalent deviatoric plastic strain:
   kappa(t+dt) = kappa(t).

3. Check yield condition:
   f(sigma_trial, kappa) < 0.

4. If elastic:
   sigma(t+dt) = sigma_trial
   kappa(t+dt) = kappa(t)

5. If plastic:
   perform return mapping
   sigma(t+dt) = sigma_trial - d_sigma_p
   kappa(t+dt) = kappa(t) + d_kappa
```

### 5.3 Implementation mapping

The paper states that the time integration is implemented through:

```text
CPU:
  JSphCpu::ComputeVerlet
  JSphCpu::ComputeSymplecticPre
  JSphCpu::ComputeSymplecticCorr

GPU:
  KerComputeStepVerlet
  KerComputeStepSymplecticPre
  KerComputeStepSymplecticCorr
```

Codex should inspect these functions before changing any stress update logic.

---

## 6. Artificial viscosity

Artificial viscosity is introduced to stabilize oscillations.

Momentum with artificial viscosity:

```math
\left\langle
\frac{dv^\alpha}{dt}
\right\rangle_i
=
\sum_j
m_j
\left(
\frac{\sigma_i^{\alpha\beta}+\sigma_j^{\alpha\beta}}
{\rho_i\rho_j}
-
\Pi_{ij}\delta^{\alpha\beta}
\right)
\frac{\partial W_{ij}}{\partial x_i^\beta}
+
g^\alpha
```

Viscosity term:

```math
\Pi_{ij}
=
\begin{cases}
-\frac{\alpha c_s\mu_{ij}}{\rho_{ij}},
&
v_{ij}^\beta x_{ij}^\beta \le 0,
\\
0,
&
v_{ij}^\beta x_{ij}^\beta > 0,
\end{cases}
```

```math
\mu_{ij}
=
\frac{h v_{ij}^\beta x_{ij}^\beta}
{x_{ij}^\gamma x_{ij}^\gamma+\eta^2}
```

```math
\rho_{ij}
=
0.5(\rho_i+\rho_j)
```

Sound speed:

```math
c_s
=
\sqrt{\frac{4G/3+K}{\rho}}
```

Typical parameters:

```text
alpha = 0.1
eta = 0.1h
```

Implementation caution:

- Artificial viscosity stabilizes numerical oscillations.
- It should not be used as the primary treatment for tensile instability or stress noise.

---

## 7. Stress diffusion / noise-free stress treatment

### 7.1 Stress-rate equation with diffusion

```math
\frac{d\sigma_i^{\alpha\beta}}{dt}
=
D_e^{\alpha\beta\gamma l}\dot{\varepsilon}_i^{\gamma l}
-
\dot{\omega}^{\alpha\gamma}\sigma^{\gamma\beta}
+
\sigma^{\alpha\gamma}\dot{\omega}^{\gamma\beta}
+
D_i^{\alpha\beta}
```

### 7.2 General diffusion term

```math
D_i^{\alpha\beta}
=
2\zeta h c_s
\sum_j
\psi_{ij}^{\alpha\beta}
\frac{x_{ij}^{\gamma}}
{x_{ij}^{l}x_{ij}^{l}+\eta^2}
\frac{\partial W_{ij}}{\partial x_i^\gamma}
\frac{m_j}{\rho_j}
```

where:

- `zeta`: stress diffusion coefficient, often `0.1`.
- `psi_ij`: diffusion operator.
- `cs`: solid sound speed.

### 7.3 Basic diffusion operator

```math
\psi_{ij}^{\alpha\beta}
=
\sigma_i^{\alpha\beta}
-
\sigma_j^{\alpha\beta}
```

### 7.4 Gravity-aware noise-free diffusion

For off-diagonal components:

```math
\psi_{ij}^{\alpha\beta}
=
\sigma_{ij}^{\alpha\beta},
\qquad
\alpha\ne\beta.
```

For normal components:

```math
\psi_{ij}^{xx}
=
\sigma_{ij}^{xx}
-
K_0\rho_0gz_{ij}
```

```math
\psi_{ij}^{yy}
=
\sigma_{ij}^{yy}
-
K_0\rho_0gz_{ij}
```

```math
\psi_{ij}^{zz}
=
\sigma_{ij}^{zz}
-
\rho_0gz_{ij}
```

with

```math
K_0
=
1-\sin\phi.
```

Implementation caution:

- Stress diffusion reduces high-frequency stress noise.
- It may smear shear bands if too strong.
- Gravity-aware form is most appropriate for gravity-dominated geomaterial flows.
- Before changing it, Codex should inspect current parameters and XML controls.

---

## 8. Particle shifting

GeoDualSPHysics retains DualSPHysics particle shifting for geomaterials.

### 8.1 Shifting distance

```math
\delta x_i^\alpha
=
\begin{cases}
-
A_{FSC,i} A h v_{mag,i}\Delta t
\frac{\partial C_i}{\partial x^\alpha},
&
\partial_\alpha x_i^\alpha > A_{FST},
\\
0,
&
\text{otherwise}.
\end{cases}
```

Velocity magnitude:

```math
v_{mag,i}
=
\sqrt{v_i^\alpha v_i^\alpha}.
```

### 8.2 Free-surface correction

```math
A_{FSC,i}
=
\frac{\partial_\alpha x_i^\alpha - A_{FST}}
{A_{FSM}-A_{FST}}
```

Maximum divergence:

```math
A_{FSM}
=
\begin{cases}
2, & 2D,\\
3, & 3D.
\end{cases}
```

Recommended free-surface threshold:

```text
AFST = 1.5 for 2D
AFST = 2.75 for 3D
```

Default shifting coefficient:

```text
A = 2
```

### 8.3 Files to inspect

```text
source/JSphShifting.cpp
source/JSphShifting.h
source/JSphShifting_ker.cu
source/JSphCpu.cpp
source/JSphGpu.cpp
```

Implementation caution:

- Shifting controls particle disorder and tensile clumping.
- It can affect volume, stress consistency, and free-surface behavior.
- If new scalar/tensor fields are added, Codex must check whether they need shifting-aware transport or correction.

---

## 9. Extended mDBC boundary treatment

### 9.1 Concept

GeoDualSPHysics extends the modified Dynamic Boundary Condition for geomaterial SPH.

- Several layers of dummy boundary particles complete kernel support.
- For each boundary particle, a ghost node is projected into the computational domain.
- Field variables are interpolated at the ghost node from material particles.
- Boundary-particle values are extrapolated from ghost-node values.

### 9.2 First-order consistent reconstruction

For ghost stress and gradients:

```math
\mathbf{A}_g
\begin{bmatrix}
\sigma_g^{\alpha\beta}\\
\partial_x\sigma_g^{\alpha\beta}\\
\partial_y\sigma_g^{\alpha\beta}\\
\partial_z\sigma_g^{\alpha\beta}
\end{bmatrix}
=
\begin{bmatrix}
\sum_j \sigma_j^{\alpha\beta} W_{gj}V_j\\
\sum_j \sigma_j^{\alpha\beta} \partial_xW_{gj}V_j\\
\sum_j \sigma_j^{\alpha\beta} \partial_yW_{gj}V_j\\
\sum_j \sigma_j^{\alpha\beta} \partial_zW_{gj}V_j
\end{bmatrix}
```

Boundary stress extrapolation:

```math
\sigma_b^{\alpha\beta}
=
\sigma_g^{\alpha\beta}
+
(\mathbf{x}_b-\mathbf{x}_g)\cdot\nabla\sigma_g^{\alpha\beta}
```

### 9.3 Implementation mapping

The paper maps boundary correction to:

```text
CPU:
  JSphCpu::Interaction_CdbcCorrection
  JSphCpu::Interaction_MdbcCorrection

GPU:
  KerInteractionCdbcCorrection
  KerInteractionMdbcCorrection
```

Likely files:

```text
source/JSphCpu.cpp
source/JSphCpuSingle.cpp
source/JSphGpuSingle.cpp
source/JSphGpu_ker.cu
source/JSph.cpp
```

Implementation caution:

- Do not replace mDBC globally.
- If adding new material fields, boundary/ghost-node values may also need reconstruction.
- mDBC changes can affect impact force calculation and rigid-body coupling.

---

## 10. Code documentation and function mapping

The paper’s code documentation indicates that GeoDualSPHysics modifies DualSPHysics v5.2 in three major areas.

### 10.1 Boundary treatment

```text
JSphCpu::Interaction_CdbcCorrection
JSphCpu::Interaction_MdbcCorrection
KerInteractionCdbcCorrection
KerInteractionMdbcCorrection
```

Purpose:

- boundary-material interaction;
- rigid body-material interaction;
- stress and velocity conditions on solid boundaries and rigid bodies.

### 10.2 Particle interaction

```text
JSphCpu::InteractionForcesFluid
KerInteractionForcesFluid
```

Purpose:

- material-material interaction;
- material-boundary interaction;
- material-rigid-body interaction;
- governing equations for density, momentum, strain rate, spin rate;
- shifting distance;
- stress diffusion term;
- forces on rigid bodies.

### 10.3 Time integration

```text
JSphCpu::ComputeVerlet
JSphCpu::ComputeSymplecticPre
JSphCpu::ComputeSymplecticCorr
KerComputeStepVerlet
KerComputeStepSymplecticPre
KerComputeStepSymplecticCorr
```

Purpose:

- update stress;
- update equivalent deviatoric plastic strain;
- apply semi-implicit stress update algorithm.

---

## 11. Added variables and memory implications

GeoDualSPHysics adds at least:

```text
stress tensor sigma
stress-rate tensor d_sigma/dt
equivalent deviatoric plastic strain kappa
```

This requires changes in:

```text
CPU memory allocation
GPU memory allocation
CPU-GPU data transfer
cell-linked list handling
XML material-property loading
output and post-processing
```

Codex should inspect:

```text
source/JArraysCpu.cpp
source/JArraysGpu.cpp
source/JDataArrays.cpp
source/JPartDataBi4.cpp
source/JPartFloatBi4.cpp
source/JOutputCsv.cpp
source/JCaseProperties.cpp
source/JXml.cpp
source/JSphCfgRun.cpp
```

---

## 12. Coupling with Project Chrono

### 12.1 Coupling workflow

The paper describes two-way coupling with Project Chrono through DSPHChronoLib.

Algorithm:

```text
Interaction_Forces:
  compute forces exerted on rigid-body particles.

RunFloating:
  compute rigid-body linear and angular accelerations.

DSPHChronoLib:
  compute total force and torque.
  transfer force, torque, and dtSPH to Project Chrono.

Project Chrono:
  detect collisions.
  apply mechanical constraints.
  compute rigid-body velocity, angular velocity, and center-of-mass position.

FtUpdate:
  update positions of rigid-body particles in SPH.
```

### 12.2 Files to inspect

```text
source/JChronoObjects.cpp
source/JSphCpu.cpp
source/JSphGpu_ker.cu
source/JSphCpuSingle.cpp
source/JSphGpuSingle.cpp
lib/DSPHChronoLib
```

Implementation caution:

- Do not modify Chrono coupling unless the material force calculation or rigid-body boundary treatment is the actual target.
- Changes to material-boundary stress may affect impact forces and rigid-body motion.

---

## 13. GPU implementation and performance

### 13.1 CUDA kernel groups

Important kernels:

```text
KerInteract
KerMDBC
KerSymPre
KerSymCorr
KerVerlet
```

The paper notes that GeoDualSPHysics kernels can have slightly lower occupancy because additional stress arrays and stress calculations increase register usage.

### 13.2 Block size configuration

GeoDualSPHysics inherits DualSPHysics options:

```text
-blocksize:0  fixed 128 threads per block
-blocksize:1  CUDA occupancy calculator
-blocksize:2  empirically selected optimal block size
```

Number of blocks:

```text
numBlocks = (particleNumber + blockSize - 1) / blockSize
```

Implementation caution:

- Port CPU changes to GPU only after CPU validation.
- Extra arrays increase memory traffic.
- Avoid unnecessary temporaries in CUDA kernels.
- Use Nsight profiling only after numerical correctness is established.

---

## 14. Mapping to the current user project

Current project root:

```text
D:\MYF\SPH\GeoDualSPHysics_v5.2\src
```

Known VS Code build tasks:

```text
CPU Debug:
  Build DualSPHysics5ReCpu Debug x64
  DebugCPU|x64

CPU Release:
  Build DualSPHysics5ReCpu Release x64
  ReleaseCPU|x64

GPU Debug:
  Build DualSPHysics5Re GPU Debug x64
  Debug|x64

GPU Release:
  Build DualSPHysics5Re GPU Release x64
  Release|x64
```

Known debug configurations:

```text
Debug CPU slope45 ImpactForces
Debug GPU slope45 ImpactForces
```

Current debug case:

```text
D:\MYF\SPH\GeoDualSPHysics_v5.2\examples\myf\02_ImpactForces
```

---

## 15. Codex file/function priority list

### 15.1 Stress update

```text
source/JSphCpu.cpp
source/JSphCpuSingle.cpp
source/JSphGpu.cpp
source/JSphGpuSingle.cpp
source/JSphGpu_ker.cu
source/JSphGpuSimple_ker.cu
```

Search keywords:

```text
Stress
Sigma
Sps
Kappa
Jaumann
Strain
Spin
Yield
Plastic
Return
Drucker
Prager
```

### 15.2 Stress diffusion

```text
source/JSphCpu.cpp
source/JSphGpu_ker.cu
source/JSphCpuSingle.cpp
source/JSphGpuSingle.cpp
```

Search keywords:

```text
Diffusion
StressDiff
zeta
K0
Jaky
SpsGrad
```

### 15.3 mDBC

```text
source/JSph.cpp
source/JSphCpu.cpp
source/JSphCpuSingle.cpp
source/JSphGpuSingle.cpp
source/JSphGpu_ker.cu
```

Search keywords:

```text
Mdbc
Cdbc
Interaction_MdbcCorrection
Interaction_CdbcCorrection
KerInteractionMdbcCorrection
Ghost
Normal
Bound
```

### 15.4 Shifting

```text
source/JSphShifting.cpp
source/JSphShifting.h
source/JSphShifting_ker.cu
source/JSphCpu.cpp
source/JSphGpu.cpp
```

Search keywords:

```text
Shifting
ShiftPosfs
RunShifting
AFST
AFSM
AFSC
```

---

## 16. Safe Codex workflow

### 16.1 Read-only inspection

```text
请不要修改任何文件。请阅读 @papers/feng2026_geodualsphysics_implementation_notes.md，并检查 source/JSphCpu.cpp、source/JSphCpuSingle.cpp、source/JSphGpu_ker.cu。请判断当前代码中 stress update、stress diffusion、mDBC 和 shifting 的实现位置。
```

### 16.2 Variable mapping

```text
请不要修改任何文件。请建立 Feng 2026 变量到当前代码变量的映射表，包括 stress tensor、stress-rate tensor、equivalent plastic strain、strain rate、spin rate、Drucker–Prager 参数、stress diffusion 参数、mDBC ghost-node变量、shifting变量。
```

### 16.3 CPU-only patch rule

```text
可以修改，但只修改 CPU 路径。修改前列出计划，修改后运行默认 CPU Debug build task。不要改 GPU、.sln、.vcxproj 或 XML schema，除非我明确要求。
```

### 16.4 GPU port rule

```text
请在 CPU 版本验证成功后，再将同一公式移植到 GPU。保持 CPU/GPU 公式一致，修改后运行 GPU Debug build task。
```

---

## 17. Numerical stability checklist

Before accepting code modifications:

1. Check stress sign convention.
2. Check current stress update and return mapping.
3. Check whether stress diffusion is already enabled.
4. Do not add duplicate stress smoothing.
5. Check interaction with shifting.
6. Check boundary stress reconstruction through mDBC.
7. Test CPU Debug first.
8. Test GPU Debug second.
9. Use Release only for production runs.
10. Compare CPU/GPU results on a small case.

Specific risks:

```text
- Stress diffusion may smear shear bands.
- Shifting may affect stress/volume consistency.
- mDBC changes may affect impact force calculation.
- Additional GPU stress arrays may reduce occupancy.
- Artificial viscosity should not substitute for tensile-instability treatment.
```

---

## 18. Recommended implementation order

Use this order for GeoDualSPHysics modifications:

```text
1. Confirm existing stress tensor and stress-rate arrays.
2. Confirm existing Drucker–Prager stress update.
3. Confirm return mapping and plastic strain update.
4. Confirm stress diffusion / noise-free stress treatment.
5. Confirm mDBC ghost-node reconstruction.
6. Confirm shifting handling for stress and plastic strain.
7. Modify CPU path only.
8. Build CPU Debug.
9. Validate small case.
10. Port to GPU.
11. Build GPU Debug.
12. Generate GPU Release for production simulation.
```

Avoid:

```text
- Direct CUDA-first modifications.
- Replacing the solver architecture.
- Rewriting mDBC globally.
- Adding new fields without memory/output planning.
- Combining multiple stabilizers without isolated tests.
```

---

## 19. Short summary for Codex

Feng et al. (2026) is the implementation architecture paper for GeoDualSPHysics. It explains how DualSPHysics v5.2 is extended with Drucker–Prager elastoplastic stress update, stress diffusion/noise-free stress treatment, shifting, extended mDBC, and Chrono coupling. It also maps the main implementations to CPU and CUDA functions. Use this paper to locate where algorithms live in the code and to plan CPU-first, GPU-second modifications.
