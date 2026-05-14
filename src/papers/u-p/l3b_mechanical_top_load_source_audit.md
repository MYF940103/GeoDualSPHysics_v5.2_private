# L3b Mechanical Top-Load Source Audit

## Objective

L3b audits routes for applying the `q0=-10 kPa` one-dimensional consolidation
surface surcharge without using the reduced L2 `AccInput` body-acceleration
path. The target is a paper-faithful mechanical load route for the Terzaghi
case, while leaving the PR pore-pressure governing equation unchanged.

## Current Routes

### AccInput Body Acceleration

`AccInput` is applied in `JSphCpu::PreInteractionVars_Forces()` before the
interaction force pass:

```text
source/JSphCpu.cpp
  if(AccInput) AccInput->RunCpu(..., Acec)
```

`JDsAccInput::RunCpu()` selects particles by `mkfluid` and adds a prescribed
acceleration to `Ace`. This is numerically useful for smoke tests, but it is
not a surface traction. L2 showed that mapping `q0` to a top material-layer
acceleration generates strong velocity/DivVel waves and a non-Terzaghi excess
pore-pressure peak.

### Explicit Platen / Motion

The code already supports `mkbound` motion in XML, and the T4q-T5 workflow used
moving/fixed platens successfully. This route is displacement- or
velocity-controlled, not force-controlled. It can create a mechanical smoke,
but it is not a constant surcharge `q0`.

### Platen Reaction Diagnostics

`SavePlatenReactionDiagnostics` accumulates CPU pairwise fluid-bound interaction
forces for mkbound platens. This is useful for checking a platen workflow, but
it does not by itself apply a force-controlled plate.

### Surface Traction / Force Boundary

No general force-controlled top material surface or loading-plate traction
route was present before L3b. There were no safe production `TopLoad*`
interfaces suitable for direct reuse; reintroducing old top-load patches
blindly would risk repeating the same acceleration-driven behavior without
clear diagnostics.

### InitialStressMode / Pore-Pressure Initialization

`InitialStressMode=1` initializes isotropic effective stress, and L3a
`PorePressureInit=3` initializes the analytical uniform excess pore-pressure
field. These are good initialization gates, but they do not reproduce mechanical
load generation.

## Minimum Safe Patch Location

The smallest CPU-only insertion point is in the CPU force stage after existing
hydromechanical feedback/damping contributions and before `AceMax` is computed:

```text
source/JSphCpuSingle.cpp
  ApplyMechanicalTopLoad(...)
```

This keeps the route opt-in, does not alter PR, and allows the applied
acceleration to be included in timestep acceleration diagnostics. The
implementation lives in `JSphCpu::ApplyMechanicalTopLoad()` and is controlled
by new parser parameters in `JSph.cpp` / `JSph.h`.

## GPU Status

L3b is CPU-first. If `MechanicalTopLoad=1` is requested with `Cpu=false`, the
parser raises a hard error. GPU compilation still succeeds; GPU simulation for
this route is deferred.

