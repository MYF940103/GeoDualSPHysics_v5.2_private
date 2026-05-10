# Sensitive Clay / Strain-Softening Model Plan

Date: 2026-05-11

Milestone: MAT-2 from `full_cpu_implementation_backlog.md`

This plan captures the material-model gap for the retrogressive slope and
Sainte-Monique cases. It is a design document only.

## Why This Matters

The retrogressive slope and Sainte-Monique targets are not only pore-pressure
benchmarks. They depend on sensitive clay behavior, progressive strength loss,
and likely remolding/destructuration. A reduced Drucker-Prager wedge smoke can
exercise geometry and u-pw field plumbing, but it cannot reproduce
retrogression.

## Current Capability

Current reduced slope/field smokes use:

- existing Drucker-Prager style soil response;
- hydrostatic pore pressure initialization;
- PR pressure diagnostics;
- short CPU execution only;
- feedback disabled in the first reduced slope smoke.

This is not a sensitive clay model.

## Required Model Features for Strict Reproduction

The paper-specific model must be confirmed from PDF/SI, but a strict sensitive
clay path likely needs:

- peak and remolded shear strength;
- strain-softening law or accumulated plastic strain dependency;
- sensitivity/remolding parameter;
- possible destructuration or bonding variable;
- residual strength floor;
- regularization or smoothing to avoid mesh/particle-size pathological
  localization;
- output of softening/remolding state variables;
- calibration against the paper material table.

## Candidate Implementation Paths

### Path A: DP With Strength Reduction Field

Pros:

- smaller extension from current DP path;
- easier CPU smoke.

Cons:

- may not match the paper if the constitutive law is more specific;
- localization and mesh dependency likely.

### Path B: Full Sensitive-Clay Constitutive Model

Pros:

- closer to retrogressive landslide physics.

Cons:

- substantial source feature;
- needs careful stress integration, state variables, output, and validation;
- too large for automatic implementation without paper parameter extraction.

### Path C: Defer Strict Slope/Field Material Model

Pros:

- allows PR core and boundary work to continue.

Cons:

- 05/06 remain reduced smoke/data-blocked, not strict reproduction.

## Minimal CPU Smoke Before Full Model

If a small material prototype is later implemented:

- use a tiny slope or shear band test;
- no long runs;
- verify code=0, excluded=0, no NaN;
- confirm strength decreases only where plastic strain/remolding accumulates;
- output softening state.

## GPU Implications

Sensitive clay is not required for passive `PorePressg` or pressure-only PR GPU
arrays. It is required before production-scale retrogressive slope or
Sainte-Monique GPU reproduction. The material state variables would need GPU
memory, sorting/duplicate, restart, and output support.

## Current Recommendation

Do not implement sensitive clay automatically in this pass. Keep 05/06 marked as
reduced smoke/data-blocked. Revisit after paper parameter extraction and after
the boundary/loading decisions are clearer.

