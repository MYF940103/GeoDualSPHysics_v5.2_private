# Implementation notes for Codex: Coupled u–pw SPH formulation for hydromechanical modeling

> Purpose: This note summarizes the paper **“A Coupled u–pw SPH Formulation for Hydromechanical Modeling of Retrogressive Landslides and Comparison With a Penalty-Based Approach”** into an implementation-oriented format for use with Codex in the GeoDualSPHysics/DualSPHysics v5.2 codebase.
>
> Scope: The notes are intended for **code navigation, design discussion, and CPU-first prototype planning**. They should **not** be used to automatically patch the code without first validating the variable mapping and numerical assumptions.

---

## 0. Paper and implementation context

### Paper target

The paper proposes a strongly coupled **displacement–pore-pressure** formulation, written as **u–pw**, for saturated porous geomaterials in SPH. It presents two variants:

1. **PPE formulation**: pressure Poisson equation / projection-method approach.
2. **PR formulation**: explicit pore-pressure-rate equation approach.

The authors implement the model in their own parallel SPH code GEOSPH/PySPH, not DualSPHysics. Therefore, direct transplantation into GeoDualSPHysics requires careful mapping of particle fields, stress update, time stepping, boundary treatment, and output.

### Main implementation objective for GeoDualSPHysics

A reasonable implementation strategy is:

1. **CPU path first**: add a minimal coupled u–pw prototype in the CPU solver.
2. **Start with PR formulation** rather than PPE, because the PR equation is explicit and more compatible with the current explicit SPH workflow.
3. Add data fields for pore pressure, porosity/permeability, effective stress, and possibly pressure-rate terms.
4. Validate against a very simple 1D consolidation or undrained compression benchmark before touching GPU kernels.
5. Port to GPU only after CPU behavior is understood and verified.

---

## 1. Governing equations

### 1.1 General mixture equations

The paper starts from a saturated two-phase porous medium with solid skeleton and pore water.

The general mass balance is

```math
\frac{1}{Q}\frac{d p_w}{dt}
- \nabla \cdot \mathbf{v}
- \nabla \cdot \mathbf{v}_s
- \frac{\nabla \rho_w}{\rho_w}\cdot \mathbf{v}
= 0 .
```

The general mixture momentum balance is

```math
\rho \frac{d\mathbf{v}_s}{dt}
+ \rho_w
\left(
\frac{d_w \mathbf{v}_w}{dt}
-
\frac{d\mathbf{v}_s}{dt}
\right)
=
\nabla \cdot \boldsymbol{\sigma}' + \nabla p_w + \rho \mathbf{g}.
```

where:

- `p_w`: pore water pressure.
- `sigma'`: effective Cauchy stress tensor of soil skeleton.
- `v_s`: solid skeleton velocity.
- `v_w`: pore water velocity.
- `v`: Darcy velocity, i.e. relative fluid–solid velocity per unit mixture area.
- `rho`: bulk mixture density.
- `rho_w`: intrinsic water density.
- `n`: porosity.
- `Q`: Biot compressibility-related modulus.
- `K_s`: solid bulk modulus.
- `K_w`: water bulk modulus.
- `k`: hydraulic conductivity, assumed isotropic/homogeneous in the paper.
- `g`: gravitational acceleration magnitude or vector depending on context.
- `z`: elevation head coordinate.

The mixture modulus relation is

```math
\frac{1}{Q} =
\frac{1-n}{K_s}
+
\frac{n}{K_w}.
```

---

## 2. PPE formulation

### 2.1 Assumptions

The PPE formulation assumes:

1. Solid and pore fluid fractions are intrinsically incompressible:

```math
K_s \to \infty,\qquad K_w \to \infty,
```

so that

```math
\frac{1}{Q}\to 0,\qquad \nabla \rho_w = 0.
```

2. Relative fluid–solid acceleration is neglected:

```math
\frac{d_w \mathbf{v}_w}{dt}
-
\frac{d\mathbf{v}_s}{dt}
= 0.
```

### 2.2 Governing equations

The mass balance becomes

```math
\nabla \cdot \mathbf{v}_s
+
\frac{k}{\rho_w g}\nabla^2 p_w
+
k\nabla^2 z
= 0.
```

The momentum balance becomes

```math
\frac{d\mathbf{v}_s}{dt}
=
\frac{1}{\rho}\nabla\cdot\boldsymbol{\sigma}'
+
\frac{1}{\rho}\nabla p_w
+
\mathbf{g}.
```

### 2.3 Predictor–corrector projection step

The predicted solid velocity is computed without pore pressure:

```math
\mathbf{v}_s^*
=
\mathbf{v}_s^n
+
\Delta t
\left(
\frac{1}{\rho^n}\nabla\cdot\boldsymbol{\sigma}'^n
+
\mathbf{g}
\right).
```

The corrected solid velocity is

```math
\mathbf{v}_s^{n+1}
=
\mathbf{v}_s^*
+
\Delta t
\frac{1}{\rho^*}
\nabla p_w^{n+1}.
```

The projected density is

```math
\rho^*
=
\rho^n
+
\Delta t\,\rho^n \nabla\cdot\mathbf{v}_s^*.
```

The pressure Poisson equation is reduced to

```math
\nabla^2 p_w^{n+1}
=
-a^*
\left(
\nabla\cdot\mathbf{v}_s^*
+
k\nabla^2 z^*
\right),
```

where

```math
a^*
=
\frac{b\rho^*}{\rho^*+b\Delta t},
\qquad
b=\frac{\rho_w g}{k}.
```

### 2.4 Implementation remarks for PPE

The PPE update involves a pressure-correction feedback coefficient `a*`. The paper notes that, for small `dt` and low permeability `k`, `a*` can become large and destabilize the explicit update.

For GeoDualSPHysics, the PPE variant should **not** be the first implementation target unless:

- a stable pressure-correction loop is carefully designed;
- permeability ranges are not too low;
- the effect of `a*` is tested;
- time-step constraints include both CFL upper bound and PPE-related lower bound.

---

## 3. PR formulation

### 3.1 Assumptions

The PR formulation relaxes fluid incompressibility but keeps the solid grains intrinsically incompressible:

```math
K_s \to \infty,
```

and assumes that the spatial gradient of water density is negligible:

```math
\nabla \rho_w \approx 0.
```

Then

```math
\frac{1}{Q}
\approx
\frac{n}{K_w}.
```

### 3.2 Governing pore-pressure-rate equation

The pore-pressure rate equation is

```math
\frac{d p_w}{dt}
=
\frac{K_w}{n}
\left(
\frac{k}{\rho_w g}\nabla^2 p_w
+
k\nabla^2 z
+
\nabla\cdot\mathbf{v}_s
\right).
```

The momentum balance is the same as in the PPE formulation:

```math
\frac{d\mathbf{v}_s}{dt}
=
\frac{1}{\rho}\nabla\cdot\boldsymbol{\sigma}'
+
\frac{1}{\rho}\nabla p_w
+
\mathbf{g}.
```

The explicit time update is

```math
p_{w,i}^{n+1}
=
p_{w,i}^{n}
+
\left\langle
\frac{d p_w}{dt}
\right\rangle_i
\Delta t.
```

### 3.3 Why PR should be implemented first

For GeoDualSPHysics, the PR formulation is the safer first target because:

- it fits the existing explicit time-integration structure;
- it avoids solving a global PPE;
- it can be implemented as a per-particle rate update;
- it allows CPU-only testing before GPU porting;
- the paper reports fewer severe stability restrictions than the PPE version.

---

## 4. SPH operators required by the paper

### 4.1 Standard SPH interpolation

```math
\langle f(\mathbf{x})\rangle_i
=
\sum_j
\frac{m_j}{\rho_j}
f_j W_{ij}.
```

### 4.2 Basic gradient

```math
\langle \nabla f \rangle_i
=
\sum_j
\frac{m_j}{\rho_j}
f_j \nabla W_{ij}.
```

### 4.3 Corrected gradient

The paper uses a first-order corrected kernel gradient:

```math
\tilde{\nabla} W_{ij}
=
\mathbf{L}_i\cdot\nabla W_{ij},
```

with

```math
\mathbf{L}_i
=
\left[
\sum_j
\frac{m_j}{\rho_j}
(\mathbf{x}_j-\mathbf{x}_i)\otimes\nabla W_{ij}
\right]^{-1}.
```

### 4.4 Divergence operators

The effective-stress divergence is discretized using a symmetric stress operator:

```math
\left\langle
\nabla\cdot\mathbf{f}
\right\rangle_i
=
\rho_i
\sum_j
m_j
\left(
\frac{\mathbf{f}_i}{\rho_i^2}
+
\frac{\mathbf{f}_j}{\rho_j^2}
\right)
\nabla W_{ij}.
```

The pore-pressure gradient in momentum is discretized as

```math
\left\langle
\nabla p_w
\right\rangle_i
\sim
\sum_j
m_j
\left(
\frac{p_{w,i}+p_{w,j}}{\rho_i\rho_j}
\right)
\mathbf{1}\cdot\nabla W_{ij}.
```

The velocity divergence in the mass equation is discretized as

```math
\left\langle
\nabla\cdot\mathbf{v}_s
\right\rangle_i
=
\sum_j
\frac{m_j}{\rho_j}
(\mathbf{v}_{s,j}-\mathbf{v}_{s,i})
\cdot
\tilde{\nabla}W_{ij}.
```

### 4.5 Laplacian operator

The pore-pressure and elevation-head Laplacians use the Morris-type operator:

```math
\left\langle
\nabla^2 f
\right\rangle_i
=
2\sum_j
\frac{m_j}{\rho_j}
(f_i-f_j)
\frac{\mathbf{x}_{ij}}{|\mathbf{x}_{ij}|^2}
\cdot
\tilde{\nabla}W_{ij}.
```

where

```math
\mathbf{x}_{ij}=\mathbf{x}_i-\mathbf{x}_j.
```

---

## 5. PR formulation in SPH summation form

For implementation planning, the key per-particle update is:

```math
\left\langle
\frac{dp_w}{dt}
\right\rangle_i
=
\frac{K_w}{n}
\left[
D_i
+
\frac{2k_i}{\rho_w g}L_{p,i}
+
2k_iL_{z,i}
\right],
```

where:

### Velocity-divergence term

```math
D_i
=
\sum_j
\frac{m_j}{\rho_j}
(\mathbf{v}_{s,j}-\mathbf{v}_{s,i})
\cdot
\tilde{\nabla}W_{ij}.
```

### Pore-pressure Laplacian term

```math
L_{p,i}
=
\sum_j
\frac{m_j}{\rho_j}
(p_{w,i}-p_{w,j})
\frac{\mathbf{x}_{ij}}{|\mathbf{x}_{ij}|^2}
\cdot
\tilde{\nabla}W_{ij}.
```

### Elevation-head Laplacian term

```math
L_{z,i}
=
\sum_j
\frac{m_j}{\rho_j}
(z_i-z_j)
\frac{\mathbf{x}_{ij}}{|\mathbf{x}_{ij}|^2}
\cdot
\tilde{\nabla}W_{ij}.
```

Then:

```math
p_{w,i}^{n+1}
=
p_{w,i}^{n}
+
\frac{K_w}{n}
\left[
D_i
+
\frac{2k_i}{\rho_w g}L_{p,i}
+
2k_iL_{z,i}
\right]
\Delta t.
```

---

## 6. Momentum equation with pore pressure

The effective-stress and pore-pressure contributions should enter the solid acceleration as

```math
\left\langle
\frac{d\mathbf{v}_s}{dt}
\right\rangle_i
=
\sum_j
m_j
\left(
\frac{\boldsymbol{\sigma}'_i}{\rho_i^2}
+
\frac{\boldsymbol{\sigma}'_j}{\rho_j^2}
\right)
\cdot\nabla W_{ij}
+
\sum_j
m_j
\left(
\frac{p_{w,i}+p_{w,j}}{\rho_i\rho_j}
\right)
\mathbf{1}\cdot\nabla W_{ij}
+
\mathbf{g}.
```

### Important implementation issue

DualSPHysics currently treats pressure, density, and stress-like terms differently from a geomechanics u–pw effective-stress formulation. Before coding, Codex must identify:

- whether current `Pressc`, `Rhop`, `Ace`, `ViscDt`, or stress arrays already include total pressure-like effects;
- whether a pore-pressure term should be added as a separate acceleration contribution;
- whether a total stress or effective stress convention is already used in the GeoDualSPHysics branch.

Do **not** simply add `∇p_w` to an existing pressure force without checking for double counting.

---

## 7. Boundary conditions

The paper partitions boundaries into:

- velocity boundaries;
- traction boundaries;
- pore-pressure Dirichlet boundaries;
- pore-pressure Neumann/flux boundaries.

The boundary conditions are:

```math
\boldsymbol{\sigma}\cdot\mathbf{n}=\mathbf{h},
```

```math
\mathbf{v}=\hat{\mathbf{v}},
```

```math
p_w=\bar{p}_w,
```

```math
-\frac{k}{\rho_w g}\nabla p_w\cdot\mathbf{n}
=
\bar{q}_w.
```

For undrained boundaries,

```math
\nabla p_w\cdot\mathbf{n}=0.
```

### Paper treatment

- Solid velocity boundaries use dummy/boundary particles.
- Boundary stresses are extrapolated from neighboring domain particles.
- Free surfaces may impose zero pore pressure.
- Pore-pressure Neumann boundaries require extrapolation/treatment so that the normal pore-pressure gradient is controlled.
- The paper uses a moving least-squares approach for extrapolating pore pressure to boundary particles.

### GeoDualSPHysics mapping

Potentially relevant existing files/functions:

- `source/JSph.cpp`
  - boundary configuration loading;
  - mDBC setup;
  - normal data loading.
- `source/JSphCpuSingle.cpp`
  - CPU mDBC correction call.
- `source/JSphCpu.cpp`
  - CPU mDBC correction implementation.
- `source/JSphGpuSingle.cpp`
  - GPU mDBC correction call.
- `source/JSphGpu_ker.cu`
  - GPU mDBC kernels.

Implementation caution:

- mDBC currently reconstructs boundary states for hydrodynamic variables.
- A u–pw model would also need boundary values or ghost/extrapolated values of `p_w`.
- Drained/free-surface boundaries and undrained/no-flux boundaries must be distinguished explicitly.

---

## 8. Constitutive update

The paper assumes an effective-stress elastoplastic model. The effective stress evolves by a hypo-elastoplastic law:

```math
\overset{\triangledown}{\boldsymbol{\sigma}}'
=
\mathbf{c}^{ep}:\mathbf{d}.
```

The Jaumann rate is

```math
\overset{\triangledown}{\boldsymbol{\sigma}}'
=
\dot{\boldsymbol{\sigma}}'
-
\boldsymbol{\omega}\cdot\boldsymbol{\sigma}'
+
\boldsymbol{\sigma}'\cdot\boldsymbol{\omega}.
```

For purely elastic isotropic behavior,

```math
\mathbf{c}^{e}
=
K\mathbf{1}\otimes\mathbf{1}
+
2\mu
\left(
\mathbf{I}
-
\frac{1}{3}\mathbf{1}\otimes\mathbf{1}
\right).
```

The paper uses Drucker–Prager and modified Cam-Clay models in benchmarks/applications. For GeoDualSPHysics, the implementation should initially avoid coupling a new complex plasticity model with pore pressure unless the existing rheology/stress update is already well identified.

### Recommended first-stage simplification

For a first coding prototype:

1. Keep current solid/rheology model unchanged.
2. Add pore pressure as an additional scalar field.
3. Add PR update based on current velocity divergence.
4. Add pore-pressure-gradient acceleration only after checking stress/pressure conventions.
5. Validate in a simple poroelastic-like case.

---

## 9. Time stepping and stability

The paper states the overall time step should satisfy

```math
\Delta t \le \min(\Delta t_s,\Delta t_w).
```

The solid CFL time step is

```math
\Delta t_s
\le
a\frac{h}{c},
```

where `c` is a numerical sound speed of the solid phase.

The pore-fluid pressure stability condition is

```math
\Delta t_w
\le
\frac{a C_w h^2}{k},
```

where

```math
C_w=\frac{\rho_w g n}{K_w}.
```

The paper indicates that a common choice is

```math
a=0.1.
```

For the PPE formulation, stability is additionally affected by

```math
a^*(k,\Delta t)
=
\frac{b\rho^*}{\rho^*+b\Delta t},
\qquad
b=\frac{\rho_w g}{k}.
```

The PPE formulation may require the time step to be neither too large nor too small.

### Implementation guidance for GeoDualSPHysics

Add any new pore-pressure time-step restriction conservatively:

```text
dt_pore = safety * Cw * h^2 / k
dt = min(existing dt, dt_pore)
```

Check units carefully. In this paper `k` is hydraulic conductivity with units of velocity, not necessarily intrinsic permeability.

Do not reuse existing DualSPHysics viscosity or density-diffusion stability coefficients unless the dimensional meaning is verified.

---

## 10. Numerical stabilization

The paper reports that stabilization is necessary in the coupled u–pw formulations. In 1D consolidation, it compares artificial viscosity and kinematic damping. Its observations include:

- some combination of artificial viscosity and kinematic damping is needed to prevent divergence;
- artificial viscosity alone can stabilize but may introduce error/dissipation;
- kinematic damping improves agreement, but excessive damping overdamps the response;
- the reported useful kinematic damping magnitude is roughly 10–50 times the time step in the tested consolidation setup;
- the PR formulation is generally preferred for the landslide simulations due to fewer stability difficulties than PPE.

### GeoDualSPHysics notes

Potential existing mechanisms that may interact with this model:

- artificial viscosity (`-viscoart`);
- laminar/SPS viscosity (`-viscolamsps`);
- density diffusion (`-ddt`);
- shifting (`-shifting`);
- damping (`JDsDamping.cpp`);
- time-step calculation (`JDsFixedDt.cpp`, `DtVariable()` calls).

Do not enable multiple stabilizers blindly. Pore-pressure diffusion, density diffusion, artificial viscosity, and shifting can interact in nonphysical ways.

---

## 11. Verification cases to reproduce before landslides

### 11.1 1D Terzaghi consolidation

Paper setup:

- column height: `H = 1.0 m`;
- width: `0.1 m`;
- initial particle spacing: `Delta = 0.01 m`;
- Young's modulus: `E = 2e6 Pa`;
- Poisson's ratio: `nu = 0.3`;
- water bulk modulus: `K_w = 2e8 Pa`;
- porosity: `n = 0.3`;
- hydraulic conductivity: `k = 1e-3 m/s`;
- time step: `dt = 1e-6 s`;
- bottom and lateral boundaries undrained;
- top free surface with zero pore pressure;
- load: `q0 = -10 kPa` applied at top.

Analytical solution:

```math
p_w(z)
=
\sum_{j=1}^{\infty}
\frac{2p_w^0}{M}
\sin\left(\frac{Mz}{H}\right)
\exp(-M^2 T_v),
```

where

```math
M=0.5(2j-1)\pi,
```

```math
T_v=\frac{c_vt}{H^2},
```

```math
c_v
=
\frac{k(1-\nu)E}
{(1+\nu)(1-2\nu)\rho_w g}.
```

### 11.2 Suggested first GeoDualSPHysics verification path

1. Implement PR on CPU only.
2. Create a minimal 1D/2D column case.
3. Use fixed bottom and undrained lateral boundaries.
4. Impose free surface pore pressure approximately as `p_w = 0`.
5. Compare pore pressure profiles to Terzaghi solution.
6. Only after acceptable agreement, add more complex boundaries or plasticity.

---

## 12. Suggested code mapping in GeoDualSPHysics

### 12.1 Current Codex-detected call chain

Codex previously identified the current solver structure as:

```text
main.cpp
  -> JSphCpuSingle::Run()
    -> ComputeStep()
      -> ComputeStep_Ver() or ComputeStep_Sym()
        -> Interaction_Forces()
        -> DtVariable()
        -> RunShifting()
        -> ComputeVerlet() or ComputeSymplectic...
```

GPU path is analogous through:

```text
main.cpp
  -> JSphGpuSingle::Run()
    -> ComputeStep()
      -> ComputeStep_Ver() or ComputeStep_Sym()
        -> Interaction_Forces()
        -> cusph::Interaction_Forces()
        -> CUDA kernels in JSphGpu_ker.cu
```

### 12.2 CPU files to inspect first

- `source/main.cpp`
  - command-line selection of CPU/GPU execution.
- `source/JSphCpuSingle.cpp`
  - CPU time-step loop.
  - `ComputeStep_Ver()`.
  - `ComputeStep_Sym()`.
  - `Interaction_Forces()`.
- `source/JSphCpu.cpp`
  - CPU particle interaction loops.
  - `InteractionForcesFluid()`.
  - `InteractionForcesBound()`.
  - possible place to accumulate `div(v_s)`, `laplacian(p_w)`, and pore-pressure-gradient acceleration.
- `source/JSph.cpp`
  - configuration loading, boundary and shifting setup.
- `source/JSphShifting.cpp`
  - shifting corrections that may disturb pore-pressure gradients if not handled carefully.
- `source/JArraysCpu.cpp` and related array classes
  - candidate locations for adding CPU-side arrays.
- `source/JPartDataBi4.cpp`, `source/JPartFloatBi4.cpp`, `source/JOutputCsv.cpp`
  - output/write support if pore pressure needs to be saved.

### 12.3 GPU files to inspect later

- `source/JSphGpuSingle.cpp`
- `source/JSphGpu.cpp`
- `source/JSphGpu_ker.cu`
- `source/JSphGpuSimple_ker.cu`
- `source/JSphShifting_ker.cu`
- `source/JArraysGpu.cpp`

Do not implement GPU first.

---

## 13. Candidate new particle fields

A u–pw implementation likely needs at least:

```cpp
double or float *PorePress;      // p_w
double or float *PorePressRate;  // dp_w/dt, optional temporary
double or float *Porosity;       // n, can start constant
double or float *HydCond;        // k, can start constant
double or float *BulkWater;      // K_w, can start constant
```

Possibly also:

```cpp
double or float *DivVel;         // divergence of solid velocity
double or float *LapPw;          // Laplacian of p_w
double or float *LapZ;           // Laplacian of elevation head
double or float *PwGrad;         // gradient of p_w, if separated
```

For minimal CPU prototype, many of these can be local temporaries inside interaction loops rather than persistent arrays.

---

## 14. Suggested CPU-first implementation phases

### Phase 0: read-only mapping

Ask Codex:

```text
Do not modify files. Find current CPU variables corresponding to position, velocity, density, pressure, acceleration, mass, neighbor list, kernel gradient, and time step. Produce a mapping table.
```

### Phase 1: passive pore-pressure field

- Add `p_w` as a particle scalar.
- Initialize it to zero or hydrostatic distribution.
- Output it to CSV/VTK if possible.
- Do not affect momentum yet.

### Phase 2: PR update without feedback

- Compute `dp_w/dt` from velocity divergence and Laplacian terms.
- Update `p_w`.
- Do not add `∇p_w` to acceleration yet.
- Validate stability and output.

### Phase 3: pore-pressure feedback to momentum

- Add pore-pressure-gradient force to acceleration.
- Confirm no double counting with existing pressure/stress terms.
- Compare against Terzaghi consolidation.

### Phase 4: boundary treatment

- Add free-surface `p_w = 0`.
- Add undrained/no-flux boundary support.
- Consider mDBC-compatible pore-pressure ghost states.

### Phase 5: GPU port

- Port fields and kernels only after CPU is stable.
- Confirm CPU/GPU numerical consistency on a small case.

---

## 15. Specific Codex prompts for safe implementation

### 15.1 First mapping prompt

```text
Please do not modify any files. Read this implementation note and inspect source/JSphCpuSingle.cpp and source/JSphCpu.cpp. Map the variables in the paper (p_w, v_s, rho, sigma', k, n, K_w, h, dt, W_ij, gradW_ij) to existing GeoDualSPHysics variables or identify missing fields. Provide a table and do not edit code.
```

### 15.2 Insertion point prompt

```text
Please do not modify any files. Find the safest CPU-only insertion point for computing the PR pore-pressure-rate update. Explain whether it should be placed before Interaction_Forces(), inside InteractionForcesFluid(), after PreInteraction_Forces(), or after ComputeStep_Sym/Ver, and justify the choice.
```

### 15.3 Minimal CPU prototype prompt

```text
You may modify files, but only CPU path. Implement a passive pore-pressure scalar field initialized to zero and included in output if possible. Do not change momentum or physical equations. Before editing, list files to modify. After editing, run the default CPU Debug build task.
```

### 15.4 PR update prompt

```text
You may modify files, but only CPU path. Add a first-pass PR update for p_w using a constant porosity n, hydraulic conductivity k, and water bulk modulus K_w. Do not add pore-pressure feedback to acceleration yet. Keep the patch minimal and build CPU Debug.
```

---

## 16. Numerical risks and checks

### 16.1 Dimensional consistency

Check whether `k` in the paper is hydraulic conductivity `[m/s]`, whereas some geomechanics codes use intrinsic permeability `[m^2]`. Do not mix them.

### 16.2 Density convention

DualSPHysics variables often use fluid density and pressure conventions. The paper uses mixture density and effective stress. Identify whether `rho` in the code is mixture density, phase density, or weakly-compressible SPH density.

### 16.3 Pressure double counting

If current GeoDualSPHysics already has pressure-like force terms, adding `∇p_w` may double count pressure unless total/effective stress conventions are separated.

### 16.4 Boundary particles

The PR equation needs pore-pressure values on neighboring particles. Boundary particles must have meaningful `p_w` values or be excluded/treated carefully.

### 16.5 Shifting

Particle shifting changes particle positions and may affect pore-pressure gradients and Laplacian terms. If `p_w` is not advected or corrected consistently, spurious pressure noise can appear.

### 16.6 Time step

Add pore-pressure time-step restriction before strong coupling. Start with conservative `dt`.

### 16.7 Artificial viscosity and damping

Avoid tuning stabilization and physics simultaneously. First run with a simple benchmark and document every stabilizer used.

---

## 17. Recommended initial implementation target

Recommended first target for GeoDualSPHysics:

```text
PR formulation, CPU-only, constant n/k/K_w, passive p_w field, then explicit dp_w/dt update, then optional pressure-gradient feedback.
```

Avoid initially:

```text
PPE formulation, GPU kernels, complex mDBC pore-pressure extrapolation, Drucker–Prager strain softening, modified Cam-Clay, production landslide cases.
```

---

## 18. Minimal acceptance criteria before GPU implementation

Before porting to GPU:

1. CPU Debug builds without warnings beyond existing known project warnings.
2. A tiny consolidation benchmark runs without NaN/Inf.
3. `p_w` remains bounded.
4. `dt` obeys both existing SPH restrictions and the pore-pressure restriction.
5. Results qualitatively match Terzaghi consolidation trends.
6. Code paths are documented.
7. CPU/GPU parity plan is written.

---

## 19. Short summary for Codex

This paper should be treated as a **strongly coupled hydromechanical u–pw SPH formulation**. The **PR equation** is the most suitable first implementation target in GeoDualSPHysics because it is explicit and local. Implement it CPU-first. Add pore pressure as a scalar particle field, compute `dp_w/dt` from velocity divergence, pore-pressure Laplacian, and elevation-head Laplacian, then later feed `∇p_w` into the solid acceleration after verifying stress/pressure conventions. Boundary conditions, time-step restrictions, and stabilization are critical; do not begin with GPU or full landslide simulation.
