# Triaxial Loading and Confinement Plan

Date: 2026-05-11

Milestone: LOAD-2 from `full_cpu_implementation_backlog.md`

This document designs the missing loading and confinement workflow for the
undrained triaxial paper case. It does not implement source changes.

## Current Reduced Smoke

`examples/u-pw/04_Undrained_Triaxial` currently has a reduced CPU smoke:

- small 2D column;
- top `mkfluid=1` material layer loaded by native `AccInput`;
- current Drucker-Prager soil path;
- no true confining stress boundary;
- approximate postprocessing only.

This verifies field plumbing but is not strict triaxial reproduction.

## Strict Triaxial Requirements

A strict triaxial smoke needs:

- specimen geometry matching the paper or a documented coarse equivalent;
- initial isotropic confinement or equivalent stress state;
- undrained hydraulic boundaries;
- controlled axial strain rate or controlled axial stress;
- lateral confinement maintained during axial loading;
- pore pressure output;
- stress path output: `p'`, `q`, axial strain, possibly volumetric strain.

Exact paper values for specimen size, confinement, loading rate, and material
model still need PDF/SI extraction or manual entry.

## Loading Options

### Option A: Native AccInput on Top Material Layer

Status: already used for reduced smoke.

Pros:

- no source changes;
- easy to apply to `mkfluid=1`;
- useful for tiny health checks.

Cons:

- acceleration is not strain-control;
- can inject local dynamics;
- does not impose a rigid platen or uniform displacement;
- weak match to triaxial apparatus.

Use only for reduced smoke and debugging.

### Option B: Moving Boundary / Platen Motion

Pros:

- closer to axial strain control;
- native DualSPHysics motion tools may already support it;
- avoids reintroducing source-side loading hacks.

Cons:

- requires a top boundary plate geometry;
- must ensure pore-pressure boundaries remain undrained or drained as intended;
- contact/boundary interactions may influence stress field.

Preferred first strict-smoke route if existing motion XML can drive a top plate.

### Option C: Prescribed Velocity on Top Material Layer

Pros:

- simpler than a full platen;
- can approximate axial strain rate.

Cons:

- requires particle group velocity control or motion mechanism;
- may conflict with stress update if applied to material particles directly.

Use only if native motion on boundary plate is too difficult.

### Option D: Stress/Traction Boundary

Pros:

- physically closest for stress-controlled triaxial paths.

Cons:

- not available in the current u-pw PR prototype;
- likely requires new source code and careful boundary force implementation.

Defer unless the paper case specifically demands stress control.

## Confinement Options

### Option 1: Fixed Lateral Boundary

Pros:

- available now;
- stable for reduced smoke.

Cons:

- not a prescribed confining stress;
- produces constrained-strain behavior, not true triaxial response.

Use only for reduced smoke.

### Option 2: Native Moving/Pressure Boundary Approximation

Pros:

- may approximate constant lateral stress with moving walls or external
  forcing.

Cons:

- requires design against existing DualSPHysics mechanisms;
- not yet validated for effective-stress soil.

Candidate for strict smoke only after a small dry/mechanical check.

### Option 3: Source-Level Traction / Confining Pressure

Pros:

- direct control of lateral stress.

Cons:

- new production mechanics boundary code;
- interacts with effective stress and pore pressure;
- not a small pre-GPU task.

Defer unless native mechanisms are insufficient and user approves scope.

## Recommended Strict-Smoke Workflow

1. Reconstruct paper parameters from PDF/SI notes:
   - geometry;
   - confinement;
   - axial strain/stress path;
   - material model.
2. Create a small boundary-platen XML using native motion if possible.
3. Keep hydraulic boundaries undrained:
   - no top drained during undrained loading;
   - bottom/lateral no-flux.
4. Run a tiny CPU smoke:
   - very small axial strain;
   - no long parameter tuning;
   - check no NaN/excluded.
5. Postprocess:
   - axial strain from platen/specimen height;
   - `p'` and `q` from `Sigma_kk`/`Sigma_ij`;
   - pore-pressure sign and magnitude trend.

## Minimum Smoke Standard

- GenCase code=0;
- solver code=0;
- excluded=0;
- no NaN/Inf;
- top loading produces compression of the expected sign;
- pore pressure sign is plausible for undrained compression;
- `p'`/`q` script runs, even if strict validation is deferred.

## Source Change Policy

Do not add source-level triaxial loading or confinement yet. First exhaust
native XML mechanisms: moving boundary/platen, motion, AccInput, or existing
external force examples. If native tools cannot achieve a stable strict smoke,
write a separate traction/confinement source design before implementation.

## GPU Implications

The loading mechanism itself should preferably remain XML/native and not become
a GPU PR core dependency. Stress-path output and material model choices may
affect later GPU validation, but they should not alter passive `PorePressg`
array design.

