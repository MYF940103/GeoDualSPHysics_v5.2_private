# L2 External-Load 1D Consolidation Setup Audit

Date: 2026-05-14

## Objective

Audit the difference between the L1 external-load smoke and a paper-aligned
one-dimensional Terzaghi consolidation setup before running L2.

L2 remains XML/workflow/postprocessing only. No source-side `TopLoad*` route is
reintroduced.

## L1 Setup

L1 lives in:

```text
examples/u-pw/01_1D_Consolidation/experiments/ExternalLoad_L1_Baseline/
```

L1 key settings:

| Item | L1 value |
|---|---:|
| Geometry | `H=1.0 m`, `width=0.1 m`, `Dp=0.01 m` |
| Bulk soil | `mkfluid=0` |
| Top loading layer | `mkfluid=1` |
| Skeleton model | not explicit in XML; legacy default path |
| `E`, `nu` | `2e6 Pa`, `0.3` |
| `n`, `k`, `Kw` | `0.3`, `1e-3 m/s`, `2e8 Pa` |
| External acceleration | `a_z=-0.047619 m/s2` |
| Load ramp end / drain start | `0.05 s` |
| `TimeMax` | `0.2 s` |
| `PorePressureBoundaryOperator` | `0` |
| `PorePressureFeedback` | `1` |
| `HydromechDampingXi` | `0.05` |
| Executed result | GPU Release only, `code=0`, `excluded=0` |

L1 was intentionally a smoke test. Its acceleration was a small stable forcing
history, not a calibrated `q0=-10 kPa` surcharge.

## Paper Setup Target

The target u-pw 1D consolidation setup is:

| Item | Target |
|---|---:|
| Height | `H=1.0 m` |
| Width | `0.1 m` |
| Particle spacing | `Delta=0.01 m` |
| Young modulus | `E=2e6 Pa` |
| Poisson ratio | `nu=0.3` |
| Water bulk modulus | `Kw=2e8 Pa` |
| Porosity | `n=0.3` |
| Hydraulic conductivity | `k=1e-3 m/s` |
| Top drainage | `p_w=0` excess-pressure drainage |
| Bottom/lateral drainage | undrained/no-flux |
| Top load | `q0=-10 kPa` |
| Reference | Terzaghi single-drainage analytical solution |

## Differences and L2 Changes

### Geometry and particle spacing

L1 already uses the nominal target geometry and `Dp=0.01 m`. L2 keeps this
unchanged. The postprocessing uses the material particle-center height
(`H_effective ~= 0.9901 m`) when comparing to the analytical curve.

### Skeleton and hydraulic parameters

L2 explicitly sets:

```xml
<SoilConstitutiveModel value="0" />
<ModulusE value="2e6" />
<PRvs value="0.3" />
<Porosity0 value="0.3" />
<HydraulicConductivity value="1e-3" />
<WaterBulkModulus value="2e8" />
<WaterDensity value="1000" />
```

The hydraulic material constants are placed under `<special><soils>` instead
of relying on deprecated `<parameters>` fallbacks.

### Top drainage

The current implementation uses the existing layer correction:

```xml
PorePressureTopDrained=1
PorePressureDrainThickness=0
PorePressureTopDrainedStartTime=0.005
```

With thickness `0`, the code uses the kernel support thickness. L2 activates
top drainage at the end of the external-load ramp.

### Bottom and lateral undrained conditions

Bottom no-flux uses the existing layer correction:

```xml
PorePressureBottomNoFlux=1
PorePressureBottomNoFluxThickness=0
```

The lateral direction remains the established 1D periodic column route rather
than an explicit nonperiodic lateral no-flux wall. This is acceptable for the
reduced 1D comparison but is still not a full boundary-theory reproduction.

### External load

L2 keeps the L1 route, but maps the target surcharge to the top material layer:

```text
a_z = q0 / (rho0 * Dp)
    = -10000 / (2100 * 0.01)
    = -476.190476 m/s2
```

This is the closest XML-only AccInput mapping for a one-particle-thick loading
layer. It remains a reduced route because it is a body acceleration on material
particles, not a true traction or loading plate.

### Analytical reconstruction

L2 adds a Terzaghi single-drainage analytical comparison:

```text
u(y,t) / u0 = sum_{n=0}^\infty 2/M_n sin(M_n y/H) exp(-M_n^2 c_v t/H^2)
M_n = (2n+1) pi/2
```

where `y` is depth from the drained top. The script reports both:

- target `u0 = 10 kPa`;
- fitted amplitude from the first post-drainage bottom response.

The fitted-amplitude curve is diagnostic only; the target curve is the paper
reference.

## CPU/GPU Support

The selected L2 parameter set uses GPU-supported routes:

- `SoilConstitutiveModel=0`;
- `HydraulicElevationSource=1`;
- `PorePressureBoundaryOperator=0`;
- `PorePressureFeedbackOperator=1`;
- native `AccInput`.

Therefore both CPU Release and GPU Release are valid short validation targets.

## Expected Limitation

The main risk is not parsing or GPU support. The risk is physical: a high
`q0=-10 kPa` represented as acceleration on a material top layer can excite a
dynamic coupled response rather than the quasi-static instantaneous surcharge
assumed by Terzaghi theory.
