# L3e 1D Consolidation Loading Route Classification

Date: 2026-05-14

## Category A: Validation-Ready Paper-Compatible Gate

### L3a Initial-Pressure Diffusion Gate

L3a removes mechanical loading and initializes the Terzaghi analytical excess
pressure directly:

```text
PorePressureInit=3
PorePressureExcessAmp=10000 Pa
PorePressureFeedback=0
AccInput disabled
MechanicalTopLoad disabled
```

It validates the PR diffusion update and hydraulic boundaries against the
Terzaghi initial-value solution. It does not reproduce mechanical load
generation.

### L3c Consistent Initial-State Gate

L3c formalizes the same physical initial condition:

```text
p_w0 = |q0| = 10 kPa
InitialStressMode = 0
Initial effective-stress increment = 0
```

This is the cleanest current figure route for the paper-aligned 1D
consolidation chain. CPU and GPU both complete with `code=0`, `excluded=0`,
and `DtMin=0`, with peak excess pressure exactly at the `10 kPa` scale.

Scope caveat: Category A validates PR diffusion, top drainage, bottom no-flux,
and the Terzaghi initial-state decay trend. It does not validate the mechanical
surface-load generation stage or full pore-pressure feedback.

## Category B: Stable Reduced Smoke

### L1 External-Load Baseline

L1 is an early external-load route smoke. It is stable and useful as a
regression anchor, but it is not paper-aligned and does not provide the strict
Terzaghi analytical comparison.

### L2 Paper-Aligned AccInput Setup

L2 aligns the geometry and material constants with the paper setup, but still
uses native `AccInput` on the top material layer. This is a body acceleration,
not a surface surcharge. It is CPU/GPU stable, but it generates a dynamic
pressure peak near `6.25e5 Pa`, far above the intended `10 kPa` scale.

### L3b Mechanical Top-Load Force-On-Material Route

L3b removes `AccInput` and applies `Fz=q0*A` directly to the top material
surface with the CPU-only `MechanicalTopLoad` prototype. It proves that the
problem is broader than the `AccInput` file path: direct material-surface force
still behaves dynamically and generates a pressure peak near `5.90e5 Pa`.

Category B cases are useful smoke/regression cases, but they should not be used
as strict Terzaghi validation figures.

## Category C: Deferred Strict Route

The strict mechanical reproduction remains deferred. Candidate future routes:

- quasi-static force-controlled loading plate;
- true surface traction boundary;
- consistent total-stress plus pore-pressure initializer;
- staged coupled loading after feedback mechanics are ready.

This is future L3d work.

## Category D: Not Recommended Now

A damping or viscosity sweep is not recommended before the loading route is
fixed. L2 and L3b show that the dominant error is load generation, not merely a
damping parameter. A sweep could hide the route error without making the setup
paper-faithful.
