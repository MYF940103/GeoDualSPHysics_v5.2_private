# Sensitive Clay Softening Implementation Plan

Date: 2026-05-11

## 1. Scope

This implementation is:

- CPU-only;
- Drucker-Prager based;
- focused on the u-pw paper's sensitive-clay exponential softening law;
- intended for reduced retrogressive slope and Sainte-Monique smoke tests;
- not a full MCC or field-scale sensitive-clay material branch;
- not a GPU implementation.

The production PR pressure-rate, feedback, Shepard, damping, restart, and
hydraulic boundary logic are not modified.

## 2. Parameters

Reuse existing `StSoilCte` material constants:

- `coh`: peak cohesion `c_p`;
- `phi`: peak friction angle `phi_p`;
- `coh_r`: residual cohesion `c_r`;
- `phi_r`: residual friction angle `phi_r`;
- `n_coh`: cohesion softening coefficient;
- `n_phi`: friction softening coefficient;
- `Kplastic`: existing particle output/state for accumulated equivalent
  deviatoric plastic strain.

Add one explicit switch to `StSoilCte`:

```cpp
unsigned Softening;
```

Recommended XML:

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
      <Softening value="1" />
    </soils>
  </special>
</execution>
```

Default:

```xml
<Softening value="0" />
```

If `Softening=0`, existing Drucker-Prager behavior must be unchanged.

## 3. Strength Evolution

Use the paper Eq. (48) form:

```text
c(kappa) = c_r + (c_p - c_r) exp(-n_coh * kappa)
phi(kappa) = phi_r + (phi_p - phi_r) exp(-n_phi * kappa)
```

where:

- `kappa = Kplastic`;
- `Kplastic` is the existing accumulated equivalent deviatoric plastic strain;
- residual values are lower bounds reached asymptotically.

This is already implemented by `UpdateDPvars()` and used by
`ConsRelationEPsft_fast()`.

## 4. Return-Mapping Hook

Current CPU integration paths compute elastic trial stress and then call:

```cpp
ConsRelationEP_fast(...)
```

The minimal change is:

```cpp
if(SoilCte.Softening)
  ConsRelationEPsft_fast(... SoilCte.phi, SoilCte.phi_r, SoilCte.n_phi,
                         SoilCte.coh, SoilCte.coh_r, SoilCte.n_coh,
                         SoilCte.dlt, kplasticold, signew, kplasnew);
else
  ConsRelationEP_fast(...);
```

This keeps the elastic predictor and return-mapping structure intact.

The three CPU time-integration locations that need this decision are:

- `JSphCpu::ComputeVerletVarsFluid()`;
- `JSphCpu::ComputeSymplecticPre()`;
- `JSphCpu::ComputeSymplecticCorr()`.

## 5. Validation and Safety

Validate material input:

- `Softening` accepts `0` or `1`;
- `coh_r >= 0`;
- `n_coh >= 0`;
- `n_phi >= 0`;
- if `Softening=1` and residual values are not meaningful, issue warnings or
  default residuals to peak values.

Do not allow negative cohesion.

Friction angles are already read in degrees and converted to radians.

## 6. Output

First implementation keeps output minimal:

- rely on existing `Kplastic`;
- do not add local cohesion/friction arrays in this phase.

Postprocessing scripts can compute approximate local softened cohesion from
`Kplastic` using the same formula.

Future optional diagnostics:

- `SofteningCohesion`;
- `SofteningPhi`;
- `SofteningStrengthRatio`.

These are not required for the first CPU smoke.

## 7. Smoke Tests

### Micro Tests

Create `examples/u-pw/05_Retrogressive_Slope/experiments/SofteningMicro/`.

Run:

1. `Softening=0`: backward-compatible reduced slope smoke.
2. `Softening=1`: weak/residual-sensitive smoke with visible `Kplastic` growth.
3. Extreme residual setting: verify no NaN, no negative strength, and no crash.

### Reduced Case 5 Smoke

Create:

- `CaseRetrogressiveSlope_PR_SofteningSmoke_Def.xml`
- `xCaseRetrogressiveSlope_PR_SofteningSmoke_win64_CPU_release.bat`
- `analyze_retro_softening_smoke.py`

Check:

- GenCase code=0;
- DualSPHysics code=0;
- excluded=0 or clearly explained if tiny;
- finite PR fields;
- `Kplastic` grows;
- computed softened cohesion decreases from peak toward residual where plastic
  strain accumulates.

## 8. Known Differences From Full Paper Workflow

- No full gravity-initialization / strength-reduction staged workflow.
- No production MLS pore-pressure boundary.
- No full field-scale particle count.
- No GPU.
- No MCC.
- No explicit remolding/destructuration variable beyond `Kplastic`-driven
  exponential softening.

This is a CPU reduced-smoke material feature, not a complete paper
reproduction.

## 9. Micro-Test Result

CPU micro tests were added under
`examples/u-pw/05_Retrogressive_Slope/experiments/SofteningMicro/`.

The baseline/off, on, and extreme-residual cases all completed with `code=0`,
`excluded=0`, and no NaN/Inf. The deliberately weak trigger case also completed
and produced visible plastic strain:

- `Kplastic_max = 8.5393706e-4`;
- estimated local cohesion minimum `0.8587 Pa` from a peak value of `1 Pa` and
  residual value of `0.1 Pa`;
- no negative strength, NaN, or excluded particles.

This validates the CPU code path before moving to the reduced retrogressive
slope softening smoke.
