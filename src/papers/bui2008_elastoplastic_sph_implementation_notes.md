# Implementation notes for Codex: Bui et al. (2008) elastoplastic SPH for geomaterials

> Source paper: Ha H. Bui, Ryoichi Fukagawa, Kazunari Sako, Shintaro Ohno, **“Lagrangian meshfree particles method (SPH) for large deformation and failure flows of geomaterial using elastic–plastic soil constitutive model”**, *International Journal for Numerical and Analytical Methods in Geomechanics*, 2008.
>
> Purpose: These notes are written for Codex to understand the paper in implementation terms before modifying GeoDualSPHysics/DualSPHysics code.
>
> Codex rule: **Do not modify source files directly from this note. First map paper variables to current code variables, identify existing implementation status, then propose a minimal CPU-first plan.**

---

## 1. What this paper contributes

Bui et al. (2008) provides one of the foundational SPH formulations for large-deformation geomaterial failure using an elastoplastic soil constitutive model.

Main contributions:

1. Uses SPH to solve large deformation and post-failure flow of geomaterials.
2. Implements an elastic–perfectly plastic **Drucker–Prager** model.
3. Supports associated and non-associated plastic flow.
4. Calculates hydrostatic pressure / mean stress directly from the constitutive model, rather than by a fluid-like equation of state.
5. Identifies tensile instability as a major problem in elastoplastic SPH.
6. Uses:
   - tension cracking treatment for non-cohesive soil;
   - stress scaling back for return to the yield surface;
   - artificial stress method for cohesive soil tensile instability.
7. Applies the formulation to soil collapse and bearing capacity problems.

---

## 2. Governing equations

### 2.1 Mass balance

The Lagrangian mass conservation equation is

```math
\frac{D\rho}{Dt}
=
-\rho \frac{\partial v^\alpha}{\partial x^\alpha}
```

where:

- `rho`: soil density.
- `v^alpha`: velocity component.
- `x^alpha`: spatial coordinate.
- `D/Dt`: material derivative.
- Greek indices denote Cartesian components and repeated indices imply summation.

The paper notes that the continuity equation can be optional if density is kept constant. Retaining it can represent changes of void ratio or porosity.

### 2.2 Momentum balance

The momentum equation is

```math
\frac{D v^\alpha}{Dt}
=
\frac{1}{\rho}
\frac{\partial \sigma^{\alpha\beta}}{\partial x^\beta}
+
f^\alpha
```

where:

- `sigma^{alpha beta}`: total stress tensor of soil.
- `f^alpha`: external acceleration, usually gravity.
- In this paper, the total stress tensor is treated as the effective stress tensor of soil particles.

---

## 3. Stress tensor and pressure convention

The paper decomposes total stress as

```math
\sigma^{\alpha\beta}
=
-p\delta^{\alpha\beta}
+
s^{\alpha\beta}
```

where:

- `p`: hydrostatic pressure / mean stress.
- `s^{alpha beta}`: deviatoric stress tensor.
- `delta^{alpha beta}`: Kronecker delta.

The pressure is computed from stress components:

```math
p
=
-\frac{1}{3}
(\sigma^{xx}+\sigma^{yy}+\sigma^{zz})
```

Important convention:

```text
Compressive stress is negative in this paper.
```

Codex must check the sign convention in GeoDualSPHysics before applying formulas.

Implementation caution:

- Do **not** map DualSPHysics fluid pressure directly to this soil pressure without checking the existing GeoDualSPHysics stress convention.
- In geomaterial SPH, pressure should come from the constitutive model, not from a weakly compressible fluid equation of state.

---

## 4. Elastic–perfectly plastic model

### 4.1 Strain-rate decomposition

Total strain rate:

```math
\dot{\varepsilon}^{\alpha\beta}
=
\dot{\varepsilon}^{e,\alpha\beta}
+
\dot{\varepsilon}^{p,\alpha\beta}
```

Elastic strain-rate tensor from generalized Hooke law:

```math
\dot{\varepsilon}^{e,\alpha\beta}
=
\frac{\dot{s}^{\alpha\beta}}{2G}
+
\frac{1-2\nu}{3E}
\dot{\sigma}^{\gamma\gamma}
\delta^{\alpha\beta}
```

where:

- `E`: Young’s modulus.
- `nu`: Poisson’s ratio.
- `G`: shear modulus.
- `s`: deviatoric stress.
- `sigma^{gamma gamma}`: trace of stress tensor.

Plastic flow rule:

```math
\dot{\varepsilon}^{p,\alpha\beta}
=
\dot{\lambda}
\frac{\partial g}{\partial\sigma^{\alpha\beta}}
```

where:

- `lambda`: plastic multiplier.
- `g`: plastic potential function.
- associated flow: `g = f`.
- non-associated flow: `g != f`.

### 4.2 Elastic moduli

```math
K
=
\frac{E}{3(1-2\nu)}
```

```math
G
=
\frac{E}{2(1+\nu)}
```

where:

- `K`: elastic bulk modulus.
- `G`: shear modulus.

### 4.3 General elastoplastic stress-rate relation

```math
\dot{\sigma}^{\alpha\beta}
=
2G\dot{e}^{\alpha\beta}
+
K\dot{\varepsilon}^{\gamma\gamma}\delta^{\alpha\beta}
-
\dot{\lambda}
\left[
\left(K-\frac{2G}{3}\right)
\frac{\partial g}{\partial\sigma^{mn}}
\delta^{mn}\delta^{\alpha\beta}
+
2G
\frac{\partial g}{\partial\sigma^{\alpha\beta}}
\right]
```

where:

```math
\dot{e}^{\alpha\beta}
=
\dot{\varepsilon}^{\alpha\beta}
-
\frac{1}{3}
\dot{\varepsilon}^{\gamma\gamma}
\delta^{\alpha\beta}
```

---

## 5. Drucker–Prager yield model

### 5.1 Yield criterion

```math
f(I_1,J_2)
=
\sqrt{J_2}
+
\alpha_\phi I_1
-
k_c
=
0
```

with

```math
I_1
=
\sigma^{xx}+\sigma^{yy}+\sigma^{zz}
```

and

```math
J_2
=
\frac{1}{2}
s^{\alpha\beta}s^{\alpha\beta}
```

where:

- `I1`: first stress invariant.
- `J2`: second invariant of deviatoric stress.
- `alpha_phi`: Drucker–Prager friction parameter.
- `kc`: cohesion-related intercept.

### 5.2 Plane-strain Drucker–Prager constants

For plane strain:

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

where:

- `phi`: internal friction angle.
- `c`: cohesion.

---

## 6. Associated and non-associated flow rules

### 6.1 Associated flow

Associated plastic potential:

```math
g
=
\sqrt{J_2}
+
\alpha_\phi I_1
-
k_c
```

Stress-rate equation:

```math
\dot{\sigma}^{\alpha\beta}
=
2G\dot{e}^{\alpha\beta}
+
K\dot{\varepsilon}^{\gamma\gamma}\delta^{\alpha\beta}
-
\dot{\lambda}
\left(
3\alpha_\phi K\delta^{\alpha\beta}
+
\frac{G}{\sqrt{J_2}}s^{\alpha\beta}
\right)
```

Plastic multiplier rate:

```math
\dot{\lambda}
=
\frac{
3\alpha_\phi K\dot{\varepsilon}^{\gamma\gamma}
+
(G/\sqrt{J_2})s^{\alpha\beta}\dot{\varepsilon}^{\alpha\beta}
}{
9\alpha_\phi^2K+G
}
```

### 6.2 Non-associated flow

Non-associated plastic potential:

```math
g
=
\sqrt{J_2}
+
3I_1\sin\psi
```

where:

- `psi`: dilatancy angle.
- `psi = 0`: plastically incompressible non-associated flow.

Stress-rate equation:

```math
\dot{\sigma}^{\alpha\beta}
=
2G\dot{e}^{\alpha\beta}
+
K\dot{\varepsilon}^{\gamma\gamma}\delta^{\alpha\beta}
-
\dot{\lambda}
\left(
9K\sin\psi\,\delta^{\alpha\beta}
+
\frac{G}{\sqrt{J_2}}s^{\alpha\beta}
\right)
```

Plastic multiplier rate:

```math
\dot{\lambda}
=
\frac{
3\alpha_\phi K\dot{\varepsilon}^{\gamma\gamma}
+
(G/\sqrt{J_2})s^{\alpha\beta}\dot{\varepsilon}^{\alpha\beta}
}{
27\alpha_\phi K\sin\psi+G
}
```

---

## 7. Jaumann stress rate

For large deformation, rigid-body rotation must not create artificial stress. The paper uses the Jaumann stress rate:

```math
\hat{\dot{\sigma}}^{\alpha\beta}
=
\dot{\sigma}^{\alpha\beta}
-
\sigma^{\alpha\gamma}\dot{\omega}^{\beta\gamma}
-
\sigma^{\gamma\beta}\dot{\omega}^{\alpha\gamma}
```

Spin-rate tensor:

```math
\dot{\omega}^{\alpha\beta}
=
\frac{1}{2}
\left(
\frac{\partial v^\alpha}{\partial x^\beta}
-
\frac{\partial v^\beta}{\partial x^\alpha}
\right)
```

Implementation caution:

- GeoDualSPHysics may already compute strain rate, spin rate, and stress rate.
- Codex must check current implementations before adding new Jaumann terms.
- Do not add a second rotation correction if one already exists.

---

## 8. SPH discretization

### 8.1 Kernel interpolation

SPH field approximation:

```math
\langle f(\mathbf{x})\rangle
=
\int_\Omega
f(\mathbf{x}')
W(\mathbf{x}-\mathbf{x}',h)
d\mathbf{x}'
```

Discrete approximation:

```math
\langle f_i\rangle
=
\sum_j
\frac{m_j}{\rho_j}
f_j W_{ij}
```

### 8.2 Velocity gradient, strain rate, and spin rate

Strain rate:

```math
\dot{\varepsilon}^{\alpha\beta}_i
=
\frac{1}{2}
\left[
\sum_j\frac{m_j}{\rho_j}
(v_j^\alpha-v_i^\alpha)
\frac{\partial W_{ij}}{\partial x_i^\beta}
+
\sum_j\frac{m_j}{\rho_j}
(v_j^\beta-v_i^\beta)
\frac{\partial W_{ij}}{\partial x_i^\alpha}
\right]
```

Spin rate:

```math
\dot{\omega}^{\alpha\beta}_i
=
\frac{1}{2}
\left[
\sum_j\frac{m_j}{\rho_j}
(v_j^\alpha-v_i^\alpha)
\frac{\partial W_{ij}}{\partial x_i^\beta}
-
\sum_j\frac{m_j}{\rho_j}
(v_j^\beta-v_i^\beta)
\frac{\partial W_{ij}}{\partial x_i^\alpha}
\right]
```

### 8.3 Momentum equation in SPH form

```math
\frac{Dv_i^\alpha}{Dt}
=
\sum_j m_j
\left(
\frac{\sigma_i^{\alpha\beta}}{\rho_i^2}
+
\frac{\sigma_j^{\alpha\beta}}{\rho_j^2}
\right)
\frac{\partial W_{ij}}{\partial x_i^\beta}
+
g^\alpha
```

---

## 9. Return mapping and numerical plasticity corrections

### 9.1 Tension cracking treatment

If the stress state exceeds the apex of the yield surface:

```math
-\alpha_\phi I_1^n+k_c<0
```

adjust normal stresses to the apex:

```math
\bar{\sigma}_{xx}^{n}
=
\sigma_{xx}^{n}
-
\frac{1}{3}
\left(
I_1^n-\frac{k_c}{\alpha_\phi}
\right)
```

```math
\bar{\sigma}_{yy}^{n}
=
\sigma_{yy}^{n}
-
\frac{1}{3}
\left(
I_1^n-\frac{k_c}{\alpha_\phi}
\right)
```

```math
\bar{\sigma}_{zz}^{n}
=
\sigma_{zz}^{n}
-
\frac{1}{3}
\left(
I_1^n-\frac{k_c}{\alpha_\phi}
\right)
```

Shear stresses remain unchanged.

Implementation meaning:

- Works well for non-cohesive soil.
- Not enough for cohesive soil because tensile instability can still occur.

### 9.2 Stress scaling back procedure

If the stress state exceeds the yield surface:

```math
-\alpha_\phi I_1^n+k_c
<
\sqrt{J_2^n}
```

define

```math
r^n
=
\frac{-\alpha_\phi I_1^n+k_c}
{\sqrt{J_2^n}}
```

Then reduce deviatoric stresses:

```math
\bar{\sigma}_{xx}^{n}
=
r^n s_{xx}^{n}
+
\frac{1}{3}I_1^n
```

```math
\bar{\sigma}_{yy}^{n}
=
r^n s_{yy}^{n}
+
\frac{1}{3}I_1^n
```

```math
\bar{\sigma}_{zz}^{n}
=
r^n s_{zz}^{n}
+
\frac{1}{3}I_1^n
```

```math
\bar{\sigma}_{xy}^{n}
=
r^n s_{xy}^{n}
```

```math
\bar{\sigma}_{xz}^{n}
=
r^n s_{xz}^{n}
```

```math
\bar{\sigma}_{yz}^{n}
=
r^n s_{yz}^{n}
```

Implementation caution:

- Apply only if the current code does not already implement equivalent return mapping.
- Avoid multiple return-mapping corrections in the same step.

---

## 10. Artificial viscosity

Artificial viscosity is used to damp numerical oscillations.

Modified momentum form:

```math
\frac{Dv_i^\alpha}{Dt}
=
\sum_j m_j
\left(
\frac{\sigma_i^{\alpha\beta}}{\rho_i^2}
+
\frac{\sigma_j^{\alpha\beta}}{\rho_j^2}
-
\Pi_{ij}\delta^{\alpha\beta}
\right)
\frac{\partial W_{ij}}{\partial x_i^\beta}
+
g^\alpha
```

Typical Monaghan-type viscosity:

```math
\Pi_{ij}
=
\begin{cases}
\frac{-\alpha c_s \mu_{ij}+\beta \mu_{ij}^2}{\rho_{ij}},
&
\mathbf{v}_{ij}\cdot\mathbf{x}_{ij}<0,
\\
0,
&
\mathbf{v}_{ij}\cdot\mathbf{x}_{ij}\ge 0.
\end{cases}
```

with

```math
\mu_{ij}
=
\frac{h\mathbf{v}_{ij}\cdot\mathbf{x}_{ij}}
{|\mathbf{x}_{ij}|^2+\eta^2}
```

Implementation caution:

- Artificial viscosity should stabilize oscillations and shocks.
- It should not be used as the main cure for tensile instability because large values alter the deformation mode.

---

## 11. Artificial stress for tensile instability

### 11.1 Why it is needed

Bui et al. report that tensile instability causes:

- unrealistic fractures;
- particle clustering;
- artificial clumps;
- severe instability in cohesive soils.

For cohesive soil, tension cracking alone is insufficient.

### 11.2 Artificial-stress momentum form

The modified momentum equation includes a repulsive artificial stress term:

```math
\frac{Dv_i^\alpha}{Dt}
=
\sum_j m_j
\left(
\frac{\sigma_i^{\alpha\beta}}{\rho_i^2}
+
\frac{\sigma_j^{\alpha\beta}}{\rho_j^2}
-
\Pi_{ij}\delta^{\alpha\beta}
+
f_{ij}^{n}
(R_i^{\alpha\beta}+R_j^{\alpha\beta})
\right)
\frac{\partial W_{ij}}{\partial x_i^\beta}
+
g^\alpha
```

with

```math
f_{ij}
=
\frac{W_{ij}}{W(d,h)}
```

where:

- `d`: initial particle spacing.
- `h`: smoothing length.
- `n`: exponent controlling the artificial stress term.
- `R_i`: artificial stress tensor.

Implementation caution:

- Only use if current GeoDualSPHysics shifting/stress diffusion does not sufficiently control tensile instability.
- Test in CPU path first.
- Do not enable simultaneously with excessive artificial viscosity without parameter isolation.

---

## 12. Boundary stress treatment

For stress at boundary points, Bui et al. compute local boundary stresses using neighboring soil particles.

Uncorrected boundary stress interpolation:

```math
P_n
=
\sum_i
\frac{m_i}{\rho_i}
P_i W_{ni}
```

Corrected form near truncated support:

```math
P_n
=
\frac{
\sum_i
\frac{m_i}{\rho_i}
P_iW_{ni}
}{
\sum_i
\frac{m_i}{\rho_i}
W_{ni}
}
```

Average boundary stress:

```math
P
=
\frac{\sum_{n=1}^{M}P_n ds_n}
{\sum_{n=1}^{M}ds_n}
```

Implementation mapping:

- Current GeoDualSPHysics uses mDBC rather than this original boundary stress treatment.
- Use Bui boundary formulas mainly for conceptual comparison, not direct replacement.

---

## 13. DualSPHysics/GeoDualSPHysics code mapping

### 13.1 Files to inspect first

```text
source/main.cpp
source/JSphCpuSingle.cpp
source/JSphCpu.cpp
source/JSphCpu.h
source/JSph.cpp
source/JSphShifting.cpp
source/JArraysCpu.cpp
source/JPartDataBi4.cpp
```

### 13.2 Likely CPU call chain

```text
main.cpp
  -> JSphCpuSingle::Run()
    -> ComputeStep()
      -> ComputeStep_Ver() or ComputeStep_Sym()
        -> Interaction_Forces()
          -> PreInteraction_Forces()
          -> JSphCpu::Interaction_Forces_ct()
             -> InteractionForcesFluid()
             -> InteractionForcesBound()
        -> ComputeVerlet() or Symplectic update
        -> RunShifting()
```

### 13.3 Variables to map before modifying code

Ask Codex to map:

```text
rho
mass
velocity
position
acceleration
stress tensor
stress rate tensor
strain rate
spin rate
I1
J2
friction angle phi
cohesion c
dilation angle psi
bulk modulus K
shear modulus G
plastic multiplier
equivalent plastic strain
artificial viscosity
artificial stress
shifting displacement
```

---

## 14. Numerical stability checklist

Before implementing or modifying anything:

1. Check stress sign convention.
2. Check whether current code already implements DP return mapping.
3. Do not add duplicate tension cracking/stress scaling.
4. Use CPU Debug first.
5. Keep artificial viscosity moderate.
6. Use artificial stress only for tensile instability tests.
7. Check interaction with shifting.
8. Check whether stress fields are shifted, diffused, or corrected.
9. Compare against small benchmark before GPU port.
10. Do not modify CUDA until CPU implementation is validated.

---

## 15. Recommended Codex prompts

### 15.1 Read-only mapping

```text
请不要修改任何文件。请阅读 @papers/bui2008_elastoplastic_sph_implementation_notes.md，并检查 source/JSphCpu.cpp 和 source/JSphCpuSingle.cpp。请建立 Bui 2008 变量与当前代码变量的映射表，包括 rho、velocity、stress tensor、strain rate、spin rate、I1、J2、cohesion、friction angle、dilation angle、bulk modulus、shear modulus、plastic strain、artificial viscosity 和 shifting。
```

### 15.2 Return mapping inspection

```text
请不要修改任何文件。请检查当前代码是否已经实现 tension cracking、stress scaling back 或其他 return mapping。请指出具体文件和函数，并说明与 Bui 2008 的公式是否一致。
```

### 15.3 Artificial stress plan

```text
请不要修改任何文件。请判断当前代码是否已有 artificial stress 方法。如果没有，请提出 CPU-only 最小实现方案，并说明它与 shifting、stress diffusion、artificial viscosity 的关系。
```

---

## 16. Recommended implementation priority

For this project, use Bui et al. (2008) in this order:

```text
1. Understand current DP stress update.
2. Confirm return mapping / stress scaling status.
3. Confirm tensile instability treatment.
4. Confirm artificial viscosity and shifting options.
5. Only then consider adding missing CPU-only feature.
6. Validate CPU Debug.
7. Port to GPU only after CPU validation.
```

Avoid:

```text
- Direct GPU kernel modification before CPU validation.
- Adding artificial stress without checking current stress diffusion/shifting.
- Changing sign convention.
- Replacing mDBC with Bui boundary interpolation.
- Adding duplicate return mapping.
```

---

## 17. Short summary for Codex

Bui et al. (2008) provides the elastoplastic SPH foundation for geomaterial flow: mass and momentum balance, Drucker–Prager associated/non-associated plasticity, Jaumann stress rate, return mapping by tension cracking and stress scaling, artificial viscosity, artificial stress for tensile instability, and boundary stress treatment. In GeoDualSPHysics, use this paper primarily to understand or verify the constitutive update and stability treatments. Do CPU-first analysis before changing any code.
