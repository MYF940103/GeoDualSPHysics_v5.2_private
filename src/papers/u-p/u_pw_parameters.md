# u-pw PR CPU Prototype Parameters

This document summarizes the hydromechanical parameters currently introduced for the CPU-side u-pw PR prototype. The implementation is PR-only at this stage; PPE is not implemented in this branch.

## 1. Core PR Parameters

| Parameter | Type / values | Default | Purpose | Keep? |
|---|---:|---:|---|---|
| `HydromechCoupling` | `0/1` | `0` | Master switch for the hydromechanical CPU prototype. | Keep |
| `PorePressureModel` | `0/1/2` | `0` | `0`: disabled, `1`: PR explicit pore-pressure-rate, `2`: PPE placeholder. | Keep `0/1`; make `2` a hard error |
| `PorePressureDtSafety` | float, `>0` | `0.1` | Safety factor for `dt_pore`. | Keep |
| `HydraulicGravityX/Y/Z` | float vector | `(0,0,0)` | Optional hydraulic gravity vector. If all components are zero, hydraulic gravity falls back to body `Gravity`. | Keep |
| `HydraulicElevationSource` | `0/1` | `1` | `1`: legacy hydrostatic/elevation convention with `k*LapZ`; `0`: CPU-only gravity-free mode using `HydraulicGravity` only for hydraulic scaling. | Experimental |
| `BodyGravityStopTime` | double [s] | `0` | Stops mechanical body gravity at the given physical time while leaving `HydraulicGravity` unchanged. `<=0`: body gravity remains active. | Keep |

The material/phase constants below are now soil material constants and should be written under `<execution><special><soils>` next to `ModulusE`, `PRvs`, `phi`, and `coh`:

| Soil parameter | Type / values | Default | Purpose | Keep? |
|---|---:|---:|---|---|
| `Porosity0` | float, `(0,1)` | `0.3` | Constant porosity `n` used in PR rate and pore timestep. | Keep |
| `HydraulicConductivity` | float, `>=0` | `0` | Hydraulic conductivity `k` [m/s]. If zero, diffusion and pore timestep restriction are disabled. | Keep |
| `WaterBulkModulus` | float, `>0` | `2e8` | Water bulk modulus `Kw` [Pa]. | Keep |
| `WaterDensity` | float, `>0` | `1000` | Water density `rho_w` [kg/m3]. | Keep |
| `FlexibleConfiningStress` | `0/1` | `0` | CPU-only flexible confining stress source for future strict Cryer loading. GPU hard-errors if enabled. | Experimental |
| `ConfiningStressP0` | float, `>=0` | `0` | Positive external compression magnitude [Pa]. | Experimental |
| `ConfiningStressRampStart` | double [s] | `0` | Linear ramp start time. | Experimental |
| `ConfiningStressRampEnd` | double [s] | `ConfiningStressRampStart` | Linear ramp end time. If equal to start, load is applied without ramp. | Experimental |
| `ConfiningStressTargetMk` | int | `-1` | `-1`: all normal material particles; otherwise target one `mkfluid` value. | Experimental |
| `ConfiningStressMode` | int | `0` | `0`: isotropic flexible confining stress. Other modes are reserved. | Experimental |

Recommended XML location:

```xml
<execution>
  <special>
    <soils>
      ...
      <Porosity0 value="0.3" />
      <HydraulicConductivity value="1e-3" />
      <WaterBulkModulus value="2e8" />
      <WaterDensity value="1000" />
      <FlexibleConfiningStress value="0" />
    </soils>
  </special>
</execution>
```

The old `<execution><parameters>` keys with the same names are temporarily still accepted as deprecated fallbacks for old cases. If both locations are present, `<special><soils>` overrides `<parameters>` and a warning is printed. `PorePressureDtSafety` remains a numerical timestep-control parameter under `<execution><parameters>`.

Current PR rate:

```text
PorePressRate =
  Kw/n * [
    -DivVel
    + k/(rho_w*g_h) * LapPorePress
    + k * LapZ
  ]
```

where `DivVel` is the mathematical divergence of skeleton velocity. Compression gives `DivVel < 0`; therefore the volumetric pore-pressure contribution is `-DivVel`.

When `HydraulicElevationSource=0`, the CPU PR rate omits the elevation term and
uses:

```text
PorePressRate =
  Kw/n * [
    -DivVel
    + k/(rho_w*g_h) * LapPorePress
  ]
```

`HydraulicGravity` must still provide a positive magnitude `g_h` when
`HydraulicConductivity>0`; it is used only for hydraulic scaling in this mode.
The hydrostatic reference is zero, so `ExcessPorePress` equals `PorePress`.
GPU execution with `HydraulicElevationSource=0` is unsupported in C4-D and
hard-errors during XML loading.

## Constitutive Skeleton Soil Parameters

The branch now has an explicit skeleton switch so strict poroelastic benchmarks
can bypass Drucker-Prager plasticity. These parameters are soil material
constants and must be written under `<execution><special><soils>`.

| Soil parameter | Type / values | Default | Purpose | Keep? |
|---|---:|---:|---|---|
| `SoilConstitutiveModel` | `0/1/2` | `1` or `2` when legacy `Softening=1` is present | `0`: linear elastic skeleton, `1`: Drucker-Prager, `2`: Drucker-Prager + exponential softening. | Keep |
| `Softening` | `0/1` | `0` | Legacy compatibility switch. If `Softening=1` and `SoilConstitutiveModel` is absent, the parser maps to model `2`. | Keep |
| `coh` | float, `>=0` | existing soil default | Peak cohesion `c_p`. | Keep |
| `phi` | float [deg] | existing soil default | Peak friction angle `phi_p`. Internally converted to radians. | Keep |
| `coh_r` | float, `>=0` | existing soil default | Residual cohesion `c_r`. | Keep |
| `phi_r` | float [deg] | existing soil default | Residual friction angle `phi_r`. Internally converted to radians. | Keep |
| `n_coh` | float, `>=0` | existing soil default | Exponential softening coefficient for cohesion. | Keep |
| `n_phi` | float, `>=0` | existing soil default | Exponential softening coefficient for friction angle. | Keep |

`SoilConstitutiveModel=0` accepts the elastic trial stress directly and forces
`Kplastic=0`. It bypasses Drucker-Prager yield evaluation, return mapping,
plastic strain accumulation, and softening. This is the required skeleton mode
for strict linear poroelastic Terzaghi/Cryer comparisons.

The implemented CPU softening law follows the u-pw paper Eq. (48) form using
the existing accumulated plastic strain state `Kplastic`:

```text
c(kappa)   = c_r   + (c_p   - c_r)   * exp(-n_coh * kappa)
phi(kappa) = phi_r + (phi_p - phi_r) * exp(-n_phi * kappa)
kappa      = Kplastic
```

When `SoilConstitutiveModel=1`, the existing Drucker-Prager path is unchanged.
When `SoilConstitutiveModel=2`, the stress update uses the softened local `c`
and `phi` during Drucker-Prager return mapping. `Kplastic` remains the primary
output for checking whether the softening path has been activated. Local
softened cohesion or friction angle are not stored as particle arrays in this
phase; analysis scripts can reconstruct them from `Kplastic`.

Example:

```xml
<execution>
  <special>
    <soils>
      <coh value="15100" />
      <phi value="0" />
      <coh_r value="1500" />
      <phi_r value="0" />
      <n_coh value="5" />
      <n_phi value="5" />
      <SoilConstitutiveModel value="2" />
    </soils>
  </special>
</execution>
```

Current limitations:

- It is a reduced DP-based sensitive-clay approximation, not a full remolding,
  destructuration, or MCC material branch.
- Full retrogressive landslide and Sainte-Monique reproduction still require
  calibration, production-scale runs, and likely GPU/material-model follow-up.

## Default Activation Policy

`HydromechCoupling=1` is an availability switch for the CPU u-pw PR module. It does not automatically enable a coupled consolidation setup. In particular, the following features remain opt-in and must be set explicitly in the XML:

```text
PorePressureInit
PorePressureTopDrained
PorePressureBottomNoFlux
PorePressureFeedback
PorePressureShepard
HydromechDamping
SavePorePressure
```

The only automatic or conditional behavior under `HydromechCoupling=1` is:

- `dt_pore` restriction is applied when `PorePressureModel=1` and the soil material `HydraulicConductivity > 0`.
- `HydraulicGravity` falls back to the body `Gravity` when `HydraulicGravityX/Y/Z` are all zero. If any custom hydraulic gravity component is nonzero, that custom vector is used for hydraulic scaling and, when `HydraulicElevationSource=1`, for hydraulic elevation, hydrostatic pressure, `LapZ`, hydraulic boundaries, and excess-pressure diagnostics.
- `HydraulicElevationSource=0` is the C4-D CPU-only gravity-free Cryer convention: positive `HydraulicGravity` magnitude remains required for hydraulic conductivity scaling, but the hydrostatic reference is zero and `k*LapZ` is omitted from `PorePressRate`.
- `BodyGravityStopTime`, when positive, only affects the mechanical body-gravity acceleration used by the CPU/GPU time integration. It does not modify the stored body `Gravity` vector and does not alter `HydraulicGravity`.
- `FlexibleConfiningStress=1` is CPU-only in C4-B3. It adds a positive-compression isotropic stress-like pair contribution to the mechanical momentum summation, does not write to the material stress tensor, and does not alter `PorePress`, `PorePressRate`, `LapPorePress`, `LapZ`, `AccInput`, or `HydraulicGravity`.

Recommended presets:

### Pressure-Only Diffusion

Use this preset to verify the PR hydraulic subsystem without mechanical feedback:

```xml
<parameter key="HydromechCoupling" value="1" />
<parameter key="PorePressureModel" value="1" />
<parameter key="PorePressureInit" value="3" />
<parameter key="PorePressureTopDrained" value="1" />
<parameter key="PorePressureBottomNoFlux" value="1" />
<parameter key="PorePressureFeedback" value="0" />
<parameter key="SavePorePressure" value="1" />
```

### Self-Weight / Terzaghi-Style Coupled Tests

Use excess-pressure feedback with the difference-gradient operator. This avoids applying hydrostatic pore pressure as a mechanical buoyancy-like feedback term and avoids the constant-pressure boundary spuriosity observed with the symmetric material-only feedback operator:

```xml
<parameter key="HydromechCoupling" value="1" />
<parameter key="PorePressureModel" value="1" />
<parameter key="PorePressureInit" value="1" />
<parameter key="PorePressureFeedback" value="1" />
<parameter key="PorePressureFeedbackMode" value="1" />
<parameter key="PorePressureFeedbackOperator" value="1" />
<parameter key="PorePressureTopDrained" value="1" />
<parameter key="PorePressureBottomNoFlux" value="1" />
<parameter key="PorePressureShepard" value="1" />
<parameter key="PorePressureShepardMode" value="1" />
<parameter key="HydromechDamping" value="1" />
<parameter key="HydromechDampingXi" value="..." />
<parameter key="SavePorePressure" value="1" />
```

Prefer `HydromechDampingXi` for Supporting-Information-style cases. It is converted internally to `c_d = xi * sqrt(E/(rho*h^2))`. Use `HydromechDampingCoef` only when a direct damping coefficient in `[1/s]` is intentionally required.

For Supporting Information self-weight Scenario 1, use `BodyGravityStopTime` to stop mechanical body gravity after the undrained generation stage while keeping `HydraulicGravityX/Y/Z` explicitly set to `(0,0,-9.81)`. This avoids relying on fallback semantics and keeps hydraulic elevation, `dt_pore`, and `LapZ` active after the mechanical body force is stopped.

### External-Load AccInput Experimental Path

For external-load Terzaghi experiments, use native DualSPHysics `accinput` applied to a dedicated top-layer `mkfluid` group. The former source-level `TopLoad*` path has been removed, so external loading should be defined entirely through XML `accinput` histories and `mkfluid` selection:

```xml
<parameter key="PorePressureFeedback" value="1" />
<parameter key="PorePressureFeedbackMode" value="1" />
<parameter key="PorePressureFeedbackOperator" value="1" />
<parameter key="PorePressureShepardMode" value="1" />
```

Set `PorePressureTopDrainedStartTime` to the end of the external-load ramp when testing staged undrained loading followed by drainage.

## 2. Initialization Parameters

| Parameter | Type / values | Default | Purpose | Keep? |
|---|---:|---:|---|---|
| `PorePressureInit` | `0/1/2/3` | `0` | `0`: zero pressure, `1`: hydrostatic, `2`: FromFile placeholder, `3`: hydrostatic + analytical excess. | Keep `0/1/3`; make `2` a hard error until implemented |
| `PorePressureWaterLevel` | float | `0` | Water level used for hydrostatic baseline. | Keep |
| `PorePressureExcessAmp` | float [Pa] | `0` | Amplitude of analytical excess pressure for `PorePressureInit=3`. | Keep |
| `PorePressureAnalyticalProfile` | `1/2/3` | `1` | `1`: `Amp*sin(pi*eta)`, `2`: `Amp*cos(pi*eta/2)`, `3`: uniform excess. | Keep |

Elevation coordinate:

```text
z_h = -dot(pos, HydraulicGravity / |HydraulicGravity|)
```

Hydrostatic baseline:

```text
p_hydro = rho_w * |g_h| * max(PorePressureWaterLevel - z_h, 0)
```

For `PorePressureInit=3`:

```text
PorePress = p_hydro + excess
```

with:

```text
eta = (z_h - zmin_material) / (zmax_material - zmin_material)
```

## 3. Hydraulic Boundary Parameters

| Parameter | Type / values | Default | Purpose | Keep? |
|---|---:|---:|---|---|
| `PorePressureTopDrained` | `0/1` | `0` | Enables top drained correction for excess pore pressure. | Keep |
| `PorePressureDrainThickness` | float [m] | `0` | Top drained layer thickness. If `<=0`, uses `KernelH`. | Keep |
| `PorePressureTopDrainedStartTime` | double [s] | `0` | Time when top drained boundary becomes active. If `0`, active from the start. | Keep |
| `PorePressureBottomNoFlux` | `0/1` | `0` | Enables bottom no-flux layer correction for excess pore pressure. | Keep |
| `PorePressureBottomNoFluxThickness` | float [m] | `0` | Bottom no-flux layer thickness. If `<=0`, uses `KernelH`. | Keep |
| `PorePressureBoundaryOperator` | `0/1/2/3` | `0` | Optional production PR boundary contribution. `0`: legacy layer correction only; `1`: virtual ghost operator prototype; `2`: CPU-only hydraulic boundary-particle prototype; `3`: CPU-only drained curved Dirichlet ghost prototype. | Experimental |
| `PorePressureCurvedDrained` | `0/1` | `0` | Enables mode `3` curved drained boundary. Requires `PorePressureBoundaryOperator=3`. | Experimental |
| `CurvedDrainedBoundaryCenterX/Y/Z` | double [m] | `0` | Sphere center for mode `3`. | Experimental |
| `CurvedDrainedBoundaryRadius` | double [m], `>0` | `0` | Sphere radius for mode `3`. | Experimental |
| `CurvedDrainedBoundaryTargetMk` | int | `-1` | Target mkfluid for mode `3`; `-1` means all material particles. | Experimental |
| `CurvedDrainedBoundaryValue` | double [Pa] | `0` | Prescribed drained boundary value. | Experimental |
| `CurvedDrainedBoundaryUseExcess` | `0/1` | `1` | `1`: value is excess pressure; `0`: value is total pressure. | Experimental |
| `CurvedDrainedBoundaryThickness` | double [m] | `0` | Interior shell thickness for ghost placement; if `<=0`, uses `KernelH`. | Experimental |
| `CurvedDrainedBoundaryMode` | `0/1/2/3` | `0` | Mode `3` subtype. `0`: first-order spherical Dirichlet ghost; `1`: strengthened image Dirichlet ghost; `2`: diagnostic material surface drained clamp after pressure update, not production; `3`: multi-sample spherical Dirichlet boundary quadrature, CPU-only experimental. | Experimental |

Top drained correction:

```text
if z_h >= zmax_material - drain_thickness:
    PorePress = p_hydro
```

Bottom no-flux layer correction:

```text
bottom layer:
    z_h <= zmin_material + bottom_thickness

reference layer:
    zmin_material + bottom_thickness < z_h <= zmin_material + 2*bottom_thickness

bottom excess = mean(reference layer excess)
```

This is a minimal layer correction, not a full mirror/ghost pore-pressure boundary treatment.

`PorePressureBoundaryOperator=1` adds virtual boundary contributions to the
production `LapPorePress` and `LapZ` operators before `PorePressRate` is
computed. Top drained uses an excess-pressure Dirichlet ghost (`excess=0`).
Bottom no-flux uses a hydraulic-head convention, implemented as a mirrored
excess pressure (`d excess/dn=0`) rather than a zero total-pressure gradient.
The legacy layer correction remains active as a safety projection. This mode is
available on CPU and GPU, but remains experimental and is not the default.

`PorePressureBoundaryOperator=2` is an H1 CPU-only experimental prototype for
hydraulic mDBC-style boundary-particle reconstruction. Boundary particles do not
store an advected pore-pressure degree of freedom; instead, their hydraulic
state is reconstructed on the fly and contributes to `LapPorePress`/`LapZ`
quadrature. Top boundary particles use `excess=0`; bottom boundary particles
reconstruct excess pressure from neighbouring material particles to represent
head/excess Neumann consistency. GPU runs with mode `2` are unsupported and
should fail rather than silently falling back to mode `0`.

`PorePressureBoundaryOperator=3` is a C4-C CPU-only experimental prototype for
a drained curved boundary, currently designed for spherical Cryer smokes. It
selects material particles near a prescribed spherical exterior and adds an
outward Dirichlet ghost state to `LapPorePress` and `LapZ` before
`PorePressRate` is computed. The default convention is
`CurvedDrainedBoundaryUseExcess=1` with `CurvedDrainedBoundaryValue=0`, i.e.
drained excess pore pressure. It does not clamp material pore pressure after
the update. GPU runs with mode `3` or `PorePressureCurvedDrained=1` are
unsupported and should fail rather than silently falling back to mode `0`.

## 4. Feedback Parameters

| Parameter | Type / values | Default | Purpose | Keep? |
|---|---:|---:|---|---|
| `PorePressureFeedback` | `0/1` | `0` | Enables pore-pressure acceleration feedback to `Acec`. | Keep |
| `PorePressureFeedbackMode` | `0/1` | `0` | `0`: use total `PorePress`; `1`: use excess `PorePress - p_hydro`. | Keep |
| `PorePressureFeedbackOperator` | `0/1` | `0` | `0`: symmetric stress-style operator; `1`: difference-gradient operator. | Keep |

Recommended for Terzaghi/self-weight tests:

```xml
<parameter key="PorePressureFeedback" value="1" />
<parameter key="PorePressureFeedbackMode" value="1" />
<parameter key="PorePressureFeedbackOperator" value="1" />
```

Rationale:

- `Mode=1` avoids applying mechanical feedback from the hydrostatic baseline.
- `Operator=1` avoids the large missing-neighbor boundary force observed with material-only symmetric feedback under constant excess pressure.

Current operators:

```text
Operator 0: symmetric stress-style diagnostic
  a_pw = -sum_j m_j * (p_i+p_j)/(rho_i*rho_j) * gradW_ij

Operator 1: difference-gradient feedback
  gradp_i = sum_j (m_j/rho_j) * (p_j-p_i) * gradW_ij
  a_pw = -gradp_i/rho_i
```

`Sigmac` remains the skeleton effective stress. Pore pressure is not subtracted from `Sigmac`; it is fed back as an acceleration term.

## 5. Stabilization Parameters

| Parameter | Type / values | Default | Purpose | Keep? |
|---|---:|---:|---|---|
| `PorePressureShepard` | `0/1` | `0` | Enables Shepard regularization of pore pressure. | Keep |
| `PorePressureShepardInterval` | integer `>0` when enabled | `20` | Applies Shepard regularization every N time steps. | Keep |
| `PorePressureShepardMode` | `0/1` | `0` | `0`: regularize total `PorePress`; `1`: regularize excess pressure. | Keep |
| `HydromechDamping` | `0/1` | `0` | Enables hydromechanical kinematic damping. | Keep |
| `HydromechDampingXi` | float | `0` | Dimensionless damping coefficient from the Supporting Information. If `>0`, the code computes `c_d=xi*sqrt(E/(rho0*h^2))`. | Keep |
| `HydromechDampingCoef` | float [1/s] | `0` | Direct damping coefficient `c_d` in `a_damp=-c_d*v`. Compatibility/debug input; do not set together with `HydromechDampingXi`. | Keep |
| `HydromechDampingStartTime` | double [s] | `0` | Damping activation time. | Keep |
| `HydromechDampingEndTime` | double [s] | `0` | If `> start`, damping is disabled after this time. If `<= start`, damping remains active after start. | Keep |

Shepard regularization:

```text
p_i_reg =
  sum_j (m_j/rho_j) p_j W_ij
  /
  sum_j (m_j/rho_j) W_ij
```

Mode `1` applies the same formula to excess pressure and then reconstructs:

```text
PorePress = p_hydro + excess_reg
```

Hydromechanical damping:

```text
a_damp = -c_d * v
```

The preferred paper-aligned input is now `HydromechDampingXi`. When `HydromechDampingXi>0`, the effective coefficient is computed as:

```text
c_d = xi * sqrt(E / (rho * h^2))
```

where the implementation uses `E=SoilCte.ModulusE`, `rho=RhopZero`, and `h=KernelH`.

`HydromechDampingCoef` is still supported as a direct `c_d [1/s]` compatibility/debug input. Do not set both `HydromechDampingXi` and `HydromechDampingCoef` in the same case.

For a typical 1D consolidation case:

```text
E   = 2e6 Pa
rho = 2100 kg/m3
h   = 0.018 m

sqrt(E/(rho*h^2)) ~= 1714 1/s

xi = 4e-5 -> c_d ~= 0.0686 1/s
xi = 0.01 -> c_d ~= 17.1 1/s
xi = 0.05 -> c_d ~= 85.7 1/s
```

## 6. Output Parameters

| Parameter | Type / values | Default | Purpose | Keep? |
|---|---:|---:|---|---|
| `SavePorePressure` | `0/1` | `0` | Enables pore-pressure diagnostic output. | Keep |

When enabled and corresponding arrays exist, current output includes:

```text
PorePress
ExcessPorePress
PorePressRate
DivVel
LapPorePress
LapZ
PorePressureAccel
PorePressureAccelDiff
```

Recommended long-term output set:

```text
PorePress
ExcessPorePress
PorePressRate
DivVel
LapPorePress
LapZ
PorePressureAccelDiff
```

`PorePressureAccel` can remain as a comparison diagnostic. `PorePressureAccelDiff` is the recommended production feedback diagnostic for Terzaghi/self-weight cases.

## 7. Removed / Temporary Parameters And Interfaces

### Removed Source-Side TopLoad Parameters

Removed in CPU-F6a:

```text
TopLoadEnabled
TopLoad
TopLoadThickness
TopLoadRampStart
TopLoadRampEnd
```

Historical behavior:

```text
a_load = TopLoad / (rho * top_load_thickness)
```

applied as a body-acceleration equivalent to the top material layer.

Reason for removal:

- It duplicates functionality available through native DualSPHysics `accinput`.
- It is sensitive to layer selection and can inject strong local momentum.
- It is not the preferred route for reproducing external-load Terzaghi tests.

Current external-load path:

```text
Use native DualSPHysics accinput with a dedicated top-layer mkfluid group.
```

Archived XML files under `examples/u-pw/**/experiments/` may still contain
historical `TopLoad*` keys. They document failed/deprecated experiments and are
not guaranteed to parse after CPU-F6a. Formal case XML should not contain
`TopLoad*`.

### Removed `PorePressureAccelSymCorr`

Removed diagnostic:

```text
PorePressureAccelSymCorr
PorePressureAceSymCorrc
```

Reason for removal:

- It was added to test symmetric feedback with corrected gradient.
- It did not reduce the constant-excess boundary spurious force.
- In the tested 1D column, it amplified the boundary spike.

Recommended action:

```text
Removed in CPU-F1a. Do not port to GPU.
```

### `PorePressureModel=2`

Temporary placeholder:

```text
PorePressureModel=2: PPE
```

PPE is not implemented in this branch.

Recommended action:

```text
Treat PorePressureModel=2 as a hard error:
"PPE formulation is not implemented in this branch. Use PorePressureModel=1 for PR."
```

## 8. Recommended Settings

### A. Pressure-Only Diffusion

Purpose: verify pore-pressure diffusion/elevation-head subsystem without mechanical feedback.

```xml
<parameter key="HydromechCoupling" value="1" />
<parameter key="PorePressureModel" value="1" />
<parameter key="PorePressureInit" value="3" />
<parameter key="PorePressureAnalyticalProfile" value="3" />
<parameter key="PorePressureExcessAmp" value="10000" />

<parameter key="PorePressureTopDrained" value="1" />
<parameter key="PorePressureTopDrainedStartTime" value="0" />
<parameter key="PorePressureBottomNoFlux" value="1" />

<parameter key="PorePressureFeedback" value="0" />
<parameter key="PorePressureShepard" value="0" />
<parameter key="SavePorePressure" value="1" />
```

Expected:

- `DivVel` contribution is near zero.
- `ExcessPorePress` decays smoothly.
- Top drained layer remains near zero excess.
- Bottom no-flux layer has a small gradient proxy.

### B. Self-Weight Undrained Response

Purpose: compare early self-weight-generated undrained pore pressure to Supporting Information Eq. (4).

```xml
<parameter key="HydromechCoupling" value="1" />
<parameter key="PorePressureModel" value="1" />
<parameter key="PorePressureInit" value="1" />
<parameter key="PorePressureWaterLevel" value="1.0" />

<parameter key="PorePressureFeedback" value="1" />
<parameter key="PorePressureFeedbackMode" value="1" />
<parameter key="PorePressureFeedbackOperator" value="1" />

<parameter key="PorePressureTopDrained" value="1" />
<parameter key="PorePressureTopDrainedStartTime" value="999" />
<parameter key="PorePressureBottomNoFlux" value="1" />

<parameter key="PorePressureShepard" value="1" />
<parameter key="PorePressureShepardInterval" value="20" />
<parameter key="PorePressureShepardMode" value="1" />

<parameter key="HydromechDamping" value="1" />
<parameter key="HydromechDampingXi" value="0.05" />

<parameter key="SavePorePressure" value="1" />
```

Recommended comparison:

```text
total PorePress vs Eq.(4)
ExcessPorePress vs Eq.(4) - hydrostatic
```

Do not compare `ExcessPorePress` directly to Eq. (4) when the initial condition is hydrostatic.

### C. Self-Weight Scenario 2: Gravity-On Dissipation

Purpose: allow pore pressure to evolve with body gravity still active.

Suggested starting point:

```xml
<parameter key="PorePressureInit" value="1" />
<parameter key="PorePressureFeedback" value="1" />
<parameter key="PorePressureFeedbackMode" value="1" />
<parameter key="PorePressureFeedbackOperator" value="1" />

<parameter key="PorePressureTopDrained" value="1" />
<parameter key="PorePressureTopDrainedStartTime" value="0.002" />
<parameter key="PorePressureBottomNoFlux" value="1" />

<parameter key="PorePressureShepard" value="1" />
<parameter key="PorePressureShepardInterval" value="20" />
<parameter key="PorePressureShepardMode" value="1" />

<parameter key="HydromechDamping" value="1" />
<parameter key="HydromechDampingXi" value="0.05" />
```

Notes:

- First validate the undrained response window.
- Then activate top drainage.
- Do not begin with long dissipation runs before the early self-weight response is stable.

### D. External-Load Terzaghi Experimental Path

Purpose: exploratory external-load consolidation test.

Recommended route:

- Do not use source-level `TopLoad`.
- Use native DualSPHysics `accinput`.
- Split the top material layer into a dedicated `mkfluid`.
- Apply a small ramped vertical acceleration to that top-layer group.

Suggested hydromech settings:

```xml
<parameter key="PorePressureInit" value="1" />
<parameter key="PorePressureFeedback" value="1" />
<parameter key="PorePressureFeedbackMode" value="1" />
<parameter key="PorePressureFeedbackOperator" value="1" />

<parameter key="PorePressureTopDrained" value="1" />
<parameter key="PorePressureTopDrainedStartTime" value="ramp_end" />
<parameter key="PorePressureBottomNoFlux" value="1" />

<parameter key="PorePressureShepard" value="1" />
<parameter key="PorePressureShepardMode" value="1" />
<parameter key="HydromechDamping" value="1" />
```

Start with very small loads. Do not jump directly to `q0=-10 kPa`.

## 9. Current Cleanup Roadmap

Recommended cleanup order:

1. Document parameters in this file.
2. Convert `PorePressureModel=2` to a hard error.
3. Continue SW-2c self-weight refinement.
4. Removed `PorePressureAccelSymCorr` and `PorePressureAceSymCorrc` in CPU-F1a.
5. Removed source-level `TopLoad*` and `ApplyTopLoad()` in CPU-F6a.

Do not combine cleanup of TopLoad, SymCorr, and PPE placeholder into one patch.
