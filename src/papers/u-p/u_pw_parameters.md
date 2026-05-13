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
| `InitialStressMode` | `0/1` | `0` | CPU-only initial skeleton/effective stress initialization. `0`: none, `1`: uniform isotropic effective compression. GPU hard-errors if enabled. | Experimental |
| `InitialEffectiveStressIso` | float, `>=0` | `0` | Positive initial effective compression magnitude [Pa]. CPU writes this as negative `Sigmac.xx=Sigmac.yy=Sigmac.zz` because compressive skeleton/effective stress is negative in the current stress convention. | Experimental |
| `InitialEffectiveStressTargetMk` | int | `-1` | `-1`: all normal material particles; otherwise target one `mkfluid` value for initial effective stress. | Experimental |

The material/phase constants below are now soil material constants and should be written under `<execution><special><soils>` next to `ModulusE`, `PRvs`, `phi`, and `coh`:

| Soil parameter | Type / values | Default | Purpose | Keep? |
|---|---:|---:|---|---|
| `Porosity0` | float, `(0,1)` | `0.3` | Constant porosity `n` used in PR rate and pore timestep. | Keep |
| `HydraulicConductivity` | float, `>=0` | `0` | Hydraulic conductivity `k` [m/s]. If zero, diffusion and pore timestep restriction are disabled. | Keep |
| `WaterBulkModulus` | float, `>0` | `2e8` | Water bulk modulus `Kw` [Pa]. | Keep |
| `WaterDensity` | float, `>0` | `1000` | Water density `rho_w` [kg/m3]. | Keep |
| `FlexibleConfiningStress` | `0/1` | `0` | CPU-only flexible confining stress source for spherical/triaxial confinement diagnostics. GPU hard-errors if enabled. | Experimental |
| `ConfiningStressP0` | float, `>=0` | `0` | Positive external compression magnitude [Pa]. | Experimental |
| `ConfiningStressRampStart` | double [s] | `0` | Linear ramp start time. | Experimental |
| `ConfiningStressRampEnd` | double [s] | `ConfiningStressRampStart` | Linear ramp end time. If equal to start, load is applied without ramp. | Experimental |
| `ConfiningStressTargetMk` | int | `-1` | `-1`: all normal material particles; otherwise target one `mkfluid` value. | Experimental |
| `ConfiningStressMode` | int | `0` | `0`: isotropic flexible confining stress. Other modes are reserved. | Experimental |
| `ConfiningStressGradientMode` | `0/1` | `0` | `0`: raw kernel gradient, legacy behavior. `1`: CPU renormalized/corrected kernel gradient for the flexible confining stress pair term only. GPU hard-errors when this mode is enabled. | Experimental |
| `FlexibleConfiningStressFiDiagnostic` | `0/1` | `0` | Computes Zhao-style kernel completeness `f_i = sum_j (m_j/rho_j) W_ij` for material targets. Diagnostic only unless selector is enabled. | Experimental |
| `SaveConfiningStressDiagnostics` | `0/1` | `0` | Prints extended CPU confinement diagnostics: target counts, `f_i` summary, cylinder classes, net force, radial tendency, and cap leakage. | Experimental |
| `ConfiningStressFiThreshold` | float, `>0` | `0.70` | Candidate near-boundary threshold for `f_i` selector. Zhao suggests `0.70` for 3D diagnostics. | Experimental |
| `ConfiningStressGeometry` | `0/1` | `0` | `0`: no geometry classification, `1`: cylinder classification for triaxial diagnostics. | Experimental |
| `ConfiningStressCylinderCenterX/Y/Z` | float vector | `(0,0,0)` | Cylinder base/axis reference point for confinement classification. | Experimental |
| `ConfiningStressCylinderAxisX/Y/Z` | float vector | `(0,0,1)` | Cylinder axis direction. The parser normalizes it and rejects zero length. | Experimental |
| `ConfiningStressCylinderRadius` | float, `>0` if geometry enabled | `0` | Cylinder radius for lateral/cap classification. | Experimental |
| `ConfiningStressCylinderHeight` | float, `>0` if geometry enabled | `0` | Cylinder height along the axis for cap and lateral classification. | Experimental |
| `ConfiningStressCapExclusionLength` | float, `>=0` | `0` | Cap exclusion length. If zero, defaults to `KernelSize`. | Experimental |
| `ConfiningStressEdgeExclusionLength` | float, `>=0` | `0` | Radial edge-ring tolerance. If zero, defaults to `KernelSize`. | Experimental |
| `ConfiningStressUseFiSelector` | `0/1` | `0` | If enabled, applies the confining force only to target particles with `f_i <= ConfiningStressFiThreshold`. | Experimental |
| `ConfiningStressUseLateralSelector` | `0/1` | `0` | If enabled, applies the confining force only to cylinder lateral particles; requires `ConfiningStressGeometry=1`. | Experimental |
| `ConfiningStressLateralSelectorStartTime` | double [s] | `0` | CPU-only staged selector switch. When `ConfiningStressUseLateralSelector=1` and this value is `>0`, the run starts with the lateral selector disabled and activates it at the given time. Values `<=0` preserve legacy immediate lateral-selector behavior. GPU hard-errors for non-default scheduling. | Experimental |
| `CapConfiningStress` | `0/1` | `0` | CPU-only top/bottom cap-normal hydrostatic support diagnostic for reduced triaxial staging. Not a production platen-boundary route. GPU hard-errors if enabled. | Diagnostic |
| `CapConfiningStressP0` | float, `>=0` | `0` | Positive external compression magnitude [Pa] for cap-normal support. | Experimental |
| `CapConfiningStressRampStart` | double [s] | `0` | Linear cap-support ramp start time. | Experimental |
| `CapConfiningStressRampEnd` | double [s] | `CapConfiningStressRampStart` | Linear cap-support ramp end time. If equal to start, load is applied without ramp. | Experimental |
| `CapConfiningStressTopMk` | int | `-1` | `-1`: all top-cap material particles; otherwise target one `mkfluid` value. | Experimental |
| `CapConfiningStressBottomMk` | int | `-1` | `-1`: all bottom-cap material particles; otherwise target one `mkfluid` value. | Experimental |
| `CapConfiningStressMode` | int | `0` | `0`: uniform integrated pressure force `p0*pi*R^2` distributed over selected top/bottom cap mass. | Experimental |
| `CapConfiningStressAxisX/Y/Z` | float vector | `(0,0,1)` | Cylinder axial direction for cap support. The parser normalizes it; top receives `-axis`, bottom receives `+axis`. | Experimental |
| `SaveCapConfiningStressDiagnostics` | `0/1` | `0` | Prints CPU cap-support diagnostics: target counts, edge-ring skipped count, cap acceleration, net force, and symmetry residual. | Experimental |

T3 confinement diagnostic/selector keys are currently parsed under
`<execution><parameters>` together with the original flexible-confinement
controls. They are opt-in and leave the legacy force target set unchanged when
both selector flags are zero.

T4l cap-support keys are also parsed under `<execution><parameters>`. They are
intended only for reduced triaxial hydrostatic staging diagnostics. The cap
support is not axial deviatoric loading, is not written into the stress tensor,
and skips cylinder edge-ring particles to avoid double-counting lateral
flexible confinement.

T4p reclassifies `CapConfiningStress` as diagnostic-only. T4o showed that this
explicit acceleration patch does not preserve the all-surface hydrostatic state
and should not be tuned into a production triaxial cap/platen formulation. A
strict triaxial workflow should instead use explicit bottom/top platen groups,
with bottom fixed, top prescribed in velocity or displacement, lateral
`FlexibleConfiningStress`, specimen-only measurements, and reaction-force
diagnostics.

T4n adds `ConfiningStressLateralSelectorStartTime` for a single-run
all-surface-to-lateral confinement switch. It only changes the target selection
of `FlexibleConfiningStress`; it does not change the confinement force formula,
`f_i` diagnostics, PR pressure update, stress update, or axial loading. The
default keeps the previous static selector behavior.

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
- `ConfiningStressGradientMode=1` is a T4b opt-in Zhao-style diagnostic path. It computes a local first-order correction matrix from target material neighbours and applies the corrected gradient only to the flexible confinement pair term. The default `0` keeps the previous raw-gradient behavior. GPU execution hard-errors when mode `1` is requested.

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
| `PorePressureBoundaryOperator` | `0/1/2/3` | `0` | Optional production PR boundary contribution. `0`: legacy layer correction only; `1`: virtual ghost operator prototype; `2`: CPU-only hydraulic boundary-particle prototype; `3`: CPU-only drained curved Dirichlet prototype. | Experimental |
| `PorePressureCurvedDrained` | `0/1` | `0` | Enables mode `3` curved drained boundary. Requires `PorePressureBoundaryOperator=3`. | Experimental |
| `CurvedDrainedBoundaryCenterX/Y/Z` | double [m] | `0` | Sphere center for mode `3`. | Experimental |
| `CurvedDrainedBoundaryRadius` | double [m], `>0` | `0` | Sphere radius for mode `3`. | Experimental |
| `CurvedDrainedBoundaryTargetMk` | int | `-1` | Target mkfluid for mode `3`; `-1` means all material particles. | Experimental |
| `CurvedDrainedBoundaryValue` | double [Pa] | `0` | Prescribed drained boundary value. | Experimental |
| `CurvedDrainedBoundaryUseExcess` | `0/1` | `1` | `1`: value is excess pressure; `0`: value is total pressure. | Experimental |
| `CurvedDrainedBoundaryThickness` | double [m] | `0` | Interior shell thickness for ghost placement; if `<=0`, uses `KernelH`. | Experimental |
| `CurvedDrainedBoundaryMode` | `0/1/2/3/4/5/6/7/8` | `0` | Mode `3` subtype. `0`: first-order spherical Dirichlet ghost; `1`: strengthened image Dirichlet ghost; `2`: diagnostic material surface drained clamp after pressure update, not production; `3`: material-side multi-sample spherical Dirichlet boundary quadrature; `4`: boundary-particle prescribed Dirichlet hydraulic state; `5`: radial MLS / integrated flux correction; `6`: radial-shell / FV flux correction; `7`: conservative multi-shell radial exchange; `8`: boundary-aware corrected quadratic MLS Laplacian. | Experimental |

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

For `PorePressureBoundaryOperator=3`, `CurvedDrainedBoundaryMode` currently
selects the CPU-only experimental subroute:

- `0`: first-order spherical Dirichlet ghost;
- `1`: strengthened image ghost;
- `2`: diagnostic material surface clamp, not production;
- `3`: material-side multi-sample spherical Dirichlet quadrature;
- `4`: boundary-particle prescribed Dirichlet hydraulic state;
- `5`: radial MLS / integrated flux correction, CPU-only experimental;
- `6`: radial-shell / FV flux correction, CPU-only experimental;
- `7`: conservative multi-shell radial exchange, CPU-only experimental;
- `8`: boundary-aware corrected quadratic MLS Laplacian, CPU-only experimental.

Mode `4` is the C5e paper-style boundary-particle prototype. It uses selected
boundary particles as hydraulic quadrature sites, prescribes the drained value
(`p_w=0`, or `excess=0` under no-elevation Cryer convention), and contributes
to `LapPorePress`/`LapZ`. It does not advect boundary pore pressure, does not
clamp material particles, and remains CPU-only experimental.

Additional mode-4 parameters:

| Parameter | Type / values | Default | Purpose |
|---|---:|---:|---|
| `CurvedDrainedBoundaryTargetMkBound` | integer, `-1` or mkbound | `-1` | Select all spherical boundary particles or only a specific `mkbound`. |
| `CurvedDrainedBoundaryUseBoundaryParticles` | `0/1` | `1` | Required for mode `4`; enables selected boundary-particle participation. |
| `CurvedDrainedBoundarySelectionTolerance` | length | `0` | Radius tolerance for selecting boundary particles. If `0`, uses a kernel/dp-based fallback. |
| `CurvedDrainedBoundaryAdamiDiagnostic` | `0/1` | `0` | Computes normalized-kernel extrapolated boundary pressure as diagnostics only; it is not used as the drained value. |
| `CurvedDrainedBoundaryWeighting` | `0/1/3` | `0` | Mode-4 boundary-particle effective-volume weighting. `0`: raw boundary-particle volume weighting; `1`: Adami-style local partition normalization; `3`: diagnostic missing-support capped weighting, not production. |

Mode-4 weighting notes:

- `0` preserves the C5e behavior and is the default for backward
  compatibility inside the experimental mode.
- `1` computes local material and boundary kernel partitions around each
  material target and scales boundary effective volume by
  `min(1, 1/(S_m+S_b))`.
- `3` scales by the estimated missing support `max(0,1-S_m)/S_b` and is
  diagnostic only.
- The drained boundary value remains prescribed; the weighting modes do not
  use Adami extrapolation to define `p_b`.

Mode `5` is the C5j MLS / flux-consistent prototype. It estimates the
spherical normal gradient with a constrained radial linear MLS fit against the
physical drained surface value (`p_b=0` for Cryer no-elevation pressure-only
diffusion), then applies a shell-average integrated `LapPorePress` correction.
It does not clamp material pressure, does not count dummy boundary-particle
volumes, and does not change the PR governing equation. C5j pressure-only
testing showed that this prototype runs with `code=0`, `excluded=0`, and
`Kplastic=0`, but it does not yet pass the FV radial diffusion gate because the
surface shell remains too pressurized and late-time flux remains too strong.

Additional mode-5 parameters:

| Parameter | Type / values | Default | Purpose |
|---|---:|---:|---|
| `CurvedDrainedMLSOrder` | `0/1` | `1` | MLS order for mode `5`. `1`: constrained radial linear fit; `0`: fallback route. |
| `CurvedDrainedMLSRadiusFactor` | float | `1` | Support radius multiplier on `KernelH`; `0` also uses `KernelH`. |
| `CurvedDrainedFluxDiagnostics` | `0/1` | `0` | Print per-step mode-5, mode-6, or mode-7 flux diagnostics. Mode `8` has its own corrected-Laplacian diagnostics switch. |
| `CurvedDrainedMLSConditionLimit` | float | `1e8` | Maximum accepted local moment condition number. |
| `CurvedDrainedMLSFallbackMode` | `3/4` | `3` | Fallback if local MLS support is invalid or ill-conditioned. |

Mode `6` is the C5k radial-shell / FV flux prototype. It uses
`CurvedDrainedBoundaryThickness` as the outer shell width, computes
volume-weighted shell pressure and radius near the prescribed sphere, estimates
the drained boundary flux against `p_b=0`, and distributes the integrated
`4*pi*R^2*q_R` loss as a `LapPorePress` correction over the outer material
shell. It does not clamp material pressure, does not count dummy boundary
particle volumes, and does not change the PR governing equation. C5k
pressure-only testing showed that mode `6` runs with `code=0`, `excluded=0`,
and `Kplastic=0`, but it does not yet pass the FV radial diffusion gate:
`dp=0.010` improves median flux ratio while keeping the surface shell too high,
and `dp=0.008` develops late apparent flux reversal.

Mode `7` is the C5m conservative multi-shell radial exchange prototype. It
partitions the sphere into radial shells and computes FV interface fluxes
between shell-average pressures, with spherical symmetry at the center and
`p_b=0` at the drained outer radius. The default C5m gate uses
`CurvedDrainedShellCorrectionMode=1`, which adds a shell-average correction to
the existing `LapPorePress` so each populated shell's volume-integrated storage
rate matches the FV flux balance. It does not clamp material pressure and does
not count dummy boundary volume. In this prototype, mode `7` is restricted to
`HydraulicElevationSource=0`.

Additional mode-7 parameters:

| Parameter | Type / values | Default | Purpose |
|---|---:|---:|---|
| `CurvedDrainedShellCount` | unsigned | `0` | Number of radial shells for mode `7`; `0` uses an automatic count from radius and shell thickness/dp. |
| `CurvedDrainedShellMinParticles` | unsigned | `1` | Minimum particles required in a populated shell before fallback. |
| `CurvedDrainedShellMode` | `0/1` | `0` | `0`: automatic shell count; `1`: fixed `CurvedDrainedShellCount`. |
| `CurvedDrainedShellCorrectionMode` | `0/1` | `1` | `0`: replace per-particle diffusion rate by the shell FV rate; `1`: add shell-average correction to the existing SPH diffusion rate. |
| `CurvedDrainedShellDiagnostics` | `0/1` | `0` | Print per-step shell populations, means, interface fluxes, correction rates, and conservation residuals. |

Mode `8` is the C5n boundary-aware corrected Laplacian prototype. It applies a
local quadratic MLS recovery only near the curved drained sphere:

```text
p(xi) ~= a0 + a1 xi_x + a2 xi_y + a3 xi_z
       + a4 xi_x^2 + a5 xi_y^2 + a6 xi_z^2
       + a7 xi_x xi_y + a8 xi_x xi_z + a9 xi_y xi_z

nabla^2 p = 2 (a4 + a5 + a6)
```

Material neighbors and tangential samples on the physical sphere enter the
least-squares system. Under the Cryer no-elevation pressure-only convention,
the boundary samples use the prescribed drained value `p_b=0`. Mode `8`
replaces near-boundary `LapPorePress`; it does not clamp `PorePress` and does
not count dummy boundary-particle volume. C5n showed that mode `8` fixes
manufactured polynomial consistency, but it does not pass the dynamic
pressure-only FV radial diffusion gate.

Additional mode-8 parameters:

| Parameter | Type / values | Default | Purpose |
|---|---:|---:|---|
| `CurvedDrainedCorrectedLapRadiusFactor` | float | `2` | Support radius multiplier on `KernelH`; `0` uses `KernelSize`. |
| `CurvedDrainedCorrectedLapRMinFactor` | float in `[0,1]` | `0.7` | Minimum normalized radius where the corrected Laplacian replaces `LapPorePress`. |
| `CurvedDrainedCorrectedLapBoundarySamples` | unsigned | `9` | Number of tangential spherical boundary samples, including the projected point. |
| `CurvedDrainedCorrectedLapMinSamples` | unsigned | `12` | Minimum total MLS samples before fallback. |
| `CurvedDrainedCorrectedLapConditionLimit` | float | `1e12` | Maximum accepted local condition estimate. |
| `CurvedDrainedCorrectedLapBoundaryWeight` | float | `1` | Relative weight for Dirichlet boundary samples. |
| `CurvedDrainedCorrectedLapFallbackMode` | `0/4` | `0` | `0`: keep existing material `LapPorePress`; `4`: use a local gap fallback. |
| `CurvedDrainedCorrectedLapDiagnostics` | `0/1` | `0` | Print per-step mode-8 sample, condition, fallback, and replacement diagnostics. |
| `CurvedDrainedCorrectedLaplacianLimiter` | `0/1/3` | `0` | Mode-8-only limiter. `0`: off, old C5n behavior; `1`: positivity cap on negative diffusion-rate strength; `3`: blend corrected MLS and material Laplacian. |
| `CurvedDrainedLimiterCFL` | float in `[0,1]` | `0.9` | CFL-like pressure-gap fraction used by the positivity limiter with the current/previous time-step estimate. |
| `CurvedDrainedLimiterBlend` | float in `[0,1]` | `1` | Blend factor `theta` for `theta*Lap_MLS + (1-theta)*Lap_material` when limiter `3` is active. |
| `CurvedDrainedLimiterPreventNegative` | `0/1` | `0` | Apply the positivity cap after the selected mode-8 limiter. |

C5o tested these mode-8 limiters in the pressure-only spherical FV gate. Blend
`0.25` improved center pressure and reduced the pressure-rate artifact, but the
surface shell remained far from the FV reference and apparent flux reversal
persisted. These limiter controls therefore remain diagnostic and should not be
used as a production strict-Cryer boundary.

### C5q Cryer Interface Cleanup Status

C5p froze the strict Cryer route after the pressure-only spherical FV diffusion
gate failed. C5q keeps production defaults unchanged and marks the Cryer
experimental boundary corrections as archived diagnostics.

Status after C5q:

- `PorePressureBoundaryOperator=0` remains the production default.
- `PorePressureBoundaryOperator=1` remains experimental and GPU-supported.
- `PorePressureBoundaryOperator=2` remains CPU-only experimental.
- `PorePressureBoundaryOperator=3` remains CPU-only experimental for archived
  curved-drained research. It is not a validated strict Cryer boundary.
- `CurvedDrainedBoundaryMode=0/1` are retained as simple experimental ghost
  baselines.
- `CurvedDrainedBoundaryMode=4` is retained as an experimental
  boundary-particle prescribed drained route, but it did not pass the
  pressure-only FV gate and is not validated for new production cases.
- `CurvedDrainedBoundaryMode=5/6/7/8`, `CurvedDrainedMLS*`,
  `CurvedDrainedShell*`, `CurvedDrainedCorrectedLap*`, and
  `CurvedDrainedLimiter*` are deprecated archived Cryer experiments. They
  should not be used for new cases unless a new boundary formulation review is
  opened.
- `CurvedDrainedBoundaryWeighting=3` is diagnostic capped weighting only.
- No C6 Figure 7B comparison should start without a new drained-boundary
  formulation and a passing pressure-only spherical FV diffusion gate.

## 4. Feedback Parameters

| Parameter | Type / values | Default | Purpose | Keep? |
|---|---:|---:|---|---|
| `PorePressureFeedback` | `0/1` | `0` | Enables pore-pressure acceleration feedback to `Acec`. | Keep |
| `PorePressureFeedbackMode` | `0/1` | `0` | `0`: use total `PorePress`; `1`: use excess `PorePress - p_hydro`. | Keep |
| `PorePressureFeedbackOperator` | `0/1/2/3` | `0` | `0`: legacy symmetric stress-style operator; `1`: difference-gradient operator; `2`: CPU-only LSQ pressure-gradient feedback; `3`: CPU-only paper-style stress-pair pressure momentum prototype. | Keep / Experimental |
| `PorePressureFeedbackLSQRadiusFactor` | float, `>0` | `1` | Support-radius factor for operator `2`, capped by the kernel support. | Experimental |
| `PorePressureFeedbackLSQConditionLimit` | float, `>=0` | `1e12` | LSQ condition proxy limit for operator `2`; `<=0` disables the condition check. | Experimental |
| `PorePressureFeedbackLSQFallback` | `0/1` | `0` | Operator `2` fallback: `0` uses operator `1` difference-gradient, `1` applies zero feedback for ill-conditioned particles. | Experimental |
| `PorePressureFeedbackStartTime` | seconds | `0` | Optional CPU feedback gate. Feedback acceleration is zero before this time when `PorePressureFeedback=1`. | Experimental |
| `PorePressureFeedbackRampEndTime` | seconds | `0` | Optional CPU feedback ramp end time. If greater than `StartTime`, feedback factor ramps linearly from zero to `Scale`. | Experimental |
| `PorePressureFeedbackScale` | `0..1` | `1` | Maximum pore-pressure feedback acceleration scale for staged equilibration diagnostics. | Experimental |
| `SavePorePressureFeedbackDiagnostics` | `0/1` | `0` | Prints CPU feedback acceleration diagnostics: factor, raw/used acceleration, limiter activation, and class-wise maxima. | Experimental |
| `PorePressureFeedbackDiagInterval` | integer, `>0` | `1` | Step interval for feedback diagnostics when enabled. | Experimental |
| `PorePressureFeedbackRelaxation` | `0..1` | `0` | Optional first-order feedback acceleration relaxation. `0` disables it; `(0,1)` uses `a_old + alpha(a_raw-a_old)`. | Experimental |
| `PorePressureFeedbackLimiterMode` | `0..3` | `0` | `0`: none, `1`: absolute cap, `2`: ratio cap, `3`: absolute plus ratio cap. | Experimental |
| `PorePressureFeedbackMaxAccel` | float, `>=0` | `0` | Absolute feedback acceleration cap in `m/s2`; disabled when `<=0`. | Experimental |
| `PorePressureFeedbackMaxAccelRatio` | float, `>=0` | `0` | Cap relative to the current non-feedback/confining acceleration reference; disabled when `<=0`. | Experimental |
| `PorePressureFeedbackUseClassFilter` | `0/1` | `0` | CPU-only triaxial diagnostic filter for applying feedback by cylinder class. Requires `ConfiningStressGeometry=1`. | Experimental |
| `PorePressureFeedbackExcludeCaps` | `0/1` | `0` | With class filter, skip top/bottom cap classes. | Experimental |
| `PorePressureFeedbackExcludeEdges` | `0/1` | `0` | With class filter, skip cylinder edge-ring class. | Experimental |
| `PorePressureFeedbackExcludeConfinementTargets` | `0/1` | `0` | With class filter and lateral confinement selector, skip selected lateral confinement targets. | Experimental |
| `PorePressureFeedbackInteriorOnly` | `0/1` | `0` | With class filter, apply feedback only to cylinder interior class. | Experimental |

Recommended for Terzaghi/self-weight tests:

```xml
<parameter key="PorePressureFeedback" value="1" />
<parameter key="PorePressureFeedbackMode" value="1" />
<parameter key="PorePressureFeedbackOperator" value="1" />
```

For T4e-style triaxial staged confinement diagnostics, feedback acceleration
can be delayed or ramped without changing the PR pore-pressure update:

```xml
<parameter key="PorePressureFeedback" value="1" />
<parameter key="PorePressureFeedbackStartTime" value="0.003" />
<parameter key="PorePressureFeedbackRampEndTime" value="0.0045" />
<parameter key="PorePressureFeedbackScale" value="1" />
```

The defaults preserve old behavior. Non-default feedback gating is currently
CPU-only; GPU runs hard-error when a non-default start/ramp/scale is requested.
T4e showed that these controls are diagnostic staging tools only: delaying and
ramping full feedback did not stabilize the reduced selected-confinement
triaxial sample, while `PorePressureFeedbackScale=0.25` reduced the artifact
but still produced pressure reversal.

For T4f-style triaxial feedback stabilization diagnostics, the acceleration
itself can be relaxed or capped without modifying the PR pressure update:

```xml
<parameter key="SavePorePressureFeedbackDiagnostics" value="1" />
<parameter key="PorePressureFeedbackRelaxation" value="0.2" />
<parameter key="PorePressureFeedbackLimiterMode" value="3" />
<parameter key="PorePressureFeedbackMaxAccel" value="50" />
<parameter key="PorePressureFeedbackMaxAccelRatio" value="25" />
```

These controls are experimental CPU-only safety guards. T4f showed that
relaxation plus cap can remove selected-confinement exclusions and DtMin bursts
with full feedback scale `1`, but it does not yet provide validation-quality
triaxial dynamics: local negative pressure remains and axial loading still
reintroduces center-core reversal.

For T4g-style formulation diagnostics, feedback can also be restricted by
cylinder class without changing the PR pressure update:

```xml
<parameter key="PorePressureFeedbackUseClassFilter" value="1" />
<parameter key="PorePressureFeedbackInteriorOnly" value="1" />
```

This is a CPU-only diagnostic path. T4g showed that class filtering removes the
unfiltered full-feedback exclusions and DtMin burst, but it still does not pass
the selected-confinement gate: pressure reversal remains and max
`PorePressRate` is still about `4.79e10 Pa/s` for the best interior-only
operator-1 case. The filter is not a validation setting.

Rationale:

- `Mode=1` avoids applying mechanical feedback from the hydrostatic baseline.
- `Operator=1` avoids the large missing-neighbor boundary force observed with material-only symmetric feedback under constant excess pressure.
- T4g manufactured tests confirm that operator 1 is constant-pressure
  consistent on the retained triaxial cloud, while operator 0 generates a
  nonzero surface response under uniform pressure.

Current operators:

```text
Operator 0: symmetric stress-style diagnostic
  a_pw = -sum_j m_j * (p_i+p_j)/(rho_i*rho_j) * gradW_ij

Operator 1: difference-gradient feedback
  gradp_i = sum_j (m_j/rho_j) * (p_j-p_i) * gradW_ij
  a_pw = -gradp_i/rho_i

Operator 2: LSQ pressure-gradient feedback
  p_j - p_i ~= gradp_i dot (x_j-x_i)
  A_i gradp_i = b_i
  a_pw = -gradp_i/rho_i

Operator 3: paper-style stress-pair pressure momentum prototype
  a_pw = sum_j m_j * (p_i+p_j)/(rho_i*rho_j) * gradW_ij
```

`Sigmac` remains the skeleton effective stress. Pore pressure is not subtracted from `Sigmac`; it is fed back as an acceleration term.

T4h adds operator `2` only as a CPU diagnostic route. It passes the static
manufactured uniform and linear-pressure checks, but it does not pass the
selected-confinement dynamic gate: unstabilized LSQ reaches about
`5.04e10 Pa/s` max `PorePressRate`, and stabilized LSQ still reverses. Do not
use operator `2` as a triaxial validation setting yet. GPU execution
hard-errors when operator `2` is requested.

T4j adds operator `3` as a CPU diagnostic route that is closer to the original
u-pw notes in algebraic stress-pair form. It is not validation-ready: uniform
pressure on the free-surface triaxial cloud produces the expected missing-
support surface response, and the selected-confinement dynamic gate is worse
than operator `1` (`excluded=407` unfiltered, `excluded=55` interior-only).
GPU execution hard-errors when operator `3` is requested. Do not use operator
`3` for new validation cases without a new boundary-completion or initial-
confinement plan.

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

## 10. Triaxial Platen Diagnostics Status

T4q and T4r use existing fixed/moving `mkbound` XML mechanics for explicit
triaxial platens:

- top platen: prescribed motion through `<motion><objreal ref="1">`;
- bottom platen: fixed `mkbound`;
- specimen: separate `mkfluid`;
- lateral confinement: optional `FlexibleConfiningStress`;
- `CapConfiningStress` is diagnostic-only and not recommended as production
  platen support.

No new XML parameter was added in T4r.

Current limitation:

```text
ordinary fixed/moving mkbound platens do not output true top/bottom reaction
```

T4r postprocessing therefore uses:

```text
sigma_a_proxy = -mean(Sigma_zz) over specimen-only particles
Fz_proxy = sigma_a_proxy * pi * R^2
```

This proxy is acceptable for elastic feedback-off workflow diagnostics. It is
not a strict platen reaction and should not be cited as validation reaction
force. A future CPU-only opt-in diagnostic should accumulate true platen
reaction by `mkbound` before strict triaxial stress-path validation.

## 11. Platen Reaction Diagnostics

T4t adds an opt-in CPU diagnostic for explicit triaxial platens:

```xml
<parameter key="SavePlatenReactionDiagnostics" value="0" />
<parameter key="PlatenTopMkBound" value="1" />
<parameter key="PlatenBottomMkBound" value="2" />
<parameter key="PlatenReactionMode" value="0" />
<parameter key="PlatenReactionArea" value="0" />
<parameter key="PlatenReactionInterval" value="500" />
```

Defaults preserve previous behavior.

- `SavePlatenReactionDiagnostics=1`: enable CPU logging of top/bottom platen
  reaction diagnostics.
- `PlatenTopMkBound`, `PlatenBottomMkBound`: user mkbound values for the
  top and bottom platens. They must be non-negative and distinct.
- `PlatenReactionMode=0`: pairwise fluid-bound interaction accumulator. The
  solver sums the opposite of the specimen-side SPH pair contribution for
  interactions with the selected platen groups.
- `PlatenReactionArea`: reference area used to convert axial force to axial
  stress. Use `pi*R^2` for the current reduced cylinder. A value of `0`
  disables meaningful stress conversion.
- `PlatenReactionInterval`: log interval in solver steps.

The diagnostic is CPU-only and hard-errors on GPU when enabled. It does not
change the physics. Mode `0` is closer to a true platen reaction than
`Fz_proxy=-mean(Sigma_zz)*pi*R^2`, but it does not include prescribed-motion
constraint forces. It should be cited as a pairwise specimen-platen
interaction reaction diagnostic.

## 12. Modified Cam Clay CPU Model

M3c enables `SoilConstitutiveModel=3` as a CPU-only Modified Cam Clay stress
update branch. The parser/state/output skeleton was added in M3b; M3c connects
the CPU return mapping.

```xml
<SoilConstitutiveModel value="3" />
<MccLambda value="0.2" />
<MccKappa value="0.04" />
<MccM value="1.2" />
<MccInitialVoidRatio value="0.8" />
<MccInitialPreconsolidationPressure value="200" />
<MccTensionCutoff value="1e-6" />
<MccReturnTolerance value="1e-8" />
<MccReturnMaxIter value="45" />
<MccSubstepping value="0" />
<MccMaxSubsteps value="1" />
<MccSubstepMode value="0" />
<MccSubstepStrainThreshold value="0" />
<MccSubstepYieldDistanceThreshold value="0" />
<MccMinSubsteps value="1" />
<MccAdmissibilityGuard value="0" />
<MccFailureFallback value="0" />
<SaveMccState value="1" />
<MccStressUpdateEnabled value="1" />
```

Alternatives:

- use `MccInitialSpecificVolume` instead of `MccInitialVoidRatio`;
- use `MccOCR` instead of `MccInitialPreconsolidationPressure`;
- use `MccReferencePressure` for OCR initialization when initial `p'` is not
  positive.

Rules:

- `MccInitialVoidRatio` and `MccInitialSpecificVolume` are mutually exclusive;
- `MccInitialPreconsolidationPressure` and `MccOCR` are mutually exclusive;
- missing required MCC parameters hard-error;
- `MccLambda > MccKappa > 0`, `MccM > 0`, and positive `pc0/OCR` are required;
- `SoilConstitutiveModel=3` hard-errors on GPU;
- `MccStressUpdateEnabled=1` is required for model `3` in M3c.

M3d3 adds opt-in local return robustness controls. Defaults preserve M3c/M3d
single-step behavior.

- `MccSubstepping=0/1`: enable local constitutive substepping.
- `MccMaxSubsteps`: maximum local substeps; default `1`.
- `MccSubstepMode=0`: fixed substep count using `MccMaxSubsteps`.
- `MccSubstepMode=1`: adaptive retry on failed return, up to
  `MccMaxSubsteps`.
- `MccSubstepMode=2`: adaptive count from an approximate trial-increment
  threshold and, in M3f, an optional normalized trial yield-distance
  threshold.
- `MccMinSubsteps`: minimum local MCC substeps used by mode `2`; default `1`.
- `MccSubstepStrainThreshold`: optional threshold for mode `2`.
- `MccSubstepYieldDistanceThreshold`: optional normalized trial yield-distance
  threshold for mode `2`; `0` disables this trigger.
- `MccAdmissibilityGuard=0/1`: check finite stress/state, positive admissible
  `p'`, positive `pc`, admissible void ratio, and non-negative plastic
  multiplier.
- `MccFailureFallback=0`: fail status only.
- `MccFailureFallback=1`: retry only.
- `MccFailureFallback=2`: keep last converged local substep and mark explicit
  partial fallback.

`SaveMccState=1` outputs:

- `MccPc`;
- `MccVoidRatio`;
- `MccPlasticVolStrain`;
- `MccEqPlasticStrain`;
- `MccYieldFlag`;
- `MccPlasticMultiplier`;
- `MccReturnStatus`;
- `MccReturnIterations`;
- `MccYieldResidual`;
- `MccSubstepCount`;
- `MccSubstepFailureCount`;
- `MccAdmissibilityFailureCount`;
- `MccFallbackUsed`.
- `MccSubstepTriggerReason`.

`MccSubstepTriggerReason` values:

- `0`: single-step/no proactive trigger;
- `1`: fixed substepping;
- `2`: strain-increment threshold;
- `3`: trial yield-distance threshold;
- `4`: minimum substep count;
- `5`: retry after failed return.

Current stress convention remains:

```text
Sigmac compression is negative.
MCC internals are compression-positive.
p' = -trace(Sigmac)/3.
Sigmac_new = -stress_cp_new.
```

M3c status:

- CPU Release/Debug builds pass;
- GPU Release build passes, but model `3` remains GPU-hard-error;
- feedback-off explicit-platen smokes pass for high-pc elastic-like MCC and
  mild-yield MCC;
- full pore-pressure feedback and GPU MCC remain deferred.

M3f status:

- improved adaptive substepping diagnostics are implemented;
- default behavior remains unchanged;
- M3f CPU cases remain solver-stable (`code=0`, `excluded=0`, `DtMin=0`);
- no clean mild-MCC candidate was obtained because all routes retain transient
  negative return-status episodes;
- full pore-pressure feedback and GPU MCC remain deferred.

Return-status codes in `MccReturnStatus`:

- `0`: elastic;
- `1`: plastic converged;
- `2`: plastic converged using substepping;
- `-1`: tension cutoff;
- `-2`: singular Newton Jacobian;
- `-3`: line-search failure;
- `-4`: maximum iteration failure;
- `-5`: explicit partial fallback using last converged substep;
- `-6`: admissibility guard failure.
