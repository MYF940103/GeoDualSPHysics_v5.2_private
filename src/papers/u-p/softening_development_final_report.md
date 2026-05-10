# Sensitive Clay Softening Development Final Report

Date: 2026-05-11

## Scope

This report closes the CPU-only sensitive-clay softening development pass for
the reduced retrogressive slope workflow. No GPU/CUDA files were modified, no
GPU build was run, and no long production run was started.

The implementation is a Drucker-Prager based reduced approximation of the
paper's sensitive-clay softening law. It is intended to make short CPU slope
smokes exercise peak-to-residual material degradation. It is not a complete
field-scale retrogressive landslide or Sainte-Monique reproduction.

## Commits Created

| Commit | Purpose |
|---|---|
| `17b4cbb` | Start sensitive clay softening development run. |
| `8d864db` | Audit sensitive clay softening model and existing code. |
| `423dccb` | Plan sensitive clay softening implementation. |
| `2564eff` | Implement CPU sensitive clay softening model. |
| `55e5dab` | Add sensitive clay softening micro tests. |
| `fed3e2b` | Add retrogressive slope softening CPU smoke. |

## Implemented CPU Feature

The CPU stress update now supports an optional soil material switch:

```xml
<Softening value="1" />
```

When enabled, the CPU Drucker-Prager path uses the existing
`ConsRelationEPsft_fast()` softening return-mapping variant. The elastic
predictor, u-pw PR pore-pressure rate, feedback, Shepard regularization,
hydromechanical damping, restart, and hydraulic boundary paths were not
changed.

Strength evolution:

```text
c(kappa)   = c_r   + (c_p   - c_r)   * exp(-n_coh * kappa)
phi(kappa) = phi_r + (phi_p - phi_r) * exp(-n_phi * kappa)
kappa      = Kplastic
```

This matches the paper-style exponential peak-to-residual law used in the
u-pw sensitive-clay notes. `Kplastic` is the existing accumulated equivalent
deviatoric plastic strain state and remains the primary output for checking
softening activation.

## Parameters

Parameters are soil material constants under `<execution><special><soils>`:

| Parameter | Meaning |
|---|---|
| `Softening` | `0`: previous DP behavior, `1`: CPU exponential softening. |
| `coh` | Peak cohesion `c_p`. |
| `phi` | Peak friction angle `phi_p` in degrees in XML. |
| `coh_r` | Residual cohesion `c_r`. |
| `phi_r` | Residual friction angle `phi_r` in degrees in XML. |
| `n_coh` | Cohesion softening coefficient. |
| `n_phi` | Friction softening coefficient. |

Example:

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

Default behavior is `Softening=0`, so old DP cases remain unchanged unless the
new switch is explicitly enabled.

## Build Result

CPU Debug rebuild succeeded after the source implementation. The build produced
the CPU debug executable and only the pre-existing MSVC `D9035` warning was
observed.

## Micro Tests

Location:

```text
examples/u-pw/05_Retrogressive_Slope/experiments/SofteningMicro/
```

The following CPU Release micro smokes were created and run:

| Case | Purpose | Result |
|---|---|---|
| `SofteningMicro_Off` | Backward-compatible baseline. | `code=0`, `excluded=0`, no NaN/Inf. |
| `SofteningMicro_On` | Softening enabled with normal reduced parameters. | `code=0`, `excluded=0`, no NaN/Inf. |
| `SofteningMicro_ExtremeResidual` | Residual-strength safety check. | `code=0`, `excluded=0`, no NaN/Inf. |
| `SofteningMicro_Trigger` | Deliberately weak trigger case. | `code=0`, `excluded=0`, no NaN/Inf, plastic strain generated. |

Trigger metrics:

```text
Kplastic_max = 8.5393706e-4
estimated cohesion minimum = 0.8587 Pa
peak cohesion = 1 Pa
residual cohesion = 0.1 Pa
```

This confirms that the CPU code path activates, `Kplastic` grows, and local
strength remains bounded above residual without producing NaN or excluded
particles.

## Reduced Retrogressive Slope Softening Smoke

Location:

```text
examples/u-pw/05_Retrogressive_Slope/
```

Cases:

```text
CaseRetrogressiveSlope_PR_SofteningSmoke_Off_Def.xml
CaseRetrogressiveSlope_PR_SofteningSmoke_Def.xml
```

Both cases use the same reduced wedge geometry and u-pw PR settings. The
softening case sets `Softening=1`; the comparison case sets `Softening=0`.
The cohesion values are intentionally scaled down from the paper value while
preserving the peak/residual ratio so that plasticity appears in a short CPU
smoke.

Execution summary:

| Case | GenCase | DualSPHysics | Excluded | NaN/Inf | Key fields |
|---|---:|---:|---:|---|---|
| `Softening=0` | 0 | 0 | 0 | none | PR fields, `Kplastic`, `PorePressureAccelDiff.*` |
| `Softening=1` | 0 | 0 | 0 | none | PR fields, `Kplastic`, `PorePressureAccelDiff.*` |

Reduced smoke metrics:

| Case | `Kplastic_max` | Estimated cohesion min | Max displacement | Max velocity |
|---|---:|---:|---:|---:|
| `Softening=0` | `6.5801572e-4` | `151.0 Pa` | `1.59078e-4 m` | `6.185e-1 m/s` |
| `Softening=1` | `6.5801572e-4` | `150.553 Pa` | `1.59078e-4 m` | `6.185e-1 m/s` |

The reduced smoke confirms that the material branch runs inside the slope
workflow and that postprocessing can reconstruct local strength degradation.
The physical displacement response is almost identical over the tiny smoke
window, which is expected: this run is for execution-path validation, not for
full retrogression.

## Differences From The Paper Workflow

The current implementation and smoke tests do not yet include:

- full field-scale retrogressive geometry;
- calibrated initial stress and pore-pressure state;
- production pore-pressure boundary MLS/mirror treatment;
- remolding/destructuration state beyond `Kplastic`-driven exponential
  softening;
- long-time slope retrogression;
- Sainte-Monique field topography and material zoning;
- GPU material-state support.

Therefore, reduced softening smoke passed, but strict paper reproduction is not
complete.

## GPU / Next-Step Implications

The CPU material feature does not require changing passive GPU G1 planning.
Passive G1, if later authorized, should still remain limited to `PorePressg`
allocation, sorting/duplicate, and output parity.

For production 05/06 GPU runs, softening needs a separate GPU material-state
planning step:

- GPU storage for `Softening`-dependent material constants is trivial because
  they are global soil constants in the current single-material path.
- GPU stress-update kernels would need the same peak-to-residual law using
  particle `Kplastic`.
- Any future remolding/destructuration state variable would need allocation,
  sorting/duplicate, restart, and output support.

Recommended next steps:

1. Keep CPU `Softening=1` available for reduced slope smokes.
2. Decide whether a fuller sensitive-clay/remolding model is needed before
   field-scale Sainte-Monique reproduction.
3. Do not start GPU softening until the GPU PR/core scope is explicitly
   authorized.
