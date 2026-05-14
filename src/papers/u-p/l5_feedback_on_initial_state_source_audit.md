# L5 Feedback-On Initial-State Source Audit

## Current Initialization Support

The 1D consolidation route currently supports the pressure initialization used
by L3c/L4:

```xml
<parameter key="PorePressureInit" value="3" />
<parameter key="PorePressureExcessAmp" value="10000" />
<parameter key="PorePressureAnalyticalProfile" value="3" />
```

This initializes a uniform excess pore-pressure field before applying the top
drained condition. As seen in L3c, the top drained layer is zeroed at
initialization while the interior and bottom remain at the target amplitude.

## Initial Stress Support

The source has `InitialStressMode` support, including an isotropic effective
stress initializer. For the current 1D Terzaghi route:

- `InitialStressMode=0` is used in L3c/L4;
- `InitialStressMode=1` is CPU-only isotropic effective stress;
- there is no confirmed vertical-only effective stress initializer;
- there is no total-stress-equivalent surcharge initializer;
- there is no z-range or top-load-consistent stress initializer.

Therefore L5 should not pretend to be a consistent stress-initialized
Terzaghi reproduction.

## Boundary Support

The route retains the hydraulic boundary controls used in L3c/L4:

```xml
<parameter key="PorePressureTopDrained" value="1" />
<parameter key="PorePressureBottomNoFlux" value="1" />
<parameter key="PorePressureBoundaryOperator" value="0" />
```

The top drained clamp and bottom no-flux correction are supported on CPU and
GPU for this route.

## Feedback Diagnostics

Existing PartCsv output includes the fields needed for a first feedback-on
gate when pore pressure output is enabled:

- `PorePress`;
- `ExcessPorePress`;
- `PorePressRate`;
- `DivVel`;
- `PorePressureAccelDiff.x/y/z`;
- particle position and velocity.

These fields are sufficient to compute:

- peak excess pressure;
- top drained residual;
- bottom no-flux proxy;
- velocity and divergence growth;
- feedback acceleration magnitude;
- qualitative scaling from `1 kPa` to `10 kPa`.

No source patch is required for this diagnostic gate.

## CPU/GPU Support

CPU supports all feedback operators. GPU supports only feedback operator `1`.
The L5 cases therefore use:

```xml
PorePressureFeedbackMode=1
PorePressureFeedbackOperator=1
```

GPU should only be run after the CPU target-amplitude route is stable.

## Physically Interpretable Gate Without Source Patch

A no-source L5 route is feasible if it is explicitly labeled as:

- initial excess pressure plus feedback-on diagnostic;
- no AccInput;
- no MechanicalTopLoad;
- no initial vertical stress;
- no strict surcharge generation.

If L5 is unstable or dynamically over-amplified, the next source task should
not be damping. It should be an L5b consistent stress initializer or a later
mechanical loading design.

## Minimum Future Source Patch If Needed

If feedback-on cannot be interpreted with `InitialStressMode=0`, the minimum
future source feature should be a CPU-first initializer that can set:

- vertical effective stress;
- total-stress-equivalent surcharge state;
- pore pressure consistently with the selected top drained boundary;
- output diagnostics for initial stress and pressure balance.
