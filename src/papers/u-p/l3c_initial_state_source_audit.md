# L3c Initial State Source Audit

Date: 2026-05-14

## Pore Pressure Initialization

`PorePressureInit=3` is implemented in the CPU and GPU initialization paths. It
sets a hydrostatic pore-pressure reference plus an analytical excess pressure
profile. With `PorePressureAnalyticalProfile=3`, the excess component is
uniform before boundary corrections.

For L3c:

```text
PorePressureInit=3
PorePressureExcessAmp=10000
PorePressureAnalyticalProfile=3
HydraulicElevationSource=1
PorePressureTopDrained=1
PorePressureBottomNoFlux=1
```

The top drained layer is applied during initialization when
`PorePressureTopDrainedStartTime=0`, so the top drainage particles are clamped
to hydrostatic pressure immediately.

## Initial Stress Capability

The current effective-stress initializer is:

```text
InitialStressMode=1
InitialEffectiveStressIso=<positive compression magnitude>
InitialEffectiveStressTargetMk=<mk or -1>
```

It writes a uniform isotropic compressive effective stress into `Sigmac` using
the code convention that compressive `Sigmac` diagonal values are negative.
It does not change `PorePress`.

Limitations for L3c:

- it is CPU-only;
- it is isotropic, not vertical-only;
- it does not define a total-stress state;
- it cannot set stress by `z` range;
- it cannot represent a force-controlled top surcharge by itself.

Because the Terzaghi analytical initial condition carries the instantaneous
surcharge as excess pore pressure, L3c deliberately keeps
`InitialStressMode=0`.

## Simultaneous Pore Pressure And Stress

The code can simultaneously initialize pore pressure and `Sigmac` on CPU, but
the available stress mode is not the desired paper-faithful vertical
total-stress equivalent. On GPU, `InitialStressMode=1` hard-errors, while
`PorePressureInit=3` is supported.

Thus the L3c route that remains CPU/GPU compatible is:

```text
PorePressureInit=3
InitialStressMode=0
MechanicalTopLoad=0
AccInput disabled
```

## Hydraulic Elevation

`HydraulicElevationSource=1` is retained from L3a. It uses the hydraulic
gravity convention for hydrostatic pressure and the elevation source term in
the PR update. This matches the L3a analytical diffusion gate.

## Dynamic Loading Avoidance

The following routes are intentionally not used in L3c:

- native `AccInput` top material-layer body acceleration;
- `MechanicalTopLoad=1` direct top material surface forcing;
- damping or viscosity sweeps.

L2 and L3b showed that load-generation impulses produce excess pore pressure
peaks near `5.9e5` to `6.25e5 Pa`, far above the `10 kPa` analytical scale.

## Source Patch Need

No source patch is required for the L3c initial-state gate.

A future strict mechanical route would need a separate source design for either:

- vertical/total stress plus pore-pressure initialization;
- a quasi-static force-controlled loading plate;
- or a staged coupled loading route with feedback enabled and controlled.
