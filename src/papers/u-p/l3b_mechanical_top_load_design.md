# L3b Mechanical Top-Load Design

## Candidate Routes

### Route 1: Current AccInput Body-Force Route

Status: already available and CPU/GPU stable.

This is not paper-faithful. It accelerates a material layer and creates strong
dynamic pore-pressure peaks. L2 should remain a reduced smoke route only.

### Route 2: Explicit Loading Plate With Prescribed Motion

Status: XML feasible for motion-controlled smokes.

This route is useful for deformation-controlled diagnostics, but prescribed
velocity/displacement is not the Terzaghi surface surcharge `q0`. It needs a
reaction/force matching layer before it can act as a stress-controlled
validation route.

### Route 3: Direct Top Material Surface Traction

Status: implemented as the L3b minimum CPU prototype.

The new `MechanicalTopLoad` path computes:

```text
Fz = q0 * A * ramp(t)
az = Fz / sum(m_target)
```

and applies `az` only to the selected top material surface particles. The target
surface is auto-detected unless `MechanicalTopLoadSurfaceZ` is provided.

This is closer to a surface-load formulation than `AccInput` because the force
scale is explicit and the target surface is selected geometrically, not by a
separate accelerated material layer. It is still an acceleration application to
material particles, not a true force-controlled platen or actuator reaction.

### Route 4: Consistent Initial Stress Plus Initial Excess Pressure

Status: recommended for L3c if strict analytical matching is prioritized.

This route would initialize effective stress and pore pressure consistently so
that total stress includes `q0` while the analytical initial excess pressure is
already present. It is more aligned with the Terzaghi initial-value problem but
bypasses mechanical load generation.

### Route 5: Ramped Surface Load Plus Damping

Status: not recommended as the next primary step.

Damping can reduce waves only after the loading route is physically appropriate.
L2/L3b show that the load route itself is the blocker, so a broad
damping/viscosity sweep should remain deferred.

## L3b Interface

New opt-in parameters:

- `MechanicalTopLoad=0/1`;
- `MechanicalTopLoadMode=1`;
- `MechanicalTopLoadQ0`;
- `MechanicalTopLoadRampStart`;
- `MechanicalTopLoadRampEnd`;
- `MechanicalTopLoadTargetMk`;
- `MechanicalTopLoadSurfaceZ`;
- `MechanicalTopLoadThickness`;
- `MechanicalTopLoadArea`;
- `SaveMechanicalTopLoadDiagnostics`;
- `MechanicalTopLoadDiagInterval`.

Defaults preserve previous behavior. GPU use hard-errors when enabled.

## Recommended Next Route

L3b should be treated as a source-backed mechanical-loading prototype. If it
still behaves dynamically, the recommended next strict route is L3c: consistent
initial effective stress plus initial excess pore pressure, or a future true
force-controlled platen. Damping sweeps should remain secondary.

