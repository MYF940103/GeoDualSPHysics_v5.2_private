# Sensitive Clay / Strain-Softening Model Plan

Date: 2026-05-11

Milestone: MAT-2 from `full_cpu_implementation_backlog.md`

This plan captures the material-model gap for the retrogressive slope and
Sainte-Monique cases. It started as a design document; the CPU reduced
Drucker-Prager softening path described below has now been implemented and
smoke-tested.

## Why This Matters

The retrogressive slope and Sainte-Monique targets are not only pore-pressure
benchmarks. They depend on sensitive clay behavior, progressive strength loss,
and likely remolding/destructuration. A reduced Drucker-Prager wedge smoke can
exercise geometry and u-pw field plumbing, but it cannot reproduce
retrogression.

## Current Capability

Current reduced slope/field smokes can use:

- existing Drucker-Prager style soil response;
- optional CPU Drucker-Prager exponential softening controlled by
  `<Softening value="1" />`;
- hydrostatic pore pressure initialization;
- PR pressure diagnostics;
- short CPU execution only;
- feedback enabled in the reduced u-pw softening smoke.

This is still not a full field-scale sensitive-clay model, but it exercises the
paper-style peak-to-residual strength degradation law on the CPU path.

## Implemented CPU Approximation

The CPU path now supports a reduced DP-based softening law:

```text
c(kappa)   = c_r   + (c_p   - c_r)   * exp(-n_coh * kappa)
phi(kappa) = phi_r + (phi_p - phi_r) * exp(-n_phi * kappa)
kappa      = Kplastic
```

Implementation status:

- `Softening` was added to `StSoilCte` and is read from
  `<execution><special><soils>`.
- Existing `coh`, `phi`, `coh_r`, `phi_r`, `n_coh`, and `n_phi` are reused.
- The CPU stress update calls the existing `ConsRelationEPsft_fast()` path when
  `Softening=1`.
- `Softening=0` remains the default and preserves the previous DP behavior.
- `Kplastic` remains the state/output used to reconstruct local degraded
  strength in postprocessing.

Micro tests under
`examples/u-pw/05_Retrogressive_Slope/experiments/SofteningMicro/` passed with
`code=0`, `excluded=0`, and no NaN/Inf. A deliberately weak trigger case
produced `Kplastic_max = 8.5393706e-4` and an estimated cohesion minimum of
`0.8587 Pa` from a `1 Pa` peak and `0.1 Pa` residual.

The reduced slope softening smoke
`CaseRetrogressiveSlope_PR_SofteningSmoke_Def.xml` also passed with `code=0`,
`excluded=0`, and no NaN/Inf. It produced `Kplastic_max = 6.5801572e-4` and an
estimated local cohesion minimum of `150.553 Pa` from a reduced smoke-test peak
cohesion of `151 Pa`.

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

The reduced CPU softening path is now available for smoke testing. It should be
used to keep 05 retrogressive slope reduced smokes closer to the paper material
logic, but it should not be treated as full retrogressive or Sainte-Monique
reproduction.

Remaining work:

- calibrate strength and initial-state parameters from the paper/field data;
- decide whether a fuller sensitive-clay/remolding/destructuration branch is
  required beyond `Kplastic`-driven exponential softening;
- port or redesign the material state for GPU before production slope/field
  runs;
- combine the material model with production pore-pressure boundary treatment
  and field-scale geometry.
