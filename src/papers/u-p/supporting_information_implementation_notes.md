# Implementation notes for Codex: Supporting Information for Coupled u–pw SPH formulation

> Source: Supporting Information for **“A Coupled u–pw SPH Formulation for Hydromechanical Modeling of Retrogressive Landslides and Comparison With a Penalty-Based Approach”**.
>
> Purpose: summarize the Supporting Information into implementation-oriented notes for the GeoDualSPHysics/DualSPHysics v5.2 CPU-first u–pw PR prototype.
>
> Scope: focus on stabilization, self-weight 1D consolidation, and implications for current GeoDualSPHysics implementation. Do **not** automatically patch source based on this note without a separate design review.

---

## 1. Key takeaways for the current GeoDualSPHysics prototype

The Supporting Information suggests a better next route than continuing to force the external-load Terzaghi case:

```text
Self-weight consolidation first
→ verify undrained pore-pressure build-up under gravity
→ then test dissipation with body gravity off or hydrostatic convergence with gravity on
→ only after this, return to externally loaded Terzaghi.
```

The main reasons are:

1. The authors explicitly use both **Monaghan artificial viscosity** and **global kinematic damping**.
2. They use **Shepard regularization of pore pressure** every 20–40 time steps.
3. Their self-weight verification naturally generates excess pore pressure from distributed gravitational loading, avoiding the very stiff top-layer loading problem we observed.

---

## 2. Numerical stabilization in the Supporting Information

### 2.1 Modified momentum equation

The stabilized momentum equation is:

```math
<dv_s/dt>_i =
sum_j m_j (sigma'_i/rho_i^2 + sigma'_j/rho_j^2 + Pi_ij) · grad W_ij
+ sum_j m_j ((p^w_i+p^w_j)/(rho_i rho_j)) 1 · grad W_ij
- c_d v_i + g
```

Implementation meaning for GeoDualSPHysics:

- `Sigmac` should remain effective stress `sigma'`.
- Pore-pressure feedback is an extra acceleration-like contribution.
- Artificial viscosity and damping are part of the stable coupled formulation.

### 2.2 Monaghan artificial viscosity

The paper uses Monaghan artificial viscosity:

```math
Pi_ij =
(-alpha cbar_ij mu_ij + beta mu_ij^2) / rhobar_ij, if v_ij · x_ij < 0
0, otherwise
```

where

```math
mu_ij = h (v_ij · x_ij) / (|x_ij|^2 + eta h^2)
```

Reported coefficient ranges:

```text
0.1 <= alpha <= 0.8
0 <= beta <= 0.4
```

The self-weight figures use:

```text
alpha = 0.4
```

### 2.3 Global kinematic damping

The damping force is:

```math
-c_d v_i
```

with:

```math
c_d = xi * sqrt(E / (rho h^2))
```

where `xi` is dimensionless.

Reported range:

```text
0 <= xi <= 0.05
```

The self-weight figures use:

```text
xi = 4e-5
```

Mapping to the current GeoDualSPHysics parameter:

```text
HydromechDampingCoef = c_d = xi * sqrt(E / (rho h^2))
```

For typical 1D consolidation values:

```text
E   = 2e6 Pa
rho ≈ 2100 kg/m3
h   ≈ 0.018 m
```

the scale is approximately:

```text
sqrt(E/(rho*h^2)) ≈ 1714 1/s

xi = 4e-5  -> c_d ≈ 0.0686 1/s
xi = 0.01  -> c_d ≈ 17.1 1/s
xi = 0.05  -> c_d ≈ 85.7 1/s
```

This means the current exploratory `HydromechDampingCoef = 500 1/s` is far above the reported self-weight damping if interpreted via this formula.

### 2.4 Shepard regularization of pore pressure

The Supporting Information uses Shepard regularization:

```math
p^{w,reg}_i =
[sum_j (m_j/rho_j) p^w_j W_ij] /
[sum_j (m_j/rho_j) W_ij]
```

Applied frequency:

```text
every 20 to 40 time steps
```

Implication:

- Current coupled instability may require this smoothing before long coupled tests.
- This should be implemented as an optional CPU-only feature first.
- It should be off by default.

Suggested future parameters:

```xml
<parameter key="PorePressureShepard" value="0" />
<parameter key="PorePressureShepardInterval" value="20" />
```

---

## 3. Self-weight consolidation verification

### 3.1 Initial undrained response

The initial undrained pore pressure response under self-weight is:

```math
p^w_0(z) =
[(K_w/n) rho g (H-z)] /
[K + 4G/3 + K_w/n]
```

where:

```math
K = E / [3(1-2nu)]
G = E / [2(1+nu)]
```

`z` is measured from the bottom upward.

For the standard 1D consolidation parameters:

```text
H  = 1.0 m
E  = 2e6 Pa
nu = 0.3
Kw = 2e8 Pa
n  = 0.3
k  = 1e-3 m/s
dt = 1e-6 s
```

`Kw/n` is much larger than the elastic stiffness terms, so the undrained self-weight pore pressure is close to:

```text
p0(z) ≈ rho g (H-z)
```

but slightly reduced by the denominator above.

### 3.2 Scenario 1: gravity switched off after undrained response

After self-weight-induced pore pressure is generated, gravity is switched off and dissipation proceeds. The solution is:

```math
p^w(z,T_v) =
sum_{n=0}^N A_n cos(lambda_n z) exp(-lambda_n^2 T_v H^2)
```

where:

```math
lambda_n = (2n+1) pi / (2H)
A_n = (2/H) int_0^H p^w_0(z) cos(lambda_n z) dz
T_v = c_v t / H^2
```

Implementation route:

```text
Stage A: body gravity on, top undrained, generate self-weight pore pressure
Stage B: restart with body gravity off, hydraulic gravity still on, top drained active
```

This is compatible with the existing `HydraulicGravity` / body `Gravity` decoupling.

### 3.3 Scenario 2: gravity maintained

If gravity remains active after drainage begins, pore pressure evolves from the initial undrained response toward the hydrostatic gradient.

Implementation route:

```text
Stage A: body gravity on, top undrained, generate self-weight pore pressure
Stage B: keep body gravity on, activate top drained, bottom no-flux active
```

Target hydrostatic profile:

```math
p^w_hydro(z) = rho_w g (H-z)
```

if water level is at the top surface.

---

## 4. Parameters reported for self-weight verification

The Supporting Information gives:

```text
k       = 1e-3 m/s
Delta t = 1e-6 s
alpha   = 0.4
xi      = 4e-5
```

It uses the same material parameters as the 1D Terzaghi consolidation problem:

```text
H  = 1.0 m
width = 0.1 m
Delta = 0.01 m
E  = 2e6 Pa
nu = 0.3
Kw = 2e8 Pa
n  = 0.3
k  = 1e-3 m/s
```

---

## 5. Recommended GeoDualSPHysics route

### Phase SW-0: Keep pressure-only benchmark as baseline

The existing pressure-only 1D consolidation case should remain as a baseline. It has verified:

- PR pore pressure update.
- `dt_pore`.
- top drained layer.
- bottom no-flux layer.
- `ExcessPorePress` output.
- pressure diffusion trend.

### Phase SW-1: Add pore-pressure Shepard regularization

Implement optional CPU-only:

```xml
<parameter key="PorePressureShepard" value="0" />
<parameter key="PorePressureShepardInterval" value="20" />
```

First version:

- material-material only.
- apply after pore-pressure update.
- do not smooth boundary particles.
- do not alter `PorePressureRate`.
- default off.
- log when applied.

### Phase SW-2: Revisit damping scaling

Current `HydromechDampingCoef` should be compared to:

```text
c_d = xi * sqrt(E/(rho*h^2))
```

Add log output:

```text
HydromechDampingXiEquivalent =
HydromechDampingCoef / sqrt(E/(rho*h^2))
```

This helps compare current settings with the Supporting Information.

### Phase SW-3: Self-weight undrained loading stage

Create:

```text
examples/u-pw/01_1D_Consolidation/Case1DConsolidation_PR_SelfWeight_Def.xml
```

Suggested settings:

```xml
<parameter key="HydromechCoupling" value="1" />
<parameter key="PorePressureModel" value="1" />
<parameter key="PorePressureFeedback" value="1" />
<parameter key="PorePressureFeedbackMode" value="1" />
<parameter key="PorePressureFeedbackOperator" value="1" />
<parameter key="PorePressureInit" value="1" />
<parameter key="PorePressureTopDrained" value="1" />
<parameter key="PorePressureTopDrainedStartTime" value="T_undrained" />
<parameter key="PorePressureBottomNoFlux" value="1" />
<parameter key="TopLoadEnabled" value="0" />
```

Gravity settings:

```text
body Gravity = (0,0,-9.81)
HydraulicGravity = (0,0,-9.81)
```

Start from hydrostatic baseline:

```text
PorePressureInit=1 -> ExcessPorePress=0
```

During undrained loading:

```text
top drained inactive
bottom no-flux active
gravity active
feedback active
```

The model should generate excess pore pressure through volumetric compression.

### Phase SW-4: Compare initial undrained response

At transition time `T_undrained`, compare numerical excess pressure with:

```math
p^w_0(z) =
[(K_w/n) rho g (H-z)] /
[K + 4G/3 + K_w/n]
```

### Phase SW-5: Dissipation scenario 1, gravity off

At `T_undrained`:

- switch mechanical body gravity off;
- keep hydraulic gravity nonzero;
- activate top drained;
- keep bottom no-flux.

Recommended workflow:

```text
run undrained self-weight stage
save restart
restart with body Gravity=0, HydraulicGravity=(0,0,-9.81), top drained active
```

### Phase SW-6: Dissipation scenario 2, gravity on

At `T_undrained`:

- keep mechanical gravity on;
- activate top drained;
- bottom no-flux active.

Pore pressure should trend toward hydrostatic.

---

## 6. Implications for current difficulties

The external-load Terzaghi case has been difficult because:

- top-layer acceleration produces rapid dynamic deformation;
- PR equation contains `Kw/n * DivVel`, which strongly amplifies small volumetric strain rates;
- pore-pressure feedback then further accelerates skeleton motion;
- no Shepard pressure regularization is active;
- explicit coupling is stiff.

Self-weight consolidation may be easier because it generates pore pressure from distributed body-force-induced deformation instead of a concentrated top-layer acceleration.

---

## 7. Recommended immediate tasks

1. Commit current source state.
2. Add this markdown note to the repository as:

```text
src/papers/u-p/supporting_information_implementation_notes.md
```

3. Implement optional CPU-only `PorePressureShepard` regularization.
4. Create self-weight 1D consolidation case.
5. Compare initial undrained response with the analytical expression.
6. Only then return to external-load Terzaghi.

